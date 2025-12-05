# backend/app.py
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import os
import json
import logging
import unicodedata
import re
import sys

from core.pipeline import TranslationPipeline
from core.glossary import Glossary

# ============================================================
# 1. Resolver rutas reales incluso cuando se empaqueta con PyInstaller
# ============================================================

def resource_path(relative_path):
    """
    Devuelve la ruta absoluta tanto en modo desarrollo como empaquetado.
    PyInstaller coloca los archivos en sys._MEIPASS.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

# ---------------------------
# Paths / Config
# ---------------------------
CONFIG_PATH = resource_path("config.json")
GLOSSARY_JSON_PATH = resource_path("glossary.json")

DEFAULT_PORT = 5000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interprete-backend")

# ============================================================
# 2. Load config.json (API key y settings)
# ============================================================
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
    except Exception as e:
        logger.warning("Could not load config.json: %s", e)

DEEPL_API_KEY = CONFIG.get("DEEPL_API_KEY") or os.environ.get("DEEPL_API_KEY")
PORT = int(CONFIG.get("PORT", DEFAULT_PORT))

# ============================================================
# 3. Load glossary.json
# ============================================================
try:
    with open(GLOSSARY_JSON_PATH, "r", encoding="utf-8") as f:
        glossary_data = json.load(f)
except Exception as e:
    logger.warning("Could not load glossary.json: %s", e)
    glossary_data = []

glossary = Glossary(glossary_data)

# ============================================================
# 4. Initialize pipeline
# ============================================================
pipeline = TranslationPipeline(
    glossary=glossary,
    deepl_api_key=DEEPL_API_KEY
)

# ============================================================
# 5. Flask App
# ============================================================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def root():
    return {
        "status": "ok",
        "message": "Interpreter Notepad backend running"
    }

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "backend": "interprete-notepad",
        "glossary_entries": glossary.size()
    }), 200

@app.route("/translate", methods=["POST"])
def translate():
    logger.info("\n>>> ENTERED TRANSLATE ENDPOINT <<<\n")

    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON format."}), 400

    if not payload or "text" not in payload:
        return jsonify({"error": "Missing 'text'"}), 400

    text = payload["text"]

    if not isinstance(text, str):
        return jsonify({"error": "'text' must be a string"}), 400

    if not text.strip():
        return jsonify({"error": "'text' cannot be empty"}), 400

    if len(text) > 5000:
        return jsonify({"error": "Text exceeds 5000 characters"}), 413

    text = (
        text.replace("\x00", "")
            .replace("\u200b", "")
            .replace("\ufeff", "")
            .strip()
    )
    text = unicodedata.normalize("NFC", text)

    try:
        result = pipeline.run(text)
        translated_text = result["translated_text"]
        detected_source = result["detected_source"]
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        return jsonify({"error": "Translation pipeline internal error"}), 500

    return jsonify({
        "translated_text": translated_text,
        "detected_source": detected_source
    }), 200


@app.post("/debug_glossary")
def debug_glossary():
    data = request.json.get("text", "")

    src = pipeline.detect_language_simple(data)
    pre, mapping, hits = glossary.apply_placeholders(data, src)

    return {
        "input": data,
        "detected_lang": src,
        "pre_with_placeholders": pre,
        "mapping": mapping,
        "hits": hits
    }

# ============================================================
# 6. Run
# ============================================================
if __name__ == "__main__":
    logger.info("Starting Interprete Notepad backend on 127.0.0.1:%d", PORT)
    app.run(host="127.0.0.1", port=PORT, debug=False)
