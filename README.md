# Interpreter_Function

App de notas para interpretes con traducción directa

interprete-notepad/
├─ electron-app/
│  ├─ package.json
│  ├─ main.js                 # bootstrap de Electron
│  ├─ public/
│  │  ├─ index.html
│  │  ├─ styles.css
│  │  └─ renderer.js          # UI logic
├─ backend/
│  ├─ app.py                  # Flask API
│  ├─ glossary.json           # glosario local (embebido)
│  ├─ config.json             # settings, DeepL key (local)
│  ├─ requirements.txt
│  └─ utils.py                # tokenizador, helpers
├─ build/
│  └─ scripts for packaging (electron-builder, pyinstaller)
└─ README.md
