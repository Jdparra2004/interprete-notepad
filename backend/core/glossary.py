# core/glossary.py
# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Tuple


class Glossary:
    """
    Maneja:
      - generación de placeholders
      - reemplazo seguro antes de DeepL
      - restauración después de DeepL
    """

    def __init__(self, entries: List[Dict]):
        self.entries = entries or []
        self.compiled = []
        self._compile_all()

    # ---------------------------------------------------------
    # Compilación de variantes ES / EN / ACRÓNIMO
    # ---------------------------------------------------------
    def _make_variants(self, entry: Dict) -> List[Tuple[str, str]]:
        variants = []

        te = entry.get("term_es", "").strip()
        tn = entry.get("term_en", "").strip()
        ac = entry.get("acronym", "").strip()

        if te:
            variants.append((te, "es"))
        if tn:
            variants.append((tn, "en"))
        if ac:
            variants.append((ac, "acronym"))

        for a in entry.get("aliases_es", []) or []:
            variants.append((a.strip(), "es"))

        for a in entry.get("aliases_en", []) or []:
            variants.append((a.strip(), "en"))

        return variants

    def _compile_all(self):
        self.compiled = []

        for entry in self.entries:
            for variant, lang_key in self._make_variants(entry):
                if not variant:
                    continue

                # \b para palabras exactas y evitar falsos positivos
                pat = re.compile(
                    r"\b" + re.escape(variant) + r"\b",
                    flags=re.IGNORECASE | re.UNICODE
                )

                self.compiled.append((pat, entry, lang_key))

        # Ordenar por longitud para preferir coincidencias largas
        self.compiled.sort(key=lambda t: -len(t[0].pattern))

    # ---------------------------------------------------------
    # Generación de placeholders
    # ---------------------------------------------------------
    def _generate_placeholder(self, idx: int):
        return f"GLOSARIOPH{idx:04d}TOKEN"

    # ---------------------------------------------------------
    # Reemplazo antes de traducir
    # ---------------------------------------------------------
    def apply_placeholders(self, text: str, src_lang: str):
        """
        src_lang: "es" o "en"
        Retorna:
           text_modificado, placeholder_map, had_hits
        """
        if not text.strip():
            return text, {}, False

        is_es = src_lang == "es"
        is_en = src_lang == "en"

        ph_map = {}
        had_hits = False
        current_text = text

        ph_index = 1

        for pattern, entry, lang_key in self.compiled:

            # Determinar si este patrón aplica según el idioma fuente
            if is_es and lang_key != "es":
                continue
            if is_en and lang_key not in ("en", "acronym"):
                continue

            term_es = entry.get("term_es", "")
            term_en = entry.get("term_en", "")
            acronym = entry.get("acronym", "")

            # Qué valor debe restaurarse después de DeepL
            if is_es:
                # ES → EN
                replacement_value = f"{acronym} ({term_en})" if acronym else term_en
            else:
                # EN → ES, si usa acrónimo también devuelve ES
                replacement_value = term_es

            # Generar placeholder único
            placeholder = self._generate_placeholder(ph_index)

            new_text, count = pattern.subn(placeholder, current_text)

            if count > 0:
                ph_map[placeholder] = replacement_value
                current_text = new_text
                ph_index += 1
                had_hits = True

        return current_text, ph_map, had_hits

    # ---------------------------------------------------------
    # Restauración después de traducir
    # ---------------------------------------------------------
    def restore_placeholders(self, text: str, ph_map: Dict[str, str]) -> str:
        result = text
        for ph, value in ph_map.items():
            result = result.rep
