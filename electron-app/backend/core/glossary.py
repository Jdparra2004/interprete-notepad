# core/glossary.py
# -*- coding: utf-8 -*-
import re
import unicodedata
from typing import List, Dict, Tuple


def _norm(s: str) -> str:
    """Normalize and strip strings to NFC."""
    if s is None:
        return ""
    return unicodedata.normalize("NFC", s.strip())


class Glossary:
    """
    Glossary:
      ✓ Normaliza todo
      ✓ Maneja acrónimos correctamente (EN→ES y ES→EN)
      ✓ Evita falsos positivos
      ✓ Respeta idioma fuente detectado
    """

    def __init__(self, entries: List[Dict]):
        self.entries = entries or []
        self.compiled: List[Tuple[re.Pattern, Dict, str, str]] = []
        self._compile_all()

    # --------------------------------------------------
    # Generate variants (ES, EN, acronyms + aliases)
    # --------------------------------------------------
    def _make_variants(self, entry: Dict) -> List[Tuple[str, str, str]]:
        """
        Returns list of (variant_text, variant_language, variant_type)
        variant_type ∈ {"main", "alias", "acronym"}
        """
        variants = []

        term_es = _norm(entry.get("term_es", ""))
        term_en = _norm(entry.get("term_en", ""))
        acronym = _norm(entry.get("acronym", ""))

        # Spanish main term
        if term_es:
            variants.append((term_es, "es", "main"))

        # English main term
        if term_en:
            variants.append((term_en, "en", "main"))

        # Acronyms — must match both directions
        if acronym:
            variants.extend([
                (acronym, "acronym", "acronym"),
                (acronym.upper(), "acronym", "acronym"),
                (acronym.lower(), "acronym", "acronym"),
            ])

        # Aliases ES
        for a in entry.get("aliases_es", []):
            a = _norm(a)
            if a:
                variants.append((a, "es", "alias"))

        # Aliases EN
        for a in entry.get("aliases_en", []):
            a = _norm(a)
            if a:
                variants.append((a, "en", "alias"))

        return variants

    # --------------------------------------------------
    # Compile regex patterns
    # --------------------------------------------------
    def _compile_all(self):
        self.compiled = []

        for entry in self.entries:
            for variant, lang, vtype in self._make_variants(entry):
                pattern = re.compile(
                    rf"(?<![A-Za-z0-9]){re.escape(variant)}(?![A-Za-z0-9])",
                    flags=re.IGNORECASE | re.UNICODE
                )
                self.compiled.append((pattern, entry, lang, vtype))

        # Prioritize multi‑word & longer matches
        self.compiled.sort(key=lambda i: -len(i[0].pattern))

    # --------------------------------------------------
    # Placeholders
    # --------------------------------------------------
    def _placeholder(self, idx: int):
        return f"GLOSARIOPH{idx:04d}TOKEN"

    def apply_placeholders(self, text: str, src_lang: str):
        """
        Replace terms with placeholders.
        src_lang: "en" or "es"
        """
        if not text:
            return text, {}, False

        result = text
        placeholder_map = {}
        idx = 1
        hits = False

        for pattern, entry, variant_lang, vtype in self.compiled:

            # Filter by detected language
            if src_lang == "es" and variant_lang not in ("es",):
                continue
            if src_lang == "en" and variant_lang not in ("en", "acronym"):
                continue

            term_es = _norm(entry.get("term_es", ""))
            term_en = _norm(entry.get("term_en", ""))
            ac = _norm(entry.get("acronym", ""))

            # -------------------------
            # ES → EN + optional acronym
            # -------------------------
            if src_lang == "es":
                if ac:
                    # Example: "intravenosa" -> "IV (intravenous)"
                    final = f"{ac} ({term_en})"
                else:
                    final = term_en

            # -------------------------
            # EN → ES (acronyms map too)
            # -------------------------
            else:  # src_lang == "en"
                # Example: "IV" -> "vía intravenosa"
                final = term_es

            # Apply replacement
            new_result, n = pattern.subn(self._placeholder(idx), result)

            if n > 0:
                hits = True
                placeholder_map[self._placeholder(idx)] = final
                idx += 1
                result = new_result

        return result, placeholder_map, hits

    # --------------------------------------------------
    # Restore placeholders
    # --------------------------------------------------
    def restore_placeholders(self, text: str, placeholder_map: Dict[str, str]):
        if not placeholder_map:
            return text
        for ph, val in placeholder_map.items():
            text = text.replace(ph, val)
        return text

    # For /health endpoint
    def size(self):
        return len(self.entries)
