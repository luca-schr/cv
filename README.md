# CV — Lucas Schrever

Markdown + PDF adapté à chaque offre.

## Usage

```powershell
cd "D:\digital projects\_Projects\cv"

# 1. Créer jobs/ma-offre.txt  (URL ou texte collé de l'offre)
# 2. Générer
.\cv.ps1 ma-offre

# → output/cv-ma-offre.md + .pdf
```

Le nom de la commande = nom du fichier dans `jobs/` sans `.txt`  
(`.\cv.ps1 webmaster` → `jobs/webmaster.txt`)

```powershell
.\cv.ps1 ma-offre -NoLlm    # sans Ollama (plus rapide)
.\cv.ps1 ma-offre -MdOnly   # Markdown seulement
.\cv.ps1 -Master            # régénère cv.md
```

**Terminal :** `LLM : réécriture appliquée` = Ollama OK · `LLM indisponible` = fallback tags.

## Pandoc manuel

```powershell
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\mingw64\bin"
pandoc output/cv-ma-offre.md -o output/cv-ma-offre.pdf --pdf-engine=weasyprint --css=style.css
```

Depuis la racine du projet. Idéal après édition manuelle du `.md`.

## Installation (une fois)

Python 3.14+, [Pandoc](https://pandoc.org/), [WeasyPrint](https://weasyprint.org/) + MSYS2, [Ollama](https://ollama.com).

```powershell
python -m pip install -r requirements.txt
ollama pull llama3.2
```

Ollama doit tourner en arrière-plan. Pas de clé API.

Si `pandoc` / `weasyprint` introuvables :

```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
$env:WEASYPRINT_DLL_DIRECTORIES = "C:\msys64\mingw64\bin"
```

## Contenu du CV

Éditer **`cv-data.yaml`**, puis `.\cv.ps1 -Master` et `.\cv.ps1 ma-offre`.

Config : `config/llm.yaml` (Ollama), `config/analysis.yaml` (tags).

## Git

Ignorés : `jobs/`, `output/`, `*.pdf`.
