# CV Generator v2

Générateur de CV adaptés aux offres — **FastAPI** + **Vue 3** + **Ollama** + export PDF A4 une page.

## Prérequis

- Python 3.11+
- Node.js 20+
- [Ollama](https://ollama.com/) avec `llama3.2` (`ollama pull llama3.2`)
- [Pandoc](https://pandoc.org/) + [WeasyPrint](https://weasyprint.org/) pour l'export PDF
- Windows : définir `WEASYPRINT_DLL_DIRECTORIES` si besoin (voir `server/app/config.py`)

## Structure

```
cv/
├── server/                 # API FastAPI
│   ├── app/                # routes, services, modèles SQLite
│   ├── assets/             # médias CV uniquement (photo PDF, favicon API)
│   ├── config/llm.yaml
│   └── style.css           # typo PDF A4 (proportions 10/8/5/77 %)
├── client/                 # UI Vue 3 + Vite
│   ├── public/             # fichiers servis tels quels (/favicon.svg…)
│   └── src/assets/         # images/CSS importés par Vite (logo UI, app.css)
├── data/cv.db              # SQLite (créé au démarrage)
└── README.md
```

### Où vont les fichiers ?

| Besoin | Dossier | Exemple |
|--------|---------|---------|
| Photo sur le PDF | `server/assets/` | `lucas-schrever.jpg` (chemin relatif Pandoc : `assets/…`) |
| Logo / favicon de l’UI | `client/public/` ou `client/src/assets/` | `favicon.svg`, `logo.png` importé dans Vue |
| **Ne pas** dupliquer | pas de `assets/` à la racine | un seul `server/assets/` pour le CV |

En dev, Vite (port 5173) ne proxy que `/api` vers le backend. L’UI et le PDF n’utilisent pas le même chemin HTTP.

## Développement

### Backend

```bash
cd server
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd client
npm install
npm run dev
```

Ouvrir http://localhost:5173 — le proxy Vite redirige `/api` vers le backend.

## Utilisation

1. Coller une **fiche de poste** dans le champ gauche
2. Ajuster **température** et **English** si besoin
3. **Générer CV** (Ollama analyse l'offre, adapte le profil, ajuste le PDF sur 1 page)
4. Éditer le markdown si nécessaire
5. **Télécharger PDF**
6. **Historique** : clic sur une génération pour recharger le markdown

## API

| Route | Description |
|-------|-------------|
| `POST /api/generate` | Génération CV |
| `POST /api/export/pdf` | Export PDF |
| `GET /api/generations` | Historique |
| `GET /api/generations/{id}` | Détail génération |
| `GET /api/llm/status` | Statut Ollama |
| `GET /api/profile/skills` | Skills + catégories (debug) |

## Production

```bash
cd client && npm run build
cd ../server && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

FastAPI sert `client/dist` sur `/` si le build existe.

## Modèle données

- **Profile** : corpus (expériences, formations, langues…)
- **Category** : regroupements dynamiques (Ollama / offre / seed)
- **Skill** : `level` 0–5 optionnel (`NULL` = skill issue de l'offre)
- **Generation** : historique markdown
