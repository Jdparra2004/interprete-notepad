// electron-app/api.js
const API_BASE = "http://127.0.0.1:5000";

async function translateText(text) {
    const resp = await fetch(`${API_BASE}/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json; charset=utf-8" },
        body: JSON.stringify({ text })
    });
    if (!resp.ok) {
        const err = await resp.json().catch(()=>({error: 'unknown'}));
        throw new Error(err.error || `HTTP ${resp.status}`);
    }
    return resp.json();
}

module.exports = { translateText };
