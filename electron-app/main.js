// main.js — versión completa integrada con backend.exe
const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let backendProcess = null;

function startBackend() {
    const backendPath = path.join(process.resourcesPath, "backend", "app.exe");

    console.log("Iniciando backend en:", backendPath);

    backendProcess = spawn(backendPath, [], {
        detached: false,
        stdio: "ignore"
    });

    backendProcess.on("error", (err) => {
        console.error("Error al iniciar backend:", err);
    });

    backendProcess.on("exit", (code) => {
        console.log("Backend finalizado con código:", code);
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

    win.on("closed", () => {
        stopBackend();
    });
}

app.whenReady().then(() => {
    startBackend();
    createWindow();
});

app.on("window-all-closed", () => {
    stopBackend();
    if (process.platform !== "darwin") app.quit();
});
