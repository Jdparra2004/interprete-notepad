// =============================
// 0. Validar conexión con Backend
// =============================
fetch("http://127.0.0.1:5000/health")
    .then(r => r.json())
    .then(data => console.log("%cBackend conectado OK:", "color: green", data))
    .catch(err => console.error("%cError conectando al backend:", "color: red", err));

// =============================
// 1. Config
// =============================
const API_BASE = "http://127.0.0.1:5000";

// =============================
// 2. Referencias
// =============================
const el = {
    input: document.getElementById("input"),
    output: document.getElementById("output"),
    translateBtn: document.getElementById("translateBtn"),
    clearBtn: document.getElementById("clearBtn"),
    copyBtn: document.getElementById("copyBtn"),
    langLabel: document.getElementById("langLabel"),
    useGlossary: document.getElementById("useGlossary"),
};

// =============================
// UTILIDAD: Normalizar texto EXACTO como backend
// =============================
function normalizeFrontend(text) {
    return text
        .replace(/\x00/g, "")
        .replace(/\u200b/g, "")
        .replace(/\ufeff/g, "")
        .normalize("NFC")
        .trim();
}

// =============================
// 3. Función principal: traducir
// =============================
async function translate() {
    let rawText = el.input.value;
    let text = normalizeFrontend(rawText);

    if (!text)
        return alert("Escribe algo para traducir.");

    el.translateBtn.disabled = true;
    el.translateBtn.textContent = "Traduciendo...";

    try {
        const resp = await fetch(`${API_BASE}/translate`, {
            method: "POST",
            headers: { "Content-Type": "application/json; charset=utf-8" },
            body: JSON.stringify({
                text,
                use_glossary: el.useGlossary?.checked ?? true
            })
        });

        const payload = await resp.json();

        if (!resp.ok)
            throw new Error(payload.error || "Error al traducir");

        el.output.value = payload.translated_text;
        el.langLabel.textContent = "Idioma detectado: " + (payload.detected_source || "—");

    } catch (err) {
        console.error(err);
        alert("Error: " + (err.message || err));
    } finally {
        el.translateBtn.disabled = false;
        el.translateBtn.textContent = "Traducir →";
    }
}

// =============================
// 4. Eventos
// =============================
el.translateBtn.addEventListener("click", translate);

el.clearBtn.addEventListener("click", () => {
    el.input.value = "";
    el.output.value = "";
    el.langLabel.textContent = "Idioma detectado: —";
});

el.copyBtn.addEventListener("click", async () => {
    try {
        await navigator.clipboard.writeText(el.output.value || "");
        alert("Copiado al portapapeles");
    } catch {
        alert("No se pudo copiar");
    }
});

// Atajo Ctrl+Enter
el.input.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") translate();
});
