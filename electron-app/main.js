const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

function createWindow() {
    const win = new BrowserWindow({
        width: 980,
        height: 720,
        minWidth: 860,
        minHeight: 560,
        webPreferences: {
        preload: path.join(__dirname, 'preload.js'),
        contextIsolation: true,
        nodeIntegration: false
        },
        backgroundColor: '#FFF9F2',
    });

    win.loadFile(path.join(__dirname, 'public', 'index.html'));
    // win.webContents.openDevTools();
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
    });
    