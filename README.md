# CV — Lucas Schrever

Génère un CV **Markdown + PDF** adapté à chaque offre d'emploi.

---

## Parcours rapide (au quotidien)

```powershell
cd "D:\digital projects\_Projects\cv"

# 1. Coller l'offre dans jobs/ma-offre.txt  (URL ou texte brut)
# 2. Générer le CV
.\cv.ps1 ma-offre

# 3. Récupérer le résultat
#    output/cv-ma-offre.md
#    output/cv-ma-offre.pdf
```

Le nom passé à `cv.ps1` doit correspondre au fichier dans `jobs/` **sans** `.txt` :

| Commande | Fichier attendu |
|----------|-----------------|
| `.\cv.ps1 webmaster` | `jobs/webmaster.txt` |
| `.\cv.ps1 webmaster-integrateur-wordpress` | `jobs/webmaster-integrateur-wordpress.txt` |

### Ce que fait le script

1. Lit l'offre (`jobs/*.txt`)
2. Détecte titre et mots-clés
3. **Ollama** reformule profil et bullets (si activé)
4. Applique des **garde-fous** (pas de techno ou fait inventé)
5. Exporte `.md` + `.pdf` dans `output/`

### Lire le résultat dans le terminal

| Message | Signification |
|---------|---------------|
| `LLM : réécriture appliquée` | Ollama a répondu, CV adapté |
| `Attention : LLM indisponible` | Ollama arrêté → tri par mots-clés seulement |
| `Attention : Bullet … rejetée` | Garde-fou → texte source conservé |

### Options utiles

```powershell
.\cv.ps1 webmaster -NoLlm     # plus rapide, sans Ollama
.\cv.ps1 webmaster -MdOnly      # Markdown seulement
.\cv.ps1 -Master                # régénère cv.md (sans offre)
```

---

## Première installation (une fois)

### 1. Outils requis

| Outil | Rôle |
|-------|------|
| Python 3.14+ | Pipeline de génération |
| [Pandoc](https://pandoc.org/) | Conversion MD → PDF |
| [WeasyPrint](https://weasyprint.org/) + [MSYS2](https://www.msys2.org/) | Moteur PDF (Pango sur Windows) |
| [Ollama](https://ollama.com) | Réécriture intelligente (gratuit, local) |

```powershell
cd "D:\digital projects\_Projects\cv"
python -m pip install -r requirements.txt
```

### 2. Ollama (réécriture gratuite)

Installer Ollama, puis :

```powershell
ollama pull llama3.2
```

L'app Ollama doit tourner en arrière-plan (icône barre des tâches).  
Le script appelle `http://localhost:11434` — **pas de clé API**.

> Si la commande `ollama` n'est pas reconnue, fermer et rouvrir le terminal après l'installation. Le build fonctionne quand même tant que l'app Ollama est lancée.

### 3. Vérifier que tout est OK

```powershell
python --version
pandoc --version
weasyprint --version
```

Si une commande manque, recharger le PATH :

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\mingw64\bin"
```

---

## Ajouter une offre

Créer `jobs/nom-offre.txt` avec **l'une de ces formes** :

**URL :**
```
https://fr.indeed.com/viewjob?jk=...
```

**Texte collé** (recommandé si Indeed bloque le fetch) :
```
Webmaster / Intégrateur WordPress (H/F)
…
```

Puis :

```powershell
.\cv.ps1 nom-offre
```

---

## Modifier le contenu du CV

Éditer **`cv-data.yaml`** (source de vérité), pas `cv.md` au quotidien.

```powershell
.\cv.ps1 -Master          # régénère cv.md
.\cv.ps1 ma-offre         # régénère le CV ciblé
```

Chaque bullet ou compétence peut avoir des `tags` pour le matching avec les offres.

---

## Configuration

### LLM — `config/llm.yaml`

```yaml
enabled: true
provider: ollama
model: llama3.2
base_url: http://localhost:11434
temperature: 0.2
```

- `enabled: false` ou `-NoLlm` → tri par tags, sans réécriture
- OpenAI possible (`provider: openai` + `OPENAI_API_KEY`) mais **payant** — Ollama suffit

### Analyse — `config/analysis.yaml`

Tags, filtres de bruit, règles de scoring. À modifier si de faux positifs apparaissent.

---

## Structure du projet

```
cv-data.yaml              Contenu du CV
config/
  analysis.yaml           Règles d'analyse des offres
  llm.yaml                Config Ollama / OpenAI
cv_builder/               Modules Python (analyse, rendu, garde-fous)
build.py                  Point d'entrée
cv.ps1                    Raccourci Windows
style.css                 Mise en page PDF
jobs/                     Une offre par fichier .txt
output/                   CV générés (gitignored)
```

---

## Git

Versionnés : `cv-data.yaml`, `build.py`, `style.css`, `cv.md`, `jobs/`, photo.

Ignorés : `*.pdf`, `output/`.
