// main.js
const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let backendProcess = null;

function getBackendPath() {

    // --- Modo producción (instalador) ---
    const prodPath = path.join(process.resourcesPath, "backend", "app.exe");
    if (require("fs").existsSync(prodPath)) {
        console.log("Usando backend PRODUCCIÓN:", prodPath);
        return prodPath;
    }

    // --- Modo desarrollo ---
    const devPath = path.join(__dirname, "backend", "app.exe");
    console.log("Usando backend DESARROLLO:", devPath);
    return devPath;
}

function startBackend() {
    const backendPath = getBackendPath();

    backendProcess = spawn(backendPath, [], {
        detached: false,
        stdio: "ignore"
    });

    backendProcess.on("error", err => {
        console.error("Error al iniciar backend:", err);
    });
}

function stopBackend() {
    if (backendProcess) {
        backendProcess.kill();
        backendProcess = null;
    }
}

function createWindow() {
    const win = new BrowserWindow({
        width: 1100,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, "preload.js")
        }
    });

    win.loadFile("public/index.html");

    win.on("closed", () => stopBackend());
}

app.whenReady().then(() => {
    startBackend();
    createWindow();
});

app.on("window-all-closed", () => {
    stopBackend();
    if (process.platform !== "darwin") app.quit();
});
