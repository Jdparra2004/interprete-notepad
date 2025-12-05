# core/protector.py
# -*- coding: utf-8 -*-

import re


class TextProtector:
    """
    Protege expresiones técnicas para evitar distorsiones en DeepL:
    - Números
    - Siglas
    - Unidades
    - Código técnico
    """

    def __init__(self):
        self.rules = [
            # Evita alteración de unidades (kg → kilograms, etc.)
            (re.compile(r"\b(\d+)\s?(kg|g|mg|L|mL|km|cm|mm|mol|Pa|kPa)\b"), r"\1§\2§"),

            # Siglas de ingeniería / ciencia
            (re.compile(r"\b([A-Z]{2,6})\b"), r"§\1§"),

            # Números largos
            (re.compile(r"\b\d{4,}\b"), r"§\g<0>§"),
        ]

    def protect(self, text):
        if not text:
            return text
        for pattern, repl in self.rules:
            text = pattern.sub(repl, text)
        return text

    def unprotect(self, text):
        if not text:
            return text
        return text.replace("§", "")
