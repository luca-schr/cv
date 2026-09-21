# CV

Profils JSON bilingues (`{fr, en}`) → aperçu markdown → PDF A4 **1 page**.

## Lancer

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd client && npm install && npm run build && cd ..
uvicorn app.main:app --reload
```

Interface : **http://127.0.0.1:8000**

Hot-reload front (React + TypeScript) : `cd client && npm run dev` (port 5173). Après un changement servi par uvicorn : `npm run build`.

L'export PDF nécessite Pandoc + WeasyPrint. L'échelle est calée en **1 rendu** si le CV tient déjà en une page (recherche dichotomique uniquement si trop long).

## Données

Identité partagée : `data/person.json`

Chaque profil : `data/profiles/*.json`

Tous les textes traduisibles sont un objet **`{ "fr": "...", "en": "..." }`**. Le français est la langue par défaut ; l'anglais n'ajoute que le suffixe `-en` au nom de fichier.

| Champ | Forme |
|---|---|
| `profile` | intitulé (`Développeur fullstack`) |
| `description` | accroche |
| `skills` | `{ label, items[] }` |
| `experiences` | `{ title, company, time, description }` |
| `formations` | `{ title, school, time, description }` |
| `certifications` | `{ title }` |
| `languages` | `{ title, level }` |

## Nommage PDF

`lucas-schrever-[poste]-[defaut|societe][-en]-vX`

Exemples : `lucas-schrever-developpeur-fullstack-defaut-v1.pdf`, `lucas-schrever-fullstack-developer-jane-en-v2.pdf`
