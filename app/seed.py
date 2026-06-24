"""Profil CV par défaut (seed)."""

DEFAULT_PROFILE = {
    "header": {
        "name": "Lucas Schrever",
        "title_default": "Développeur fullstack C#/JavaScript",
        "email": "lucas.schrever@outlook.com",
        "contact": (
            "Paris, France, +33 7 75 28 61 34, "
            "[lucas.schrever@outlook.com](mailto:lucas.schrever@outlook.com), "
            "[linkedin.com/in/lucas-schrever](https://linkedin.com/in/lucas-schrever), "
            "[lucas-schrever.vercel.app](https://lucas-schrever.vercel.app)"
        ),
        "photo": "assets/lucas-schrever.jpg",
    },
    "title_variants": [
        {
            "title": "Développeur front-end",
            "match_tags": ["frontend", "vue", "react", "javascript", "typescript", "ux", "ui"],
            "match_title": ["front", "frontend", "front-end", "concepteur", "intégrateur", "integrateur"],
        },
        {
            "title": "Développeur fullstack C#/JavaScript",
            "match_tags": ["fullstack", "nestjs", "dotnet", "nextjs", "graphql", "api", "postgresql"],
            "match_title": ["fullstack", "full stack", "full-stack", "ingénieur", "developer"],
        },
        {
            "title": "Webmaster / Intégrateur WordPress",
            "match_tags": ["webmaster", "wordpress", "cms", "integrateur", "seo", "php"],
            "match_title": ["webmaster", "wordpress", "cms"],
        },
        {
            "title": "Chef de projet digital",
            "match_tags": ["chef de projet", "agile", "scrum", "ux"],
            "match_title": ["chef de projet", "project manager", "digital"],
        },
    ],
    "profil": {
        "text": (
            "Développeur fullstack C#/JavaScript, de l'interface (React, Next.js) aux API (.NET, NestJS) "
            "et bases PostgreSQL. Parcours cohérent : produit SaaS, écosystème WordPress à grande échelle, "
            "pilotage de refonte UX/UI et socle marketing/SEO international."
        ),
        "intro": "Développeur fullstack C#/JavaScript, de l'interface (React, Next.js) aux API (.NET, NestJS).",
        "closing": "Parcours produit SaaS → WordPress/SEO → pilotage de projets digitaux.",
        "keywords": [
            {"term": "JavaScript", "tags": ["javascript", "js"]},
            {"term": "TypeScript", "tags": ["typescript", "ts"]},
            {"term": "React", "tags": ["react", "frontend"]},
            {"term": "TanStack Query", "tags": ["tanstack", "react-query"]},
            {"term": "Next.js", "tags": ["nextjs", "next.js"]},
            {"term": "NestJS", "tags": ["nestjs", "nest"]},
            {"term": ".NET", "tags": ["dotnet", ".net"]},
            {"term": "GraphQL", "tags": ["graphql"]},
            {"term": "WordPress", "tags": ["wordpress", "cms", "webmaster"]},
            {"term": "PostgreSQL", "tags": ["postgresql", "postgres"]},
            {"term": "Vue.js", "tags": ["vue", "vuejs"]},
            {"term": "SEO", "tags": ["seo"]},
        ],
    },
    "experiences": [
        {
            "id": "jane",
            "sort_key": 1,
            "title": "Développeur Fullstack React / Next.js et NestJS",
            "company": "Jane",
            "dates": "Déc. 2025 – Mai 2026",
            "title_tags": ["fullstack", "react", "nextjs", "nestjs", "dotnet"],
            "bullets": [
                {
                    "text": (
                        "Livraison from scratch de [jane-energie.fr](https://jane-energie.fr) : Next.js, TypeScript, "
                        "WordPress et API GraphQL."
                    ),
                    "tags": ["nextjs", "typescript", "wordpress", "graphql", "fullstack"],
                },
                {
                    "text": (
                        "Développement produit sur [jane-app.fr](https://jane-app.fr) : React, Material UI, "
                        "TanStack Query et API REST."
                    ),
                    "tags": ["react", "mui", "tanstack", "frontend", "api"],
                },
                {
                    "text": "Évolution d'API .NET et NestJS, modélisation et requêtage PostgreSQL.",
                    "tags": ["nestjs", "dotnet", "postgresql", "api", "backend"],
                },
            ],
        },
        {
            "id": "shin",
            "sort_key": 2,
            "title": "Développeur Frontend Vue.js et WordPress",
            "company": "Shin Agency",
            "dates": "Août 2023 – Sept. 2024",
            "title_tags": ["frontend", "vue", "wordpress", "php", "seo", "webmaster"],
            "bullets": [
                {
                    "text": (
                        "Refonte UX/UI de [shin-agency.com](https://shin-agency.com) : Vue.js, Tailwind CSS, Sass."
                    ),
                    "tags": ["vue", "tailwind", "sass", "ux", "ui", "frontend"],
                },
                {
                    "text": (
                        "Maintenance de 15+ sites (Andros, Best Western, Mauboussin) : PHP, WordPress, Docker, Git."
                    ),
                    "tags": ["php", "wordpress", "docker", "git", "maintenance"],
                },
                {
                    "text": "Optimisation SEO et extensions WordPress sur le site corporate.",
                    "tags": ["wordpress", "seo", "php", "cms"],
                },
            ],
        },
        {
            "id": "adtac",
            "sort_key": 3,
            "title": "Chef de Projet Digital",
            "company": "Agence de Développement Touristique de l'Aube en Champagne",
            "dates": "Mai – Août 2022",
            "title_tags": ["chef de projet", "ux", "seo"],
            "bullets": [
                {
                    "text": (
                        "Pilotage de la refonte UX/UI de l'extranet aube-champagne.com : specs, recette, coordination."
                    ),
                    "tags": ["chef de projet", "ux", "ui", "recette"],
                },
                {
                    "text": "Audits performance web, SEO et architecture applicative.",
                    "tags": ["seo", "performance", "audit"],
                },
            ],
        },
        {
            "id": "kyriba",
            "sort_key": 4,
            "title": "Assistant Consultant Marketing Digital",
            "company": "Kyriba France",
            "dates": "Mai 2020 – Août 2021",
            "title_tags": ["marketing", "wordpress", "seo"],
            "bullets": [
                {
                    "text": "Production de landing pages WordPress et Salesforce Pardot orientées conversion.",
                    "tags": ["wordpress", "marketing", "cms"],
                },
                {
                    "text": "Audits SEO et suivi d'engagement sur kyriba.com (FR, ES, IT).",
                    "tags": ["seo", "marketing", "analytics"],
                },
            ],
        },
    ],
    "formations": [
        {
            "title": "MBA Expert en Cybersécurité",
            "school": "MBA ESG Paris",
            "dates": "2025 – 2026",
            "sort_key": 1,
            "tags": ["cyber", "security", "owasp", "api"],
            "bullets": [
                "OWASP, sécurisation API REST, audits techniques — architectures Fullstack sécurisées.",
            ],
        },
        {
            "title": "Mastère Management de la Transformation Digitale",
            "school": "IIM / ESILV",
            "dates": "2018 – 2024",
            "sort_key": 2,
            "tags": ["fullstack", "digital", "agile", "ux", "ui"],
            "bullets": [
                "Fullstack, Agile/Scrum, UX/UI, mobile et intégration d'outils d'IA.",
            ],
        },
    ],
    "competences": [
        {
            "label": "Front-end",
            "items": [
                {"term": "React", "tags": ["react"]},
                {"term": "Next.js", "tags": ["nextjs"]},
                {"term": "Vue.js", "tags": ["vue"]},
                {"term": "JavaScript", "tags": ["javascript"]},
                {"term": "TypeScript", "tags": ["typescript"]},
                {"term": "TanStack Query", "tags": ["tanstack"]},
                {"term": "Material UI", "tags": ["mui"]},
            ],
        },
        {
            "label": "Back-end",
            "items": [
                {"term": "C# / .NET", "tags": ["dotnet", ".net"]},
                {"term": "NestJS", "tags": ["nestjs"]},
                {"term": "Node.js", "tags": ["nodejs"]},
                {"term": "PHP", "tags": ["php"]},
                {"term": "API REST", "tags": ["api", "rest"]},
                {"term": "GraphQL", "tags": ["graphql"]},
                {"term": "WordPress", "tags": ["wordpress", "cms"]},
            ],
        },
        {
            "label": "Data & DevOps",
            "items": [
                {"term": "PostgreSQL", "tags": ["postgresql"]},
                {"term": "MySQL", "tags": ["mysql"]},
                {"term": "MongoDB", "tags": ["mongodb"]},
                {"term": "Docker", "tags": ["docker"]},
                {"term": "GitHub Actions", "tags": ["github actions", "ci/cd"]},
                {"term": "Git", "tags": ["git"]},
            ],
        },
        {
            "label": "Styles & Design",
            "items": [
                {"term": "Tailwind CSS", "tags": ["tailwind", "css"]},
                {"term": "Sass", "tags": ["sass"]},
                {"term": "responsive design", "tags": ["responsive"]},
                {"term": "Figma", "tags": ["figma", "design"]},
            ],
        },
        {
            "label": "SEO",
            "items": [
                {"term": "audit technique", "tags": ["seo", "audit"]},
                {"term": "optimisation sémantique", "tags": ["seo"]},
                {"term": "performance web", "tags": ["performance"]},
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
