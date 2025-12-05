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
        Reemplaza términos (según src_lang) por placeholders.
        Retorna (text_with_placeholders, placeholder_map)
        placeholder_map: { placeholder: replacement_final_string }
        """
        placeholder_map = {}
        text_out = text
        used = set()
        idx = 0

        # Iterate compiled patterns; for each match, only if pattern's lang aligns with src_lang (or acronym)
        for pat, entry, lang in self.compiled:
            # decide if we should match this pattern given detected source language
            # if src_lang == 'es': we want to match Spanish terms (lang == 'es')
            # if src_lang == 'en': match English terms and acronyms (lang == 'en' or 'acronym')
            match_allowed = False
            if src_lang.lower() == "es" and lang == "es":
                match_allowed = True
            if src_lang.lower() == "en" and (lang == "en" or lang == "acronym"):
                match_allowed = True

            if not match_allowed:
                continue

            # Replacement function for re.sub
            def _repl(m):
                nonlocal idx, placeholder_map, used
                span = m.group(0)
                # avoid duplicate replacements for same exact span index: let re handle global replace
                ph = self._generate_placeholder(idx)
                # Compute final replacement depending on direction
                if src_lang.lower() == "es":
                    # Spanish input -> want English output; prefer ACRONYM (ACR (term_en)) if acronym exists
                    acr = (entry.get("acronym") or "").strip()
                    term_en = entry.get("term_en") or ""
                    if acr:
                        repl_value = f"{acr} ({term_en})" if term_en else acr
                    else:
                        repl_value = term_en or span
                else:  # src_lang == "en"
                    # English input -> want Spanish output
                    term_es = entry.get("term_es") or ""
                    # If entry is acronym-only mapping (acronym->term_es), entry must have term_es
                    repl_value = term_es or span

                placeholder_map[ph] = repl_value
                idx += 1
                return ph

            try:
                # Use sub on current text_out; flags are already in compiled pattern
                text_out = pat.sub(_repl, text_out)
            except Exception:
                continue

        had_hits = len(placeholder_map) > 0
        return text_out, placeholder_map, had_hits

    def restore_placeholders(self, text: str, placeholder_map: dict) -> str:
        out = text
        # Replace placeholders with their final values
        # Do stable replacement: iterate placeholder_map items
        for ph, val in placeholder_map.items():
            out = out.replace(ph, val)
        return out
