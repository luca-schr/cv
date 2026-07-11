"""Corpus CV par défaut + skills initiales."""

from __future__ import annotations

# Technos de prédilection — orientent profil et sélection des subskills
PREFERRED_TECHS = [
    "React",
    "Vue.js",
    "Next.js",
    "Node.js",
    ".NET",
    "API REST",
    "MongoDB",
    "WordPress",
    "Docker",
    "Tailwind CSS",
]

# Alias détectés dans le titre du poste → skill profil
TITLE_TECH_ALIASES: list[tuple[str, str]] = [
    (r"\breact\b", "React"),
    (r"\bvue\.?js\b|\bvue\b", "Vue.js"),
    (r"\bnext\.?js\b", "Next.js"),
    (r"\bnode\.?js\b|\bnodejs\b", "Node.js"),
    (r"\b\.net\b|\bdotnet\b|\basp\.?net\b", ".NET"),
    (r"\bapi\s*rest\b", "API REST"),
    (r"\bmongodb?\b", "MongoDB"),
    (r"\bwordpress\b", "WordPress"),
    (r"\bdocker\b", "Docker"),
    (r"\btailwind\b", "Tailwind CSS"),
    (r"\btypescript\b|\bts\b", "TypeScript"),
    (r"\bnestjs\b", "NestJS"),
]

PREFERRED_TECH_NORMALIZED = {
    "react",
    "vue-js",
    "next-js",
    "nodejs",
    "net",
    "api-rest",
    "mongodb",
    "wordpress",
    "docker",
    "tailwind-css",
}

DEFAULT_COMPETENCES = [
    {
        "label": "Front-end",
        "items": [
            ("React", 5),
            ("Next.js", 5),
            ("Vue.js", 4),
            ("TypeScript", 5),
            ("Tailwind CSS", 4),
        ],
    },
    {
        "label": "Back-end",
        "items": [
            ("Node.js", 5),
            ("API REST", 5),
            (".NET", 3),
            ("NestJS", 4),
            ("Express", 4),
        ],
    },
    {
        "label": "Data & CMS",
        "items": [
            ("MongoDB", 4),
            ("WordPress", 4),
            ("MySQL / PostgreSQL", 3),
        ],
    },
    {
        "label": "DevOps",
        "items": [
            ("Docker", 4),
            ("GitHub Actions", 4),
            ("Git", 5),
            ("CI/CD", 4),
        ],
    },
    {
        "label": "Cybersécurité",
        "items": [
            ("OWASP", 4),
            ("Sécurisation API REST", 4),
            ("Auth & sessions", 4),
        ],
    },
]

# Subskills rattachées à une skill parente (nom exact de la skill seed)
DEFAULT_SUBSKILLS: dict[str, list[tuple[str, int | None]]] = {
    "React": [
        ("TanStack Query", 4),
        ("React Hooks", 5),
        ("React Router", 4),
        ("MUI", 4),
        ("Zustand", 3),
    ],
    "Vue.js": [
        ("Vue Router", 4),
        ("Pinia", 4),
        ("Composition API", 4),
    ],
    "Next.js": [
        ("App Router", 4),
        ("SSR / SSG", 4),
        ("Server Actions", 3),
    ],
    "Node.js": [
        ("Express middleware", 4),
        ("Routing REST", 5),
        ("JWT / auth", 4),
        ("NestJS modules", 4),
    ],
    ".NET": [
        ("ASP.NET Core", 3),
        ("C#", 3),
        ("Entity Framework", 3),
    ],
    "API REST": [
        ("OpenAPI / Swagger", 4),
        ("Versioning API", 4),
        ("Design d'API", 5),
    ],
    "MongoDB": [
        ("Mongoose", 4),
        ("Modélisation documents", 4),
        ("Aggregation pipelines", 3),
    ],
    "WordPress": [
        ("Thèmes sur mesure", 4),
        ("Timber / Twig", 4),
        ("Headless WordPress", 4),
        ("Plugins", 3),
    ],
    "Docker": [
        ("docker-compose", 4),
        ("Images multi-stage", 3),
        ("Déploiement CI/CD", 4),
    ],
    "Tailwind CSS": [
        ("Utility-first", 4),
        ("Responsive design", 4),
        ("Design system", 3),
    ],
}

DEFAULT_PROFILE_DATA = {
    "version": 4,
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
        "photo": "assets/lucas-schrever.jpg",
    },
    "experiences": [
        {
            "id": "jane",
            "sort_key": 1,
            "title": "Développeur fullstack React/Next.js",
            "company": "Jane",
            "dates": "Déc. 2025 – Mai 2026",
            "bullets": [
                (
                    "Site vitrine [jane-energie.fr](https://jane-energie.fr) from scratch : Next.js, TypeScript, "
                    "WordPress headless, GraphQL et intégration API."
                ),
                (
                    "Application [jane-app.fr](https://jane-app.fr) : React, Fetch, MUI, routing ; "
                    "back-end NestJS / Node.js, auth, Docker et GitHub Actions."
                ),
                "Modélisation MongoDB, routes API et industrialisation des déploiements.",
            ],
        },
        {
            "id": "shin",
            "sort_key": 2,
            "title": "Développeur frontend Vue.js et WordPress",
            "company": "Shin Agency",
            "dates": "Août 2023 – Sept. 2024",
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
            "company": "Agence de Développement Touristique de l'Aube en Champagne",
            "dates": "Mai – Août 2022",
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
            "dates": "Mai 2020 – Août 2021",
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
            "dates": "2025 – 2026",
            "sort_key": 1,
            "bullets": [
                "Politique de sécurité SI, gestion des risques (EBIOS), pentesting, DevSecOps, RGPD ; "
                "préparation CompTIA Security+ et AWS Certified Security.",
            ],
        },
        {
            "id": "mastere-digital",
            "title": "Mastère Management de la Transformation Digitale",
            "school": "IIM / ESILV",
            "dates": "2018 – 2024",
            "sort_key": 2,
            "bullets": [
                "Double diplôme IIM / ESILV (RNCP niv. 7) : product management, agile/Scrum, conduite du "
                "changement, data, IA appliquée, UX et développement fullstack.",
            ],
        },
    ],
    "certifications": (
        "MongoDB Associate Developer (en cours), AWS Certified Security Specialist (en cours), "
        "CompTIA Security+ (en cours)"
    ),
    "langues": [
        "Anglais : professionnel, C1 (TOEFL/TOEIC) — veille technique",
        "Espagnol : courant",
    ],
}
