# CV Generator v1

Vue 3 + **FastAPI** + SQLite.

## Prérequis

- Node.js 20+ (client Vue uniquement)
- Python 3.11+
- [Pandoc](https://pandoc.org/) + [WeasyPrint](https://weasyprint.org/) pour l’export PDF
- (optionnel) [Ollama](https://ollama.com/) — `server/config/llm.yaml`

## Structure

```
cv/
├── client/              # Vue 3 + Vite
├── server/
│   ├── app/             # FastAPI
│   ├── assets/          # photo PDF
│   ├── config/llm.yaml
│   ├── style.css        # CSS A4 (WeasyPrint)
│   └── requirements.txt
├── data/cv.db           # SQLite (créé au démarrage)
└── README.md
```

## Démarrage

```bash
# Backend
cd server
python -m venv .venv
# Windows: .venv\Scripts\activate
# Unix:    source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd client
npm install
npm run dev
```

UI : http://localhost:5173 (proxy `/api` → `:8000`)

## Fonctions v1

1. Recherche + filtre catégorie sur les profils
2. Clic profil → charge le markdown dans le CV
3. Suppression (× rouge + confirm) — le défaut n’est pas supprimable
4. **En anglais** → bascule markdown EN
5. **Analyser le poste** → matching + adaptation (Ollama ou local)
6. **Télécharger PDF** → Pandoc + WeasyPrint + pypdf (fit A4 1 page)

## API

| Route | Description |
|-------|-------------|
| `GET /api/categories` | Liste catégories |
| `GET /api/profiles?q=&category=` | Liste / filtre |
| `GET /api/profiles/:id` | Détail |
| `GET /api/profiles/default` | Profil `is_default` |
| `DELETE /api/profiles/:id` | Suppression |
| `POST /api/analyze` | Matching offre → profil adapté |
| `POST /api/export/pdf` | Export PDF |
| `GET /api/llm/status` | État Ollama |
