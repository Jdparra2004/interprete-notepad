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
        te = _norm(entry.get("term_es", ""))
        tn = _norm(entry.get("term_en", ""))
        ac = _norm(entry.get("acronym", "") or "")

        if te:
            variants.append((te, "es"))
        if tn:
            variants.append((tn, "en"))
        if ac:
            variants.append((ac, "acronym"))

        # aliases
        for a in entry.get("aliases_es", []) or []:
            av = _norm(a)
            if av: variants.append((av, "es"))
        for a in entry.get("aliases_en", []) or []:
            av = _norm(a)
            if av: variants.append((av, "en"))

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
                    pattern = re.compile(r"\b" + re.escape(variant) + r"\b", flags=re.IGNORECASE | re.UNICODE)
                    self.compiled.append((pattern, entry, lang_key))
            except Exception as e:
                print("[glossary] compile entry failed:", e, "entry:", entry)
                continue

        # sort by pattern length (longer first) to match multi-word terms before shorter ones
        self.compiled.sort(key=lambda t: -len(t[0].pattern))

    def _placeholder(self, idx: int) -> str:
        return f"GLOSARIOPH{idx:04d}TOKEN"

    def apply_placeholders(self, text: str, src_lang: str):
        """
        Reemplaza términos conforme al idioma de entrada.
        - text: texto original (puede contener tildes)
        - src_lang: 'es' o 'en'
        Retorna: (text_with_placeholders, placeholder_map, had_hits)
        """
        try:
            if not isinstance(text, str) or not text.strip():
                return text, {}, False

            # Normalize input for consistent matching
            norm_text = _norm(text)

            placeholder_map = {}
            had_hits = False
            idx = 1

            # We'll perform replacements on the normalized text but keep mapping so placeholders replace
            # can then be applied to the original (non-normalized) output after DeepL.
            current = norm_text

            for pattern, entry, lang_key in self.compiled:
                # decide if pattern should be tried for this source language
                if src_lang == "es":
                    if lang_key != "es":
                        continue
                else:  # assume 'en'
                    if lang_key not in ("en", "acronym"):
                        continue

                # determine final replacement value (what placeholder will be restored to)
                term_es = _norm(entry.get("term_es", ""))
                term_en = _norm(entry.get("term_en", ""))
                acronym = _norm(entry.get("acronym", "") or "")

                if src_lang == "es":
                    # spanish input -> want english (prefer acronym if exists)
                    replacement_value = f"{acronym} ({term_en})" if acronym else (term_en or "")
                else:
                    # english input -> want spanish
                    replacement_value = term_es or ""

                # generate placeholder
                ph = self._placeholder(idx)

                # apply on normalized string
                new_current, n = pattern.subn(ph, current)
                if n > 0:
                    # record placeholder mapping (use replacement_value as-is; may contain accents)
                    placeholder_map[ph] = replacement_value
                    current = new_current
                    idx += 1
                    had_hits = True

            # If no hits, return original text unchanged (so DeepL will translate all)
            if not had_hits:
                return text, {}, False

            # Now we need to map placeholders back into the original-text positions.
            # Simplest robust approach: perform the same substitutions on the original (non-normalized)
            # using the same patterns but applied to the original text. This avoids index shift issues.
            original_current = _norm(text)  # normalize original similarly for safe substitution
            # apply placeholders on original_current using same compiled rules and order,
            # but only for those patterns that produced placeholders (we don't have their pattern->ph mapping),
            # so rebuild by iterating again and substituting placeholders in sequence to mirror normalized run.
            # We'll walk compiled again, substituting placeholders according to placeholder_map order.
            # Create an iterator of placeholders in insertion order:
            ph_iter = iter(placeholder_map.keys())
            mirrored = _norm(text)
            for pattern, entry, lang_key in self.compiled:
                if src_lang == "es" and lang_key != "es":
                    continue
                if src_lang != "es" and lang_key not in ("en", "acronym"):
                    continue

                # For each match occurrence, replace with next placeholder if available
                def _subseq(m):
                    try:
                        return next(ph_iter)
                    except StopIteration:
                        return m.group(0)

                try:
                    mirrored, _ = pattern.subn(_subseq, mirrored)
                except Exception:
                    continue

            # mirrored now contains placeholders in original-text's normalization form (NFC)
            # Return mirrored (we keep NFC normalized string) and the placeholder_map
            return mirrored, placeholder_map, had_hits

        except Exception as e:
            # Fail-safe: don't break pipeline; log and return original
            print("[glossary] apply_placeholders error:", e)
            return text, {}, False

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
