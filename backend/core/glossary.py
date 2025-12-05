# core/glossary.py
# -*- coding: utf-8 -*-

import re
from typing import List, Dict


class Glossary:
    """
    Gestiona términos del glosario y los convierte en placeholders seguros
    para que DeepL jamás los traduzca.
    """

    def __init__(self, glossary_entries: List[Dict]):
        self.entries = glossary_entries or []
        self.placeholder_prefix = "§§GLOS_"
        self.placeholder_suffix = "_§§"
        self.compiled_patterns = []
        self._compile_patterns()

    def _compile_patterns(self):
        self.compiled_patterns = []

        for entry in self.entries:
            term = entry.get("term")
            if not term:
                continue

            pattern = re.compile(
                r"\b" + re.escape(term) + r"\b",
                flags=re.IGNORECASE
            )
            self.compiled_patterns.append((pattern, term))

    def size(self):
        return len(self.entries)

    def apply_placeholders(self, text):
        """
        Reemplaza términos por placeholders seguros.
        """
        if not text:
            return text

        for idx, (pattern, term) in enumerate(self.compiled_patterns):
            placeholder = f"{self.placeholder_prefix}{idx}{self.placeholder_suffix}"
            text = pattern.sub(placeholder, text)

        return text

    def restore_placeholders(self, translated_text):
        """
        Devuelve los placeholders a su término original.
        """
        if not translated_text:
            return translated_text

        for idx, (_, term) in enumerate(self.compiled_patterns):
            placeholder = f"{self.placeholder_prefix}{idx}{self.placeholder_suffix}"
            translated_text = translated_text.replace(placeholder, term)

        return translated_text
