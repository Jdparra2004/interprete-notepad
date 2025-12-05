# core/pipeline.py
# -*- coding: utf-8 -*-
import logging
import requests
import unicodedata
from .normalizer import TextNormalizer
from .glossary import Glossary
from .protector import TextProtector

logger = logging.getLogger("pipeline")
logger.setLevel(logging.INFO)

DEEPL_URL = "https://api-free.deepl.com/v2/translate"

class TranslationPipeline:
    def __init__(self, glossary: Glossary, deepl_api_key: str = None, deepl_url: str = DEEPL_URL):
        self.glossary = glossary
        self.deepl_key = deepl_api_key
        self.deepl_url = deepl_url or DEEPL_URL
        self.normalizer = TextNormalizer()
        self.protector = TextProtector()

    def detect_language_simple(self, text: str) -> str:
        """
        Return 'es' or 'en'. Heuristic:
         - accented characters -> es
         - common english words -> en
         - fallback: ratio ascii letters -> en else es
        """
        if not isinstance(text, str) or not text.strip():
            return "es"
        t = text.lower()
        # accented characters indicate Spanish
        if any(ch in t for ch in "áéíóúüñ"):
            return "es"
        eng_common = ["the", "and", "is", "patient", "need", "requires", "dr"]
        spa_common = ["el", "la", "y", "es", "paciente", "necesita", "requer"]
        eng_hits = sum(1 for w in eng_common if f" {w} " in f" {t} ")
        spa_hits = sum(1 for w in spa_common if f" {w} " in f" {t} ")
        if eng_hits > spa_hits:
            return "en"
        if spa_hits > eng_hits:
            return "es"
        ascii_letters = sum(1 for ch in text if ord(ch) < 128 and ch.isalpha())
        total_letters = sum(1 for ch in text if ch.isalpha())
        if total_letters == 0:
            return "es"
        if ascii_letters / total_letters > 0.85:
            return "en"
        return "es"

    def _call_deepl(self, text: str, target_lang: str) -> str:
        if not self.deepl_key:
            raise RuntimeError("DeepL API key not configured.")
        payload = {
            "auth_key": self.deepl_key,
            "text": text,
            "target_lang": target_lang.upper()
        }
        resp = requests.post(self.deepl_url, data=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        translations = data.get("translations")
        if translations and len(translations) > 0:
            return translations[0].get("text", "")
        raise RuntimeError("DeepL returned unexpected response")

    def run(self, text: str) -> dict:
        logger.info("Pipeline: starting")
        # 1. normalize user text (keep accents for final output but normalize spaces etc.)
        normalized = self.normalizer.normalize(text)
        normalized = unicodedata.normalize("NFC", normalized)

        # 2. detect language -> 'es' or 'en'
        detected = self.detect_language_simple(normalized)
        logger.info("Pipeline: detected language=%s", detected)

        # 3. apply glossary placeholders based on detected source language
        # glossary.apply_placeholders returns (text_with_placeholders, placeholder_map, had_hits)
        with_placeholders, placeholder_map, had_hits = self.glossary.apply_placeholders(normalized, detected)
        logger.debug("Pipeline: with_placeholders=%s", with_placeholders)
        logger.debug("Pipeline: placeholder_map=%s", placeholder_map)

        # 4. protect technical tokens (units, acronyms patterns)
        protected = self.protector.protect(with_placeholders)
        logger.debug("Pipeline: protected text=%s", protected)

        # 5. call DeepL (if configured) for the rest (target depends on detected)
        translated = protected
        try:
            if self.deepl_key and protected.strip():
                target = "EN" if detected == "es" else "ES"
                logger.info("Pipeline: calling DeepL target=%s", target)
                translated = self._call_deepl(protected, target)
            else:
                logger.info("Pipeline: DeepL key missing or empty text -> skipping DeepL")
        except Exception as e:
            logger.warning("Pipeline: DeepL failed: %s. Falling back to protected text.", e)
            translated = protected

        # 6. unprotect technical tokens
        restored_tech = self.protector.unprotect(translated)
        logger.debug("Pipeline: restored tech=%s", restored_tech)

        # 7. restore glossary placeholders with their final glossary-driven values
        final = self.glossary.restore_placeholders(restored_tech, placeholder_map)
        logger.info("Pipeline: finished")
        return {"translated_text": final, "detected_source": detected}
