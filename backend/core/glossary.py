# core/glossary.py
# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Tuple

class Glossary:
    """
    Carga glosario y crea patrones para matching.
    Provee apply_placeholders(text, src) -> (text_with_placeholders, placeholder_map)
    y restore_placeholders(text, placeholder_map) -> restored_text
    """

    def __init__(self, entries: List[Dict]):
        self.entries = entries or []
        # compiled entries: list of tuples (pattern, entry, lang_key)
        # lang_key = 'es' or 'en' or 'acronym'
        self.compiled = []
        self._compile_all()

    def _make_variants(self, entry: Dict) -> List[Tuple[str, str]]:
        """
        Produce list of (variant, lang_key) to index from a single entry.
        """
        variants = []
        te = entry.get("term_es", "").strip()
        tn = entry.get("term_en", "").strip()
        ac = (entry.get("acronym") or "").strip()

        # main forms
        if te:
            variants.append((te, "es"))
        if tn:
            variants.append((tn, "en"))
        if ac:
            variants.append((ac, "acronym"))

        # aliases lists (optional)
        for a in entry.get("aliases_es", []) or []:
            variants.append((a.strip(), "es"))
        for a in entry.get("aliases_en", []) or []:
            variants.append((a.strip(), "en"))

        # also add accent-less / normalized variants if needed (optional)
        return variants

    def _compile_all(self):
        self.compiled = []
        for entry in self.entries:
            for variant, lang in self._make_variants(entry):
                if not variant:
                    continue
                # build robust regex: word boundaries but allow accents and unicode words
                pat = re.compile(r"\b" + re.escape(variant) + r"\b", flags=re.IGNORECASE | re.UNICODE)
                self.compiled.append((pat, entry, lang))
        # sort by length to prefer longest matches
        self.compiled.sort(key=lambda t: -len(t[0].pattern))

    def size(self):
        return len(self.entries)

    def _generate_placeholder(self, idx: int) -> str:
        # token safe for DeepL (avoid exotic punctuation). Use alnum underscores.
        return f"GLOSSARYPH{idx:04d}TOKEN"

    def apply_placeholders(self, text: str, src_lang: str):
        """
        Replace glossary terms with placeholders.
        src_lang = 'es' or 'en'
        Returns: (text_with_placeholders, placeholder_map, had_hits)
        """
        if not isinstance(text, str) or not text.strip():
            return text, {}, False

        placeholder_map = {}
        had_hits = False
        result = text

        # Placeholder counter — MUST start at 1 consistently
        ph_index = 1

        # Detect direction
        is_spanish = src_lang == "es"
        is_english = src_lang == "en"

        # Precompiled patterns inside the Glossary object avoid recreating them.
        for item in self.terms:

            # Extract info
            term_es = item["term_es"]
            term_en = item["term_en"]
            acronym = item.get("acronym")

            # Decide valid matches
            if is_spanish:
                # Spanish → match Spanish terms only
                patterns = [
                    getattr(item, "pattern_es_exact", None),
                    getattr(item, "pattern_es_alias", None)
                ]
                final = f"{acronym} ({term_en})" if acronym else term_en

            else:
                # English → match English terms + acronyms
                patterns = [
                    getattr(item, "pattern_en_exact", None),
                    getattr(item, "pattern_en_alias", None),
                    getattr(item, "pattern_acronym", None)
                ]
                final = term_es

            # Apply each pattern
            for pattern in patterns:
                if not pattern:
                    continue

                # Generate placeholder safely
                placeholder = f"GLOSARIOPH{ph_index:04d}TOKEN"

                # Replace
                new_text, n = pattern.subn(placeholder, result)

                if n > 0:
                    placeholder_map[placeholder] = final
                    ph_index += 1
                    had_hits = True
                    result = new_text

        return result, placeholder_map, had_hits


    def restore_placeholders(self, text: str, placeholder_map: dict) -> str:
        out = text
        # Replace placeholders with their final values
        # Do stable replacement: iterate placeholder_map items
        for ph, val in placeholder_map.items():
            out = out.replace(ph, val)
        return out
