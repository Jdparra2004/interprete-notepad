# utils.py
import re
import unicodedata

# ---------------------------------------------------
# Normalización básica de texto en español (médico)
# ---------------------------------------------------
def normalize_spanish(text: str) -> str:
    """
    Normaliza texto en español para contexto médico:
    - Corrige términos médicos comunes sin acento
    - Limpia espacios duplicados
    - Mantiene estructura original (no reescribe frases)
    """

    if not text:
        return text

    # Normalización Unicode (previene errores raros de encoding)
    text = unicodedata.normalize("NFC", text)

    # Reglas médicas específicas (con límites de palabra)
    medical_fixes = {
        r"\bvia\b": "vía",
        r"\bintravenosa\b": "intravenosa",
        r"\bintramuscular\b": "intramuscular",
        r"\bsubcutanea\b": "subcutánea",
        r"\boral\b": "oral"
    }

    for pattern, replacement in medical_fixes.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    # Limpieza de espacios extra
    text = re.sub(r"\s{2,}", " ", text)

    return text.strip()


import re

# ---------------------------------------------------
# Aplicar glosario con placeholders
# ---------------------------------------------------
def apply_glossary_placeholders(text: str, lang: str):
    """
    Reemplaza términos del glosario por placeholders seguros.
    Retorna:
    - texto con placeholders
    - mapa placeholder -> texto final
    - flag si hubo coincidencias
    """

    from app import GLOSSARY  # cargado una sola vez en app.py

    placeholder_map = {}
    placeholder_index = 1
    had_hits = False

    for entry in GLOSSARY:
        term = entry["term_es"] if lang == "es" else entry["term_en"]
        acronym = entry.get("acronym")
        term_en = entry.get("term_en")

        if not term:
            continue

        pattern = r"\b" + re.escape(term) + r"\b"

        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            placeholder = f"__GLOSSARY_{placeholder_index}__"

            if acronym:
                replacement = f"{acronym} ({term_en})"
            else:
                replacement = term_en

            text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)

            placeholder_map[placeholder] = replacement
            placeholder_index += 1
            had_hits = True

    return text, placeholder_map, had_hits

# Restaurar el texto final
def reconstruct_text(text: str, placeholder_map: dict) -> str:
    for placeholder, final_value in placeholder_map.items():
        text = text.replace(placeholder, final_value)
    return text

