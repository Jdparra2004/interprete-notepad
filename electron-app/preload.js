const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
    translate: (payload) => ipcRenderer.invoke('translate', payload)
});

// forward translate to main so we can centralize (we will implement handler in main if needed)
// but for simplicity we'll call backend from renderer via fetch directly (no Node access).
