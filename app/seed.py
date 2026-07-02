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
]

DEFAULT_COMPETENCES = [
    {
        "label": "React & interfaces",
        "items": [
            "React (Hooks, composants, état local)",
            "Next.js (pages, routing, rendu SSR)",
            "TanStack Query (cache, requêtes, mutations)",
            "Consommation API (Axios, REST)",
            "TypeScript / JavaScript",
        ],
    },
    {
        "label": "Vue.js & intégration",
        "items": [
            "Vue.js (Composition API, composants)",
            "Tailwind CSS",
            "HTML / CSS responsive",
        ],
    },
    {
        "label": "Node.js & back-end",
        "items": [
            "Express (routes, middleware, controllers)",
            "NestJS (modules, guards, validation)",
            "Authentification (JWT, sessions)",
            "Modélisation API REST",
            "PHP & thèmes WordPress",
        ],
    },
    {
        "label": "Données & CMS",
        "items": [
            "MongoDB (schémas, requêtes)",
            "MySQL / PostgreSQL",
            "WordPress (thèmes, plugins, headless)",
        ],
    },
    {
        "label": "DevOps & livraison",
        "items": [
            "Docker (conteneurs, déploiement)",
            "GitHub Actions (CI/CD)",
            "Git (workflow, revues)",
        ],
    },
]

DEFAULT_PROFILE = {
    "version": 3,
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
    "technos_root": TECHNOS_ROOT,
    "technos_extended": TECHNOS_EXTENDED,
    "profil": {
        "text": (
            "Développeur fullstack, j'accompagne la conception et la livraison de produits web : "
            "applications React / Next.js, interfaces Vue.js, API Node.js (Express / NestJS) et sites WordPress. "
            "Mon approche couvre le cadrage technique, le développement front et back, la connexion aux services "
            "(REST, bases SQL / NoSQL), la sécurisation des accès et la mise en production (Docker, CI/CD). "
            "Objectif : des livrables maintenables, performants et alignés sur les besoins métier."
        ),
        "services": [
            "Applications web & SaaS — React, Next.js, état serveur (TanStack Query), intégration API",
            "Back-end Node.js — Express / NestJS, routes, middleware, authentification, modèles de données",
            "Sites & écosystèmes WordPress — thèmes, intégrations front, maintenance multi-sites",
            "Industrialisation — Docker, pipelines GitHub Actions, déploiements reproductibles",
        ],
    },
    "experiences": [
        {
            "id": "jane",
            "sort_key": 1,
            "title": "Développeur Fullstack React / Next.js",
            "company": "Jane",
            "dates": "Déc. 2025 – Mai 2026",
            "bullets": [
                (
                    "Livraison from scratch de [jane-energie.fr](https://jane-energie.fr) : Next.js, TypeScript, "
                    "WordPress headless et intégration API."
                ),
                (
                    "Développement produit sur [jane-app.fr](https://jane-app.fr) : React, Hooks, TanStack Query, "
                    "Axios et consommation d'API REST."
                ),
                (
                    "Back-end NestJS / Node.js : routes, modèle MongoDB, auth et déploiements Docker / GitHub Actions."
                ),
            ],
        },
        {
            "id": "shin",
            "sort_key": 2,
            "title": "Développeur Frontend Vue.js et WordPress",
            "company": "Shin Agency",
            "dates": "Août 2023 – Sept. 2024",
            "bullets": [
                "Refonte UX/UI de [shin-agency.com](https://shin-agency.com) : Vue.js, Tailwind CSS, JavaScript.",
                "Développement et maintenance WordPress : PHP, thèmes, intégrations front et API.",
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
            "title": "MBA Expert en Cybersécurité",
            "school": "MBA ESG Paris",
            "dates": "2025 – 2026",
            "sort_key": 1,
            "bullets": [
                "OWASP, sécurisation API REST, audits techniques — architectures web sécurisées.",
            ],
        },
        {
            "title": "Mastère Management de la Transformation Digitale",
            "school": "IIM / ESILV",
            "dates": "2018 – 2024",
            "sort_key": 2,
            "bullets": [
                "Fullstack, Agile/Scrum, UX/UI, mobile et intégration d'outils d'IA.",
            ],
        },
    ],
    "competences": DEFAULT_COMPETENCES,
    "certifications": (
        "MongoDB Associate Developer (en cours), AWS Certified Security Specialist (en cours), "
        "CompTIA Security+ (en cours)"
    ),
    "langues": [
        "Anglais : professionnel, C1 (TOEFL/TOEIC) — veille technique",
        "Espagnol : courant",
    ],
}
