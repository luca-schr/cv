# CV Generator v1

Vue 3 + Express + SQLite — **sans Ollama**.

## Prérequis

- Node.js 20+
- [Pandoc](https://pandoc.org/) + [WeasyPrint](https://weasyprint.org/) pour l’export PDF

## Structure

```
cv/
├── client/          # Vue 3 + Vite
├── server/          # Express + better-sqlite3
│   ├── assets/      # photo PDF
│   └── style.css    # styles Pandoc/WeasyPrint
├── data/cv.db       # SQLite (créé au démarrage)
└── README.md
```

## Modèle SQL

- **categories** — `name` en anglais (`developer`, `manager`, `expert`, `consultant`), `label_fr` pour l’UI
- **profiles** — intitulé (ex. *Développeur fullstack .NET/React*), `is_default`, markdown FR/EN, keywords pour le matching

Profil par défaut seed : **Développeur fullstack .NET/React**.

## Démarrage

```bash
# Backend
cd server
npm install
npm run dev

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
5. **Analyser le poste** → meilleur profil par mots-clés, sinon *« Nécessite un nouveau profil »*
6. **Télécharger PDF** → Pandoc + WeasyPrint

## API

| Route | Description |
|-------|-------------|
| `GET /api/categories` | Liste catégories |
| `GET /api/profiles?q=&category=` | Liste / filtre |
| `GET /api/profiles/:id` | Détail |
| `GET /api/profiles/default` | Profil `is_default` |
| `DELETE /api/profiles/:id` | Suppression |
| `POST /api/analyze` | Matching offre → profil |
| `POST /api/export/pdf` | Export PDF |
