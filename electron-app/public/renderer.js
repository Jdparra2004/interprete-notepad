// Validar conexión Backend
fetch("http://127.0.0.1:5000/health")
    .then(r => r.json())
    .then(data => console.log("Backend conectado:", data))
    .catch(err => console.error("Error conectando al backend:", err));


// renderer.js (browser context)
const API_BASE = "http://127.0.0.1:5000";

const el = {
    input: document.getElementById('input'),
    output: document.getElementById('output'),
    translateBtn: document.getElementById('translateBtn'),
    clearBtn: document.getElementById('clearBtn'),
    copyBtn: document.getElementById('copyBtn'),
    langLabel: document.getElementById('langLabel'),
    useGlossary: document.getElementById('useGlossary'),
    };

    async function translate() {
    const text = el.input.value.trim();
    if (!text) return alert("Escribe algo para traducir.");

    el.translateBtn.disabled = true;
    el.translateBtn.textContent = "Traduciendo...";

    try {
        const resp = await fetch(`${API_BASE}/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ text })
        });
        const payload = await resp.json();
        if (!resp.ok) throw new Error(payload.error || "Error al traducir");
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

    el.translateBtn.addEventListener('click', translate);
    el.clearBtn.addEventListener('click', () => { el.input.value = ''; el.output.value = ''; el.langLabel.textContent = 'Idioma detectado: —'; });
    el.copyBtn.addEventListener('click', async () => {
    try {
        await navigator.clipboard.writeText(el.output.value || '');
        alert('Copiado al portapapeles');
    } catch (e) {
        alert('No se pudo copiar');
    }
    });

    // Ctrl+Enter to translate
    el.input.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        translate();
    }
});
