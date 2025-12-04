# backend/app.py
# -*- coding: utf-8 -*-
"""
Flask backend for Interprete Notepad
- Local server at 127.0.0.1:PORT
- /translate endpoint implements the glossary-priority translation pipeline:
    * Load glossary from glossary.db (if exists) or glossary.json
    * Detect source language (es/en) with a simple deterministic heuristic
    * Replace glossary matches with placeholders (priority)
    * Send remaining text to DeepL (if API key present)
    * Reconstruct final text replacing placeholders with glossary-driven outputs
- Returns JSON: { "translated_text": "...", "detected_source": "es" }
"""
from flask import Flask, request, jsonify
import os
import json
import re
import sqlite3
import requests
import logging

# ---- Configuration / Defaults ----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
GLOSSARY_JSON_PATH = os.path.join(BASE_DIR, "glossary.json")
GLOSSARY_DB_PATH = os.path.join(BASE_DIR, "glossary.db")

# Default runtime settings
DEFAULT_PORT = 5000
DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"  # may vary by plan

# ---- Logging ----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interprete-backend")

# ---- Load config.json (if exists) ----
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
    except Exception as e:
        logger.warning("Could not load config.json: %s", e)

DEEPL_API_KEY = CONFIG.get("DEEPL_API_KEY") or os.environ.get("DEEPL_API_KEY")
PORT = int(CONFIG.get("PORT", DEFAULT_PORT))

# ---- Utilities: language detection (simple deterministic) ----
def detect_language_simple(text: str) -> str:
    """
    Returns 'es' or 'en'. Heuristic:
    - Presence of accented characters or 'ñ' strongly suggests Spanish.
    - Presence of many common English words suggests English.
    - Fallback to Spanish for empty or ambiguous input.
    """
    if not text or text.strip() == "":
        return "es"
    text_lower = text.lower()
    # quick accent/ñ check
    if re.search(r"[áéíóúüñ]", text_lower):
        return "es"
    # common words heuristic
    english_common = ["the", "and", "is", "patient", "dr", "mg", "ml", "iv", "bp"]
    english_hits = sum(1 for w in english_common if re.search(r"\b" + re.escape(w) + r"\b", text_lower))
    spanish_common = ["el", "la", "y", "es", "paciente", "mg", "ml", "intravenosa", "presión"]
    spanish_hits = sum(1 for w in spanish_common if re.search(r"\b" + re.escape(w) + r"\b", text_lower))
    if english_hits > spanish_hits:
        return "en"
    if spanish_hits > english_hits:
        return "es"
    # fallback by ratio of ASCII alphabetical vs accented (if any accents handled above)
    ascii_letters = sum(1 for ch in text if ord(ch) < 128 and ch.isalpha())
    total_letters = sum(1 for ch in text if ch.isalpha())
    if total_letters == 0:
        return "es"
    if ascii_letters / total_letters > 0.85:
        return "en"
    return "es"

# ---- Load glossary (flexible) ----
# Internal normalized form: list of entries with keys:
#   { "term_es": "...", "term_en": "...", "acronym": "..." }
def load_glossary() -> list:
    entries = []
    # If sqlite DB exists, load from it
    if os.path.exists(GLOSSARY_DB_PATH):
        try:
            conn = sqlite3.connect(GLOSSARY_DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT term_es, term_en, acronym FROM glossary")
            rows = cur.fetchall()
            for r in rows:
                entries.append({
                    "term_es": (r[0] or "").strip(),
                    "term_en": (r[1] or "").strip(),
                    "acronym": (r[2] or "").strip() if r[2] else None
                })
            conn.close()
            logger.info("Loaded %d glossary entries from sqlite db.", len(entries))
            return entries
        except Exception as e:
            logger.warning("Could not read glossary.db (%s); falling back to glossary.json. Error: %s", GLOSSARY_DB_PATH, e)

    # fallback: load from glossary.json if exists
    if os.path.exists(GLOSSARY_JSON_PATH):
        try:
            with open(GLOSSARY_JSON_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # Accept two JSON shapes:
            # 1) dict mapping keys -> { "en": "...", "es": "..." } (legacy)
            # 2) list of objects [{ "term_es": "...", "term_en": "...", "acronym": "..." }, ...]
            if isinstance(raw, dict):
                for k, v in raw.items():
                    # Try to infer fields
                    term_es = v.get("es") or v.get("term_es") or (k if bool(re.search(r"[áéíóúñ]|[a-záéíóúñ]+", k, re.I)) else None)
                    term_en = v.get("en") or v.get("term_en") or None
                    acronym = None
                    # if key looks like an acronym (all letters upper and short) use that
                    if k.isupper() and len(k) <= 6:
                        acronym = k
                        # infer which side is which by presence of accented characters
                        if term_es and not term_en:
                            # k is likely acronym, v contains translations
                            pass
                    entries.append({
                        "term_es": term_es or "",
                        "term_en": term_en or "",
                        "acronym": acronym
                    })
            elif isinstance(raw, list):
                for item in raw:
                    entries.append({
                        "term_es": item.get("term_es","").strip(),
                        "term_en": item.get("term_en","").strip(),
                        "acronym": (item.get("acronym") or "").strip() or None
                    })
            logger.info("Loaded %d glossary entries from glossary.json", len(entries))
        except Exception as e:
            logger.warning("Could not load glossary.json: %s", e)
    else:
        logger.warning("No glossary.db or glossary.json found. Glossary will be empty.")
    return entries

# Build glossary index for efficient matching: sorted by longest phrase first
GLOSSARY = load_glossary()
# Prepare patterns list: for each entry create regex patterns for term_es, term_en, acronym (word boundary)
_glossary_patterns = []
for entry in GLOSSARY:
    # order: match longer phrases first (to avoid partial matches)
    # compile patterns case-insensitive, unicode-aware
    if entry.get("term_es"):
        _glossary_patterns.append( (len(entry["term_es"]), re.compile(r"\b" + re.escape(entry["term_es"]) + r"\b", flags=re.IGNORECASE|re.UNICODE), "es", entry) )
    if entry.get("term_en"):
        _glossary_patterns.append( (len(entry["term_en"]), re.compile(r"\b" + re.escape(entry["term_en"]) + r"\b", flags=re.IGNORECASE|re.UNICODE), "en", entry) )
    if entry.get("acronym"):
        _glossary_patterns.append( (len(entry["acronym"]), re.compile(r"\b" + re.escape(entry["acronym"]) + r"\b", flags=re.IGNORECASE|re.UNICODE), "acronym", entry) )

# sort descending by length so longest matches are applied first
_glossary_patterns.sort(key=lambda x: x[0], reverse=True)

# ---- Placeholder helper ----
def generate_placeholder(idx: int) -> str:
    return f"<<<GL{idx}>>>"

# ---- Apply glossary replacements to text, returning (placeholder_text, mapping, detected_hits) ----
def apply_glossary_placeholders(text: str, src_lang: str):
    """
    Replaces occurrences of glossary terms (matching source language) with placeholders.
    Returns:
        - text_with_placeholders: str
        - placeholder_map: dict placeholder -> replacement_text (what should appear in final translated output)
        - had_hits: bool
    Behavior:
        - If src_lang == 'es' and matches a Spanish term: replacement is:
            if acronym exists -> "ACR (term_en)"
            else -> "term_en"
        - If src_lang == 'en' and matches an English term or acronym: replacement is:
            -> "term_es"
        - Matching is case-insensitive and respects word boundaries.
    """
    placeholder_map = {}
    idx = 0
    text_out = text

    # We loop over patterns; for each match we replace all occurrences that are not already placeholders.
    # To avoid double-replacement complexity, we'll perform a single pass per pattern.
    for _, pattern, p_type, entry in _glossary_patterns:
        def _repl(m):
            nonlocal idx
            # If this exact match is already inside a placeholder, skip
            span_text = m.group(0)
            # generate replacement according to src_lang and type
            if src_lang == "es":
                # match should be Spanish term
                # replacement to English; prefer acronym + (english) if acronym present
                acronym = entry.get("acronym")
                term_en = entry.get("term_en") or ""
                if acronym:
                    repl = f"{acronym} ({term_en})" if term_en else f"{acronym}"
                else:
                    repl = term_en or span_text
            else:  # src_lang == "en"
                # match is English term or acronym -> return Spanish term
                term_es = entry.get("term_es") or ""
                repl = term_es or span_text
            placeholder = generate_placeholder(idx)
            placeholder_map[placeholder] = repl
            idx += 1
            return placeholder

        # Apply replacement
        # But avoid replacing placeholders if they already exist in text_out
        # So we call sub on current text_out
        try:
            text_out = pattern.sub(_repl, text_out)
        except Exception as e:
            logger.debug("Pattern replace issue: %s", e)
            continue

    had_hits = len(placeholder_map) > 0
    return text_out, placeholder_map, had_hits

# ---- DeepL call helper ----
def call_deepl(text: str, src: str, tgt: str) -> str:
    """
    Calls DeepL translate endpoint. Returns translated text.
    If DEEPL_API_KEY is not configured or an error happens, raises an exception.
    """
    if not DEEPL_API_KEY:
        raise RuntimeError("DeepL API key not configured.")
    data = {
        "auth_key": DEEPL_API_KEY,
        "text": text,
        "source_lang": src.upper(),
        "target_lang": tgt.upper()
    }
    try:
        resp = requests.post(DEEPL_API_URL, data=data, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        # expected structure: { "translations": [ { "detected_source_language": "...", "text": "..." } ] }
        translations = payload.get("translations")
        if translations and len(translations) > 0:
            return translations[0].get("text", "")
        else:
            raise RuntimeError("DeepL returned unexpected structure.")
    except Exception as e:
        logger.warning("DeepL request failed: %s", e)
        raise

# ---- Reconstruct placeholders into final text ----
def reconstruct_text(translated_with_placeholders: str, placeholder_map: dict) -> str:
    """
    Replace placeholders in the translated text with the intended glossary replacements.
    """
    out = translated_with_placeholders
    # simple replacement: placeholders are unique and do not overlap
    for ph, repl in placeholder_map.items():
        out = out.replace(ph, repl)
    return out

# ---- Flask app ----
app = Flask(__name__)
@app.route("/", methods=["GET"])
def health_check():
    return {
        "status": "ok",
        "message": "Interpreter Notepad backend running"
    }

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "backend": "interprete-notepad", "glossary_entries": len(GLOSSARY)}), 200

@app.route("/translate", methods=["POST"])
def translate():
    payload = request.get_json(silent=True)
    if not payload or "text" not in payload:
        return jsonify({"error": "Missing 'text' in JSON body."}), 400
    text = payload.get("text", "")
    text = text.strip()
    # detect language
    detected = detect_language_simple(text)
    src = detected
    tgt = "en" if src == "es" else "es"

    # apply glossary replacements => placeholders + map
    placeholder_text, placeholder_map, had_hits = apply_glossary_placeholders(text, src)

    # Decide if we need to call DeepL
    # If placeholder_text == text and no placeholders were applied -> we still may want to call DeepL
    # If placeholder_text contains placeholders, DeepL will usually keep placeholders intact, so safe to send.
    translated_result = None
    try:
        # Only call DeepL if there is something non-empty (and key is present)
        if DEEPL_API_KEY and placeholder_text.strip():
            translated_result = call_deepl(placeholder_text, src, tgt)
        else:
            translated_result = None
    except Exception as e:
        logger.info("DeepL not used or failed: %s", e)
        translated_result = None

    # If DeepL succeeded, translated_result contains text with placeholders preserved.
    # If not, fallback: set translated_result = placeholder_text (i.e., original segments left untranslated)
    if translated_result is None:
        # fallback: do not translate remotely; we'll return the original text with glossary replacements applied where matched.
        translated_with_placeholders = placeholder_text
    else:
        translated_with_placeholders = translated_result

    # Now reconstruct placeholders -> final desired glossary-driven strings
    final_text = reconstruct_text(translated_with_placeholders, placeholder_map)

    # Final cleanup: collapse multiple spaces, fix spaces before punctuation if any introduced
    final_text = re.sub(r"\s+([,.;:!?])", r"\1", final_text)
    final_text = re.sub(r"\s{2,}", " ", final_text).strip()

    return jsonify({"translated_text": final_text, "detected_source": detected}), 200

# ---- Run (when executed directly) ----
if __name__ == "__main__":
    logger.info("Starting Interprete Notepad backend on 127.0.0.1:%d", PORT)
    # Note: set host=127.0.0.1 to avoid exposing on network
    app.run(host="127.0.0.1", port=PORT, debug=False)
