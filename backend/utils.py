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
