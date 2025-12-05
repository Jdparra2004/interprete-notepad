# core/glossary.py
# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Tuple

class Glossary:
    """
    Sistema de glosario con placeholders, bidireccional:
      ES → EN (y agrega acrónimo si existe)
      EN → ES (detecta acrónimos también)

    apply_placeholders(text, src_lang) ->
        (text_with_placeholders, placeholder_map, had_hits)

    restore_placeholders(text, placeholder_map) ->
        text restored
    """

    def __init__(self, entries: List[Dict]):
        self.entries = entries or []
        # compiled items:
        # (regex, entry_dict, lang_key)  lang_key = "es" | "en" | "acronym"
        self.compiled: List[Tuple[re.Pattern, Dict, str]] = []
        self._compile()

    def _compile(self):
        """Precompila patrones para ES, EN y acrónimos."""
        self.compiled = []

        for entry in self.entries:
            te = entry.get("term_es", "").strip()
            tn = entry.get("term_en", "").strip()
            ac = (entry.get("acronym") or "").strip()

            # principal ES
            if te:
                pat = re.compile(r"\b" + re.escape(te) + r"\b", re.IGNORECASE)
                self.compiled.append((pat, entry, "es"))

            # principal EN
            if tn:
                pat = re.compile(r"\b" + re.escape(tn) + r"\b", re.IGNORECASE)
                self.compiled.append((pat, entry, "en"))

            # acrónimo
            if ac:
                pat = re.compile(r"\b" + re.escape(ac) + r"\b", re.IGNORECASE)
                self.compiled.append((pat, entry, "acronym"))

            # alias ES
            for a in entry.get("aliases_es", []) or []:
                a = a.strip()
                if a:
                    pat = re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE)
                    self.compiled.append((pat, entry, "es"))

            # alias EN
            for a in entry.get("aliases_en", []) or []:
                a = a.strip()
                if a:
                    pat = re.compile(r"\b" + re.escape(a) + r"\b", re.IGNORECASE)
                    self.compiled.append((pat, entry, "en"))

        # Ordenar por longitud para capturar términos más largos primero
        self.compiled.sort(key=lambda t: -len(t[0].pattern))

    def _placeholder(self, idx: int) -> str:
        return f"GLOSARIOPH{idx:04d}TOKEN"

    def apply_placeholders(self, text: str, src_lang: str):
        """
        src_lang = "es" o "en"
        Reemplaza términos del glosario con placeholders.
        Regresa: (nuevo_texto, mapa, had_hits)
        """
        if not isinstance(text, str) or not text.strip():
            return text, {}, False

        result = text
        placeholder_map = {}
        had_hits = False
        idx = 1

        for pattern, entry, lang_key in self.compiled:

            # Validar “hacia dónde” traducimos
            if src_lang == "es":
                # ES → EN + (acrónimo si existe)
                if lang_key != "es":
                    continue

                tn = entry.get("term_en", "").strip()
                ac = entry.get("acronym", "").strip()

                final = f"{ac} ({tn})" if ac else tn

            else:
                # EN → ES (si es acrónimo o término EN)
                if lang_key not in ("en", "acronym"):
                    continue

                final = entry.get("term_es", "").strip()

            placeholder = self._placeholder(idx)
            new_text, n = pattern.subn(placeholder, result)

            if n > 0:
                result = new_text
                placeholder_map[placeholder] = final
                idx += 1
                had_hits = True

        return result, placeholder_map, had_hits

    def restore_placeholders(self, text: str, placeholder_map: dict) -> str:
        """Sustituye los placeholders por el contenido del glosario."""
        out = text
        for ph, val in placeholder_map.items():
            out = out.replace(ph, val)
        return out
