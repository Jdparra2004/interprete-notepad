# backend/app.py
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import os
import json
import logging
import unicodedata
import re

from core.pipeline import TranslationPipeline
from core.glossary import Glossary


# ---------------------------
# Paths / Config
# ---------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
GLOSSARY_JSON_PATH = os.path.join(BASE_DIR, "glossary.json")

DEFAULT_PORT = 5000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("interprete-backend")


# ---------------------------
# Load config.json
# ---------------------------
CONFIG = {}
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
    except Exception as e:
        logger.warning("Could not load config.json: %s", e)

DEEPL_API_KEY = CONFIG.get("DEEPL_API_KEY") or os.environ.get("DEEPL_API_KEY")
PORT = int(CONFIG.get("PORT", DEFAULT_PORT))


# ---------------------------
# Initialize Glossary
# ---------------------------
try:
    with open(GLOSSARY_JSON_PATH, "r", encoding="utf-8") as f:
        glossary_data = json.load(f)
except Exception as e:
    logger.warning("Could not load glossary.json: %s", e)
    glossary_data = []

glossary = Glossary(glossary_data)

# ---------------------------
# Initialize Pipeline
# ---------------------------
pipeline = TranslationPipeline(
    glossary=glossary,
    deepl_api_key=DEEPL_API_KEY
)


# ---------------------------
# Flask App
# ---------------------------
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

    # ---- Validate JSON ----
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid JSON format."}), 400

    if not payload or "text" not in payload:
        return jsonify({"error": "Missing 'text'"}), 400

    text = payload["text"]

    # ---- Validate type ----
    if not isinstance(text, str):
        return jsonify({"error": "'text' must be a string"}), 400

    # ---- Validate content ----
    if not text.strip():
        return jsonify({"error": "'text' cannot be empty"}), 400

    if len(text) > 5000:
        return jsonify({"error": "Text exceeds 5000 characters"}), 413

    # ---- Normalize text ----
    text = (
        text.replace("\x00", "")
            .replace("\u200b", "")
            .replace("\ufeff", "")
            .strip()
    )
    text = unicodedata.normalize("NFC", text)

    # ---------------------------
    # Run Translation Pipeline
    # ---------------------------
    try:
        result = pipeline.run(text)
        translated_text = result["translated_text"]
        detected_source = result["detected_source"]
    except Exception as e:
        logger.error("Pipeline failed: %s", e)
        return jsonify({"error": "Translation pipeline internal error"}), 500

    # ---- Return response ----
    return jsonify({
        "translated_text": translated_text,
        "detected_source": detected_source
    }), 200


# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    logger.info("Starting Interprete Notepad backend on 127.0.0.1:%d", PORT)
    app.run(host="127.0.0.1", port=PORT, debug=False)
