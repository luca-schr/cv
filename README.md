# CV

Markdown enregistré, exporté en PDF A4 d’une page.

## Prérequis

| Outil | Minimum |
| --- | --- |
| Python | 3.11 |
| Node.js | 20.19 |
| Pandoc | 3 |
| WeasyPrint | 62 |

WeasyPrint s’appuie sur Pango, Cairo et GDK-PixBuf. Sous Debian ou Ubuntu : `weasyprint` (paquet), ou les bibliothèques `libpango-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`.

Python, à installer dans le venv : FastAPI 0.115, Uvicorn 0.32, Pydantic 2.10, pypdf 5.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd client && npm install && npm run build && cd ..
```

## Lancer

```bash
make run
```

Interface : http://127.0.0.1:8000

Front en rechargement : `cd client && npm run build` une fois le serveur lancé, ou `cd client && npm run dev` (port 5173) pendant l’édition.

## Export

`POST /api/export/pdf`

Fichier : `lucas-schrever-[poste][-en]`

Les dates restent dans le titre du poste. À l’export, les mois passent en toutes lettres si la ligne a la place ; sinon ils restent abrégés.

## Code

```
app/main.py            application, fichiers statiques
app/db.py              SQLite, markdown FR et EN
app/selectprofile/     GET /api/selectprofile
app/applydefault/      POST /api/applydefault
app/export/            POST /api/export/pdf
data/cv.sqlite         données
```
