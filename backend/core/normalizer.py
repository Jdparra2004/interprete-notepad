# core/normalizer.py
# -*- coding: utf-8 -*-

import unicodedata
import re


class TextNormalizer:
    """
    Limpieza, corrección leve y normalización Unicode/Textual.
    """

    def __init__(self):
        # Precompilación de patrones comunes
        self.multiple_spaces = re.compile(r"\s+")
        self.multiple_newlines = re.compile(r"\n{3,}")
        self.safe_punctuation = re.compile(r"[ ]+([.,;:!?])")

    def normalize(self, text: str) -> str:
        """
        Normaliza texto manteniendo estructura lingüística.
        """
        if not isinstance(text, str):
            return text

        # 1. Remover caracteres invisibles problemáticos
        text = (
            text.replace("\x00", "")
                .replace("\u200b", "")
                .replace("\ufeff", "")
                .replace("\xa0", " ")
        )

        # 2. Normalización Unicode
        text = unicodedata.normalize("NFC", text)

        # 3. Espaciado
        text = self.multiple_spaces.sub(" ", text)
        text = self.safe_punctuation.sub(r"\1", text)
        text = self.multiple_newlines.sub("\n\n", text)

        return text.strip()
