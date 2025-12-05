# core/glossary.py
# -*- coding: utf-8 -*-
import re
import unicodedata
from typing import List, Dict, Tuple

# NOTE: usamos prints ligeros para debug rápido en consola; si prefieres logging sustitúyelos.
def _norm(s: str) -> str:
    if s is None:
        return ""
    # Normalize to NFC to keep composed accents consistently
    return unicodedata.normalize("NFC", s.strip())

class Glossary:
    """
    Glossary robusto:
      - Normaliza entradas y texto (NFC)
      - Soporta ES->EN (con acrónimo) y EN->ES (incluye acrónimos)
      - Evita placeholders huérfanos y captura errores sin romper la pipeline
    """

    def __init__(self, entries: List[Dict]):
        self.entries = entries or []
        self.compiled: List[Tuple[re.Pattern, Dict, str]] = []
        try:
            self._compile_all()
        except Exception as e:
            print("[glossary] compile error:", e)
            self.compiled = []

    def _make_variants(self, entry: Dict) -> List[Tuple[str, str]]:
        variants = []

        te = entry.get("term_es", "").strip()
        tn = entry.get("term_en", "").strip()
        ac = (entry.get("acronym") or "").strip()

        # Spanish term
        if te:
            variants.append((te, "es"))

        # English term
        if tn:
            variants.append((tn, "en"))

        # Acronym variations (robust)
        if ac:
            variants.extend([
                (ac, "acronym"),
                (ac.upper(), "acronym"),
                (ac.lower(), "acronym")
            ])

        # Aliases
        for a in entry.get("aliases_es", []) or []:
            variants.append((a.strip(), "es"))

        for a in entry.get("aliases_en", []) or []:
            variants.append((a.strip(), "en"))

        return variants


    def _compile_all(self):
        self.compiled = []
        for entry in self.entries:
            try:
                for variant, lang_key in self._make_variants(entry):
                    if not variant:
                        continue
                    # Use word boundaries; pattern matches on normalized strings.
                    # We escape the variant to avoid regex injection.
                    pattern = re.compile(
                        rf"(?<![A-Za-z0-9]){re.escape(variant)}(?![A-Za-z0-9])",
                        flags=re.IGNORECASE | re.UNICODE
                    )
                    self.compiled.append((pattern, entry, lang_key))
            except Exception as e:
                print("[glossary] compile entry failed:", e, "entry:", entry)
                continue

        # sort by pattern length (longer first) to match multi-word terms before shorter ones
        self.compiled.sort(key=lambda t: -len(t[0].pattern))

    def _placeholder(self, idx: int) -> str:
        return f"GLOSARIOPH{idx:04d}TOKEN"

    def apply_placeholders(self, text: str, src_lang: str):
        if not isinstance(text, str) or not text.strip():
            return text, {}, False

        placeholder_map = {}
        result = text
        ph_index = 1
        hits = False

        is_spanish = src_lang == "es"
        is_english = src_lang == "en"

        for pattern, entry, lang in self.compiled:

            # Filtrar variantes que NO corresponden al idioma detectado
            if is_spanish and lang != "es":
                continue

            if is_english and lang not in ("en", "acronym"):
                continue

            # Definir valor final
            term_es = entry.get("term_es", "")
            term_en = entry.get("term_en", "")
            ac = entry.get("acronym", "")

            if is_spanish:
                # ES → EN
                final = f"{ac} ({term_en})" if ac else term_en
            else:
                # EN → ES (acronyms also map to Spanish term)
                final = term_es

            placeholder = f"GLOSARIOPH{ph_index:04d}TOKEN"
            new_text, n = pattern.subn(placeholder, result)

            if n > 0:
                hits = True
                placeholder_map[placeholder] = final
                ph_index += 1
                result = new_text

        return result, placeholder_map, hits


    def restore_placeholders(self, text: str, placeholder_map: Dict[str, str]) -> str:
        try:
            if not placeholder_map:
                return text
            out = text
            for ph, val in placeholder_map.items():
                out = out.replace(ph, val)
            return out
        except Exception as e:
            print("[glossary] restore_placeholders error:", e)
            return text
