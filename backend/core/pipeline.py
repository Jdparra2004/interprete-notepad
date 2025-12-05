# core/pipeline.py
# -*- coding: utf-8 -*-

import requests
import logging

from .normalizer import TextNormalizer
from .glossary import Glossary
from .protector import TextProtector


logger = logging.getLogger("pipeline")


class TranslationPipeline:

    def __init__(self, glossary: Glossary, deepl_api_key=None):
        self.glossary = glossary
        self.deepl_key = deepl_api_key
        self.normalizer = TextNormalizer()
        self.protector = TextProtector()

    # -----------------------------
    # Detect simple language
    # -----------------------------
    @staticmethod
    def detect_language_simple(text: str) -> str:
        english_chars = sum(c.isascii() for c in text)
        ratio = english_chars / max(len(text), 1)

        return "EN" if ratio > 0.85 else "ES"

    # -----------------------------
    # DeepL Call
    # -----------------------------
    def _call_deepl(self, text: str, target_lang: str) -> str:
        if not self.deepl_key:
            raise ValueError("DeepL API key not configured.")

        url = "https://api-free.deepl.com/v2/translate"
        payload = {
            "auth_key": self.deepl_key,
            "text": text,
            "target_lang": target_lang,
        }

        response = requests.post(url, data=payload, timeout=15)
        response.raise_for_status()

        data = response.json()
        return data["translations"][0]["text"]

    # -----------------------------
    # Main Pipeline
    # -----------------------------
    def run(self, text: str) -> dict:

        logger.info("Pipeline: Starting normalization")
        normalized = self.normalizer.normalize(text)

        logger.info("Pipeline: Detecting language")
        detected = self.detect_language_simple(normalized)

        target = "EN" if detected == "ES" else "ES"

        logger.info("Pipeline: Applying glossary placeholders")
        with_glossary = self.glossary.apply_placeholders(normalized)

        logger.info("Pipeline: Applying technical protection")
        protected = self.protector.protect(with_glossary)

        logger.info("Pipeline: Calling DeepL API")
        translated = self._call_deepl(protected, target)

        logger.info("Pipeline: Restoring technical protection")
        restored = self.protector.unprotect(translated)

        logger.info("Pipeline: Restoring glossary placeholders")
        final = self.glossary.restore_placeholders(restored)

        return {
            "translated_text": final,
            "detected_source": detected
        }
