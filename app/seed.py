"""Profil CV par défaut — template fullstack JS."""

from __future__ import annotations

# Technos racines : socle obligatoire du CV (réorganisable par l'IA selon l'offre)
TECHNOS_ROOT = [
    "react",
    "next",
    "vue",
    "typescript",
    "nodejs",
    "express",
    "nestjs",
    "tailwindcss",
    "mongodb",
    "mysql",
    "postgresql",
    "wordpress",
    "tanstack query",
    "axios",
    "docker",
    "github actions",
    "git",
]

# Extensions dérivées de la stack ou contexte projet
TECHNOS_EXTENDED = [
    "JavaScript",
    "React Hooks",
    "HTML",
    "CSS",
    "REST API",
    "JWT",
    "PHP",
    "CI/CD",
    "SEO",
    "Responsive design",
    "OWASP",
    "Sécurisation API",
]

SKILL_CATEGORIES = [
    "Front-end",
    "Back-end",
    "Data & CMS",
    "DevOps",
    "Cybersécurité",
]

DEFAULT_COMPETENCES = [
    {
        "label": "Front-end",
        "items": [
            "React & Hooks",
            "Next.js",
            "Vue.js",
            "TypeScript",
            "TanStack Query",
            "Tailwind CSS",
        ],
    },
    {
        "label": "Back-end",
        "items": [
            "Node.js",
            "Express",
            "NestJS",
            "JWT / auth",
            "API REST",
            "PHP",
        ],
    },
    {
        "label": "Data & CMS",
        "items": [
            "MongoDB",
            "MySQL / PostgreSQL",
            "WordPress",
        ],
    },
    {
        "label": "DevOps",
        "items": [
            "Docker",
            "GitHub Actions",
            "Git",
            "CI/CD",
        ],
    },
    {
        "label": "Cybersécurité",
        "items": [
            "OWASP",
            "Sécurisation API REST",
            "Auth & sessions",
            "Bonnes pratiques web",
        ],
    },
]

DEFAULT_PROFILE = {
    "version": 3,
    "key": "fullstack",
    "header": {
        "name": "Lucas Schrever",
        "title_default": "Développeur fullstack",
        "email": "lucas.schrever@outlook.com",
        "contact": {
            "location": "Paris, France",
            "phone": "+33 7 75 28 61 34",
            "links": [
                {"label": "LinkedIn", "url": "https://linkedin.com/in/lucas-schrever"},
                {"label": "Portfolio", "url": "https://lucas-schrever.vercel.app"},
                {"label": "GitHub", "url": "https://github.com/luca-schr/"},
            ],
        },
        "photo": "assets/DSC02211_squaree.jpg",
    },
    "technos_root": TECHNOS_ROOT,
    "technos_extended": TECHNOS_EXTENDED,
    "profil": {
        "text": (
            "Je pilote et accompagne des projets de site web, applications et logiciels "
            "du cadrage jusqu'au déploiement : technologies de développement fullstack, "
            "UX/UI design, SEO et accessibilité web."
        ),
        "services": [
            "Applications web & SaaS : React, Next.js, état serveur (TanStack Query), intégration API",
            "Back-end Node.js : Express / NestJS, routes, middleware, authentification, modèles de données",
            "Sites & écosystèmes WordPress : thèmes, intégrations front, maintenance multi-sites",
            "Industrialisation : Docker, pipelines GitHub Actions, déploiements reproductibles",
        ],
    },
    "experiences": [
        {
            "id": "jane",
            "sort_key": 1,
            "title": "Développeur fullstack React/Next.js",
            "company": "Jane",
            "dates": "Déc. 2025 - Mai 2026",
            "bullets": [
                (
                    "Site vitrine [jane-energie.fr](https://jane-energie.fr) from scratch : Next.js, TypeScript, "
                    "WordPress headless, GraphQL et intégration API."
                ),
                (
                    "Application [jane-app.fr](https://jane-app.fr) : React, Fetch, MUI, routing ; "
                    "back-end NestJS / Node.js, auth, Docker et GitHub Actions."
                ),
                (
                    "Modélisation MongoDB, routes API et industrialisation des déploiements."
                ),
            ],
        },
        {
            "id": "shin",
            "sort_key": 2,
            "title": "Développeur frontend Vue.js et WordPress",
            "company": "Shin Agency",
            "dates": "Août 2023 - Sept. 2024",
            "bullets": [
                "Refonte UX/UI de [shin-agency.com](https://shin-agency.com) : Vue.js, Tailwind CSS, JavaScript.",
                "Développement et maintenance de thèmes WordPress : PHP, Timber/Twig, jQuery, intégrations front et API.",
                "Maintenance multi-sites (15+) : WordPress, Docker, Git et optimisations performance.",
            ],
        },
        {
            "id": "adtac",
            "sort_key": 3,
            "title": "Chef de Projet Digital",
            "company": "Aube en Champagne Attractivité",
            "dates": "Mai - Août 2022",
            "bullets": [
                "Pilotage de la refonte UX/UI de l'extranet aube-champagne.com : specs, recette, coordination.",
                "Audits performance web, SEO et architecture applicative.",
            ],
        },
        {
            "id": "kyriba",
            "sort_key": 4,
            "title": "Assistant Consultant Marketing Digital",
            "company": "Kyriba France",
            "dates": "Mai 2020 - Août 2021",
            "bullets": [
                "Production de landing pages WordPress orientées conversion.",
                "Audits SEO et suivi d'engagement sur kyriba.com (FR, ES, IT).",
            ],
        },
    ],
    "formations": [
        {
            "id": "mba-cyber",
            "title": "MBA Expert en Cybersécurité",
            "school": "MBA ESG Paris",
            "dates": "2025 - 2026",
            "sort_key": 1,
            "bullets": [
                (
                    "Politique de sécurité SI, gestion des risques (EBIOS), pentesting, DevSecOps, RGPD ; "
                    "préparation CompTIA Security+ et AWS Certified Security."
                ),
            ],
        },
        {
            "id": "mastere-digital",
            "title": "Mastère Management de la Transformation Digitale",
            "school": "IIM / ESILV",
            "dates": "2018 - 2024",
            "sort_key": 2,
            "bullets": [
                (
                    "Double diplôme IIM / ESILV (RNCP niv. 7) : product management, agile/Scrum, conduite du "
                    "changement, data, IA appliquée, UX et développement fullstack."
                ),
            ],
        },
    ],
    "competences": DEFAULT_COMPETENCES,
    "certifications": (
        "MongoDB Associate Developer (en cours), AWS Certified Security Specialist (en cours), "
        "CompTIA Security+ (en cours)"
    ),
    "langues": [
        "Anglais : professionnel, C1 (TOEFL/TOEIC), veille technique",
        "Espagnol : courant",
    ],
}

CHEF_PROJET_TECHNOS_ROOT = [
    "agile",
    "scrum",
    "figma",
    "trello",
    "linear",
    "semrush",
    "seo",
    "wordpress",
    "prestashop",
    "elementor",
    "divi",
    "html",
    "css",
    "javascript",
    "react",
    "mongodb",
    "postgresql",
    "mysql",
]

CHEF_PROJET_TECHNOS_EXTENDED = [
    "Product management",
    "UX/UI",
    "low-code",
    "no-code",
    "PrestaShop",
    "Elementor",
    "Divi",
    "Figma",
    "Trello",
    "Linear",
    "Semrush",
]

CHEF_PROJET_COMPETENCES = [
    {
        "label": "Produit & méthodes",
        "items": [
            "Product management",
            "Agile / Scrum",
            "Code / low-code / no-code",
            "Trello",
            "Linear",
        ],
    },
    {
        "label": "UX / UI",
        "items": [
            "Figma",
            "UX/UI design",
            "Maquettes & recette",
        ],
    },
    {
        "label": "SEO & acquisition",
        "items": [
            "SEO",
            "Semrush",
            "Landing pages",
        ],
    },
    {
        "label": "CMS & no-code",
        "items": [
            "WordPress",
            "PrestaShop",
            "Elementor",
            "Divi",
        ],
    },
    {
        "label": "Développement",
        "items": [
            "HTML / CSS",
            "JavaScript",
            "React",
            "MongoDB",
            "PostgreSQL / MySQL",
        ],
    },
]

CHEF_PROJET_PROFILE = {
    **DEFAULT_PROFILE,
    "key": "chef-projet",
    "header": {
        **DEFAULT_PROFILE["header"],
        "title_default": "Chef de projet digital",
    },
    "technos_root": CHEF_PROJET_TECHNOS_ROOT,
    "technos_extended": CHEF_PROJET_TECHNOS_EXTENDED,
    "profil": {
        "text": (
            "Je pilote et accompagne des projets digitaux du cadrage jusqu'au déploiement : "
            "produit, sprints, solutions technologiques et bonnes pratiques de mise en œuvre "
            "(design UX/UI et produit, visibilité, cadre cyber)."
        ),
        "services": [
            "Cadrage produit et delivery agile : Scrum, Trello / Linear, priorisation, recette",
            "UX/UI : maquettes Figma, parcours, coordination design / dev",
            "SEO et acquisition : audits, Semrush, landing pages orientées conversion",
            "Sites et e-commerce no-code / low-code : WordPress, PrestaShop, Elementor, Divi",
            "Socle technique : HTML, CSS, JavaScript, React, MongoDB, PostgreSQL, MySQL",
        ],
    },
    "competences": CHEF_PROJET_COMPETENCES,
}

SEED_PROFILES = [
    ("Développeur fullstack", DEFAULT_PROFILE, True),
    ("Chef de projet digital", CHEF_PROJET_PROFILE, False),
]
