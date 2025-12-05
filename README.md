# Interpreter_Function

App de notas para interpretes con traducción directa

interprete-notepad/
├─ electron-app/
│  ├─ package.json
│  ├─ main.js

│  ├─ package-lock.json
│  ├─ api.js

│  ├─ preload.js
│  ├─ public/
│  │  ├─ index.html
│  │  ├─ styles.css
│  │  └─ renderer.js
│
├─ backend/
│  ├─ app.py                       # Flask + endpoints
│  ├─ glossary.json                # la base de términos
│  ├─ config.json                  # API keys, flags
│  ├─ requirements.txt
│  │
│  ├─ core/                        # ← NUEVA carpeta modular
│  │  ├─ normalizer.py             # limpiar acentos, estandarizar
│  │  ├─ glossary.py               # cargar + indexar glosario
│  │  ├─ protector.py              # blindaje (tokens seguros)
│  │  ├─ pipeline.py               # flujo general de traducción
│  │  └─ __init__.py
│  │
│  ├─ utils.py                     # quedará solo con cosas pequeñas
│  └─ __init__.py
│
├─ build/
│  └─ scripts (electron-builder, pyinstaller)
│
└─ README.md
