/**
 * Seed data — contenu métier en français.
 * Les `name` de catégories (SQL) restent en anglais.
 */
const ADTAC = "Agence Départementale Touristique de l'Aube en Champagne";
const ADTAC_EN = "Aube Champagne Departmental Tourism Agency";

const CERTS_FR =
  "MongoDB Associate Developer (en cours), AWS Certified Security Specialist (en cours), CompTIA Security+ (en cours)";
const CERTS_EN =
  "MongoDB Associate Developer (in progress), AWS Certified Security Specialist (in progress), CompTIA Security+ (in progress)";
const CERTS_SEC_FR =
  "AWS Certified Security Specialist (en cours), CompTIA Security+ (en cours)";
const CERTS_SEC_EN =
  "AWS Certified Security Specialist (in progress), CompTIA Security+ (in progress)";

export const CATEGORIES = [
  { name: "developer", label_fr: "Développeur" },
  { name: "expert", label_fr: "Expert" },
  { name: "manager", label_fr: "Manager" },
  { name: "consultant", label_fr: "Consultant" },
];

export const PROFILES = [
  {
    name: "Développeur Fullstack",
    category: "developer",
    is_default: true,
    title: "Développeur Fullstack",
    title_en: "Full-stack developer",
    summary:
      "Développeur Fullstack, je conçois des API et des interfaces web (React, Node.js / .NET) pour livrer des produits en agences et startups, de l'intégration à la mise en production.",
    summary_en:
      "Full-stack developer designing APIs and web UIs (React, Node.js / .NET) to ship products in agencies and startups, from integration to production.",
    keywords:
      "fullstack,full-stack,développeur,React,Next.js,TypeScript,JavaScript,Node.js,NestJS,Express,.NET,dotnet,ASP.NET,C#,Vue.js,WordPress,API REST,MongoDB,SQL Server,PostgreSQL,Docker,CI/CD,front-end,back-end,Tailwind",
    markdown: defaultFullstackMarkdown("fr"),
    markdown_en: defaultFullstackMarkdown("en"),
  },
  {
    name: "Software Engineer",
    category: "developer",
    is_default: false,
    title: "Software Engineer",
    title_en: "Software Engineer",
    summary:
      "Software Engineer : conception et livraison de services fiables (API, data, CI/CD), avec un focus qualité, architecture et industrialisation — au-delà du seul delivery web front/back.",
    summary_en:
      "Software Engineer designing and shipping reliable services (APIs, data, CI/CD), with a focus on quality, architecture and industrialization — beyond front/back web delivery alone.",
    keywords:
      "software engineer,ingénieur logiciel,ingénieur,SWE,backend,API,microservices,architecture,qualité,tests,CI/CD,Docker,cloud,observabilité,TypeScript,Node.js,NestJS,React,.NET,C#,system design,fiabilité,scalabilité",
    markdown: defaultSoftwareEngineerMarkdown("fr"),
    markdown_en: defaultSoftwareEngineerMarkdown("en"),
  },
  {
    name: "Chef de projet digital",
    category: "manager",
    is_default: false,
    title: "Chef de projet digital",
    title_en: "Digital project manager",
    summary:
      "Chef de projet digital, j'assure le cadrage, le pilotage Scrum ou en cascade, et la coordination des parties prenantes, avec une culture UX/UI et web (HTML, CSS, JavaScript, PHP).",
    summary_en:
      "Digital project manager handling scoping, Scrum or waterfall delivery and stakeholder coordination, with UX/UI and web literacy (HTML, CSS, JavaScript, PHP).",
    keywords:
      "chef de projet,project manager,product owner,digital,SEO,UX,UI,Figma,Design System,agile,scrum,sprint,rituels,kanban,cadrage,coordination,recette,stakeholders,HTML,CSS,JavaScript,PHP,WordPress,waterfall,cascade,management,pilotage,budget,planning,backlog,Pardot,Semrush",
    markdown: defaultPmMarkdown("fr"),
    markdown_en: defaultPmMarkdown("en"),
  },
  {
    name: "Expert cybersécurité applicative",
    category: "expert",
    is_default: false,
    title: "Expert cybersécurité applicative",
    title_en: "Application security expert",
    summary:
      "Expert cybersécurité applicative, j'accompagne les équipes produit pour sécuriser les API et applications web (OWASP, DevSecOps) tout au long du cycle de livraison.",
    summary_en:
      "Application security expert helping product teams harden APIs and web apps (OWASP, DevSecOps) throughout the delivery cycle.",
    keywords:
      "cybersécurité,security,OWASP,DevSecOps,RGPD,pentest,Auth,JWT,secure-by-design,AWS Security,CompTIA",
    markdown: defaultSecurityMarkdown("fr"),
    markdown_en: defaultSecurityMarkdown("en"),
  },
];

function header(role) {
  return `<div class="cv-page">
<header class="cv-header">
<div class="cv-header-main">
<p class="cv-name">Lucas Schrever</p>
<p class="cv-role">${role}</p>
<p class="cv-contact-primary">Paris, France · +33 7 75 28 61 34 · <a href="mailto:lucas.schrever@outlook.com">lucas.schrever@outlook.com</a></p>
<p class="cv-contact-links"><a href="https://linkedin.com/in/lucas-schrever">LinkedIn</a> · <a href="https://lucas-schrever.vercel.app">Portfolio</a> · <a href="https://github.com/luca-schr/">GitHub</a></p>
</div>
<img class="photo" src="assets/lucas-schrever.jpg" alt="" />
</header>
`;
}

function defaultFullstackMarkdown(lang) {
  if (lang === "en") {
    return `${header("Full-stack developer")}
## Summary

Full-stack developer designing APIs and web UIs (React, Node.js / .NET) to ship products in agencies and startups, from integration to production.

## Experience

### Full-stack developer React/Next.js — Jane *Dec. 2025 – Aug. 2026*

- Designed and shipped [jane-energie.fr](https://jane-energie.fr) from scratch, combining Next.js, TypeScript and a headless WordPress CMS to deliver a fast, maintainable marketing site.
- Built [jane-app.fr](https://jane-app.fr) with a React front end and a NestJS / Node API, covering authentication, data flows and CI/CD to industrialize releases.

### Front-end developer Vue.js & WordPress — Shin Agency *Aug. 2023 – Sep. 2024*

- Led the UX/UI redesign of [shin-agency.com](https://shin-agency.com) with Vue.js and Tailwind CSS, aligning the interface with the agency brand and conversion goals.
- Developed custom WordPress themes and kept more than fifteen multi-site instances healthy through ongoing maintenance and front-end integrations.

### Digital project manager — ${ADTAC_EN} *May – Aug. 2022*

- Steered the UX/UI redesign of the aube-champagne.com extranet: writing specs, running UAT and coordinating stakeholders through delivery.
- Conducted web performance, SEO and application-architecture audits to guide prioritization and technical choices.

### Digital marketing assistant — Kyriba France *May 2020 – Aug. 2021*

- Produced conversion-oriented landing pages for Kyriba ebooks, webinars and success stories using Salesforce Pardot.
- Ran SEO audits with Semrush and optimized content across the French, Spanish and Italian sites to improve engagement.

## Education

### MBA Cybersecurity Expert — MBA ESG Paris *2025 – 2026*

- SI security policy, EBIOS risk management, DevSecOps and GDPR, with CompTIA Security+ and AWS Security preparation.

### Master's Digital Transformation Management — IIM / ESILV *2018 – 2024*

- Double degree covering product management, agile ways of working, data, applied AI, UX and full-stack development.

## Technical skills

### Front-end

- React / Next.js — TypeScript, Hooks, Router, Tailwind
- Vue.js
- HTML / CSS / JavaScript

### Back-end

- Node.js — Express, NestJS
- .NET — ASP.NET Core, C#, Entity Framework
- API REST — design, OpenAPI

### Data & DevOps

- MongoDB, SQL Server / PostgreSQL
- Docker, GitHub Actions

## Certifications

${CERTS_EN}

## Languages

- English: professional, C1
- Spanish: fluent
</div>
`;
  }
  return `${header("Développeur Fullstack")}
## Profil

Développeur Fullstack, je conçois des API et des interfaces web (React, Node.js / .NET) pour livrer des produits en agences et startups, de l'intégration à la mise en production.

## Expériences Professionnelles

### Développeur fullstack React/Next.js — Jane *Déc. 2025 – Août 2026*

- Conception et mise en ligne de [jane-energie.fr](https://jane-energie.fr) from scratch, en combinant Next.js, TypeScript et un WordPress headless pour un site vitrine rapide et maintenable.
- Développement de [jane-app.fr](https://jane-app.fr) avec un front React et une API NestJS / Node.js, en couvrant l'authentification, les flux de données et la CI/CD pour industrialiser les mises en production.

### Développeur frontend Vue.js et WordPress — Shin Agency *Août 2023 – Sept. 2024*

- Refonte UX/UI de [shin-agency.com](https://shin-agency.com) avec Vue.js et Tailwind CSS, afin d'aligner l'interface sur l'identité de l'agence et les objectifs de conversion.
- Création de thèmes WordPress sur mesure et maintenance de plus de quinze multi-sites, avec intégrations front et suivi des performances.

### Chef de Projet Digital — ${ADTAC} *Mai – Août 2022*

- Pilotage de la refonte UX/UI de l'extranet aube-champagne.com : rédaction des specs, organisation de la recette et coordination des parties prenantes jusqu'à la livraison.
- Réalisation d'audits de performance web, de SEO et d'architecture applicative pour éclairer les priorités et les choix techniques.

### Assistant Consultant Marketing Digital — Kyriba France *Mai 2020 – Août 2021*

- Production de landing pages orientées conversion pour les ebooks, webinaires et success stories Kyriba, réalisées avec Salesforce Pardot.
- Conduite d'audits SEO avec Semrush et optimisation du contenu des sites français, espagnol et italien pour améliorer l'engagement.

## Formations

### MBA Expert en Cybersécurité — MBA ESG Paris *2025 – 2026*

- Politique de sécurité SI, gestion des risques EBIOS, DevSecOps et RGPD, avec préparation CompTIA Security+ et AWS Security.

### Mastère Management de la Transformation Digitale — IIM / ESILV *2018 – 2024*

- Double diplôme couvrant le product management, l'agile, la data, l'IA appliquée, l'UX et le développement fullstack.

## Compétences techniques

### Front-end

- React / Next.js — TypeScript, Hooks, Router, Tailwind
- Vue.js
- HTML / CSS / JavaScript

### Back-end

- Node.js — Express, NestJS
- .NET — ASP.NET Core, C#, Entity Framework
- API REST — design, OpenAPI

### Data & DevOps

- MongoDB, SQL Server / PostgreSQL
- Docker, GitHub Actions

## Certifications

${CERTS_FR}

## Langues

- Anglais : professionnel, C1
- Espagnol : courant
</div>
`;
}

function defaultSoftwareEngineerMarkdown(lang) {
  if (lang === "en") {
    return `${header("Software Engineer")}
## Summary

Software Engineer designing and shipping reliable services (APIs, data, CI/CD), with a focus on quality, architecture and industrialization — beyond front/back web delivery alone.

## Experience

### Software Engineer — Jane *Dec. 2025 – Aug. 2026*

- Designed and delivered [jane-app.fr](https://jane-app.fr) as a serviceable product: React client, NestJS API, MongoDB model, auth flows, Docker packaging and GitHub Actions for repeatable releases.
- Built [jane-energie.fr](https://jane-energie.fr) with Next.js and TypeScript, treating performance, content model and maintainability as engineering constraints, not only UI polish.

### Software Engineer (front & platform) — Shin Agency *Aug. 2023 – Sep. 2024*

- Refactored and modernized [shin-agency.com](https://shin-agency.com) with Vue.js and Tailwind, improving structure, reuse and long-term maintainability of the front codebase.
- Owned WordPress theme delivery and multi-site operations (15+): integrations, dependency hygiene and stable production behavior across client environments.

### Digital project manager — ${ADTAC_EN} *May – Aug. 2022*

- Framed the aube-champagne.com extranet redesign with specs, UAT and stakeholder alignment, while auditing performance, SEO and application architecture.
- Turned audit findings into actionable technical priorities for delivery teams.

### Digital marketing assistant — Kyriba France *May 2020 – Aug. 2021*

- Built Salesforce Pardot landing pages for ebooks, webinars and success stories with a clear conversion path and measurable engagement.
- Ran Semrush SEO audits and optimized content across FR, ES and IT properties.

## Education

### MBA Cybersecurity Expert — MBA ESG Paris *2025 – 2026*

- SI security policy, EBIOS, DevSecOps and GDPR; CompTIA Security+ / AWS Security preparation.

### Master's Digital Transformation Management — IIM / ESILV *2018 – 2024*

- Double degree: product, agile, data, applied AI, UX and full-stack engineering foundations.

## Technical skills

### Engineering & delivery

- API design (REST), auth & data modeling
- CI/CD — GitHub Actions, Docker
- Quality mindset — maintainability, secure-by-design basics

### Languages & runtimes

- TypeScript / JavaScript — React, Next.js, NestJS / Node.js
- C# / .NET — ASP.NET Core, Entity Framework (exposure)

### Data

- MongoDB, SQL Server / PostgreSQL

## Certifications

${CERTS_EN}

## Languages

- English: professional, C1
- Spanish: fluent
</div>
`;
  }
  return `${header("Software Engineer")}
## Profil

Software Engineer : conception et livraison de services fiables (API, data, CI/CD), avec un focus qualité, architecture et industrialisation — au-delà du seul delivery web front/back.

## Expériences Professionnelles

### Software Engineer — Jane *Déc. 2025 – Août 2026*

- Conception et livraison de [jane-app.fr](https://jane-app.fr) comme produit industrialisable : client React, API NestJS, modèle MongoDB, auth, packaging Docker et pipelines GitHub Actions pour des releases reproductibles.
- Construction de [jane-energie.fr](https://jane-energie.fr) avec Next.js et TypeScript, en traitant performance, modèle de contenu et maintenabilité comme des contraintes d'ingénierie, pas seulement du polish UI.

### Software Engineer (front & plateforme) — Shin Agency *Août 2023 – Sept. 2024*

- Modernisation de [shin-agency.com](https://shin-agency.com) avec Vue.js et Tailwind, en améliorant structure, réutilisation et maintenabilité du code front sur la durée.
- Responsabilité des thèmes WordPress et de l'exploitation multi-sites (15+) : intégrations, hygiène des dépendances et stabilité en production chez les clients.

### Chef de Projet Digital — ${ADTAC} *Mai – Août 2022*

- Cadrage de la refonte de l'extranet aube-champagne.com (specs, recette, parties prenantes), avec audits de performance, SEO et architecture applicative.
- Traduction des constats d'audit en priorités techniques actionnables pour les équipes de livraison.

### Assistant Consultant Marketing Digital — Kyriba France *Mai 2020 – Août 2021*

- Landing pages Salesforce Pardot pour ebooks, webinaires et success stories, avec parcours de conversion clair et suivi d'engagement.
- Audits SEO Semrush et optimisation de contenu sur les sites français, espagnol et italien.

## Formations

### MBA Expert en Cybersécurité — MBA ESG Paris *2025 – 2026*

- Politique de sécurité SI, EBIOS, DevSecOps et RGPD ; préparation CompTIA Security+ et AWS Security.

### Mastère Management de la Transformation Digitale — IIM / ESILV *2018 – 2024*

- Double diplôme : product, agile, data, IA appliquée, UX et bases d'ingénierie fullstack.

## Compétences techniques

### Ingénierie & delivery

- Conception d'API (REST), auth & modélisation data
- CI/CD — GitHub Actions, Docker
- Qualité — maintenabilité, bases secure-by-design

### Langages & runtimes

- TypeScript / JavaScript — React, Next.js, NestJS / Node.js
- C# / .NET — ASP.NET Core, Entity Framework (exposition)

### Data

- MongoDB, SQL Server / PostgreSQL

## Certifications

${CERTS_FR}

## Langues

- Anglais : professionnel, C1
- Espagnol : courant
</div>
`;
}

function defaultPmMarkdown(lang) {
  if (lang === "en") {
    return `${header("Digital project manager")}
## Summary

Digital project manager handling scoping, Scrum or waterfall delivery and stakeholder coordination, with UX/UI and web literacy (HTML, CSS, JavaScript, PHP).

## Experience

### Full-stack developer React/Next.js — Jane *Dec. 2025 – Aug. 2026*

- Coordinated delivery of [jane-energie.fr](https://jane-energie.fr) and [jane-app.fr](https://jane-app.fr) in sprint cycles: backlog grooming, planning, daily rituals, reviews and retros.
- Aligned priorities with product and stakeholders, and smoothed handoffs between design and engineering throughout the releases.

### Front-end developer Vue.js & WordPress — Shin Agency *Aug. 2023 – Sep. 2024*

- Contributed to [shin-agency.com](https://shin-agency.com) and multi-site WordPress work in a waterfall cycle, with clear specs, build phases and client validation gates.
- Supported the project manager on planning and progress tracking while delivering UX/UI and front-end integrations on time.

### Digital project manager — ${ADTAC_EN} *May – Aug. 2022*

- Owned the UX/UI redesign of the aube-champagne.com extranet: scoping, specs, UAT and stakeholder coordination through go-live.
- Led web performance, SEO and application-architecture audits to feed decisions and sequencing.

### Digital marketing assistant — Kyriba France *May 2020 – Aug. 2021*

- Designed and produced Salesforce Pardot landing pages for Kyriba ebooks, webinars and success stories, oriented toward conversion.
- Ran Semrush SEO audits and optimized content on the French, Spanish and Italian sites to strengthen engagement.

## Skills

### Project management

- Scrum — sprints, rituals (daily, review, retro), backlog
- Waterfall / cascade planning & milestones
- Stakeholder coordination, specs & UAT
- Planning, prioritization, risk follow-up

### Design

- Figma — wireframes & prototypes
- UX / UI, Design System
- SEO & web performance basics

### Web complementary

- HTML / CSS / JavaScript
- PHP / WordPress (themes & content)

## Certifications

${CERTS_EN}

## Languages

- English: professional, C1
- Spanish: fluent
</div>
`;
  }
  return `${header("Chef de projet digital")}
## Profil

Chef de projet digital, j'assure le cadrage, le pilotage Scrum ou en cascade, et la coordination des parties prenantes, avec une culture UX/UI et web (HTML, CSS, JavaScript, PHP).

## Expériences Professionnelles

### Développeur fullstack React/Next.js — Jane *Déc. 2025 – Août 2026*

- Coordination de la livraison de [jane-energie.fr](https://jane-energie.fr) et [jane-app.fr](https://jane-app.fr) en sprints : grooming du backlog, planning, rituels (daily, review, rétro).
- Alignement des priorités avec le produit et les parties prenantes, et fluidification des passages design ↔ tech tout au long des releases.

### Développeur frontend Vue.js et WordPress — Shin Agency *Août 2023 – Sept. 2024*

- Contribution à [shin-agency.com](https://shin-agency.com) et aux multi-sites WordPress en cycle en cascade, avec cadrage, phases de build et jalons de validation client.
- Appui au chef de projet sur le planning et le suivi d'avancement, tout en livrant UX/UI et intégrations front dans les délais.

### Chef de Projet Digital — ${ADTAC} *Mai – Août 2022*

- Responsabilité de la refonte UX/UI de l'extranet aube-champagne.com : cadrage, specs, recette et coordination des parties prenantes jusqu'à la mise en ligne.
- Conduite d'audits de performance web, de SEO et d'architecture applicative pour nourrir les décisions et le séquencement.

### Assistant Consultant Marketing Digital — Kyriba France *Mai 2020 – Août 2021*

- Conception et production de landing pages Salesforce Pardot pour les ebooks, webinaires et success stories Kyriba, orientées conversion.
- Réalisation d'audits SEO avec Semrush et optimisation du contenu des sites français, espagnol et italien pour renforcer l'engagement.

## Compétences

### Pilotage & management

- Scrum — sprints, rituels (daily, review, rétro), backlog
- Cycle en cascade / waterfall — jalons & livrables
- Coordination parties prenantes, specs & recette
- Planning, priorisation, suivi des risques

### Design

- Figma — wireframes & prototypes
- UX / UI, Design System
- SEO & bases de performance web

### Web complémentaire

- HTML / CSS / JavaScript
- PHP / WordPress (thèmes & contenus)

## Certifications

${CERTS_FR}

## Langues

- Anglais : professionnel, C1
- Espagnol : courant
</div>
`;
}

function defaultSecurityMarkdown(lang) {
  if (lang === "en") {
    return `${header("Application security expert")}
## Summary

Application security expert helping product teams harden APIs and web apps (OWASP, DevSecOps) throughout the delivery cycle.

## Experience

### Full-stack developer React/Next.js — Jane *Dec. 2025 – Aug. 2026*

- Strengthened authentication and API access on [jane-app.fr](https://jane-app.fr) (NestJS / Node), covering session handling, secrets management and safer deployment practices.
- Embedded secure-by-design habits on [jane-energie.fr](https://jane-energie.fr) (Next.js), including CI checks to catch regressions early.

### Front-end Vue.js & WordPress — Shin Agency *Aug. 2023 – Sep. 2024*

- Hardened WordPress multi-site estates (updates, roles, exposed surfaces) across more than fifteen properties.
- Delivered front-end integrations with close attention to XSS risks and dependency hygiene.

### Digital project manager — ${ADTAC_EN} *May – Aug. 2022*

- Audited application architecture and web performance on the aube-champagne.com extranet to surface structural and security-related risks.
- Framed specs and UAT within a delivery approach mindful of security constraints.

## Education

### MBA Cybersecurity Expert — MBA ESG Paris *2025 – 2026*

- SI security policy, EBIOS, pentesting, DevSecOps and GDPR, with CompTIA Security+ and AWS Security preparation.

### Master's Digital Transformation Management — IIM / ESILV *2018 – 2024*

- Double degree covering product management, agile, data, applied AI, UX and full-stack development.

## Skills

### Security

- OWASP, API hardening, Auth & sessions
- DevSecOps, GDPR / RGPD
- Secure CI/CD, dependency hygiene

### Complementary

- Node.js / NestJS, React, WordPress
- Docker, GitHub Actions

## Certifications

${CERTS_SEC_EN}

## Languages

- English: professional, C1
- Spanish: fluent
</div>
`;
  }
  return `${header("Expert cybersécurité applicative")}
## Profil

Expert cybersécurité applicative, j'accompagne les équipes produit pour sécuriser les API et applications web (OWASP, DevSecOps) tout au long du cycle de livraison.

## Expériences Professionnelles

### Développeur fullstack React/Next.js — Jane *Déc. 2025 – Août 2026*

- Renforcement de l'authentification et des accès API sur [jane-app.fr](https://jane-app.fr) (NestJS / Node) : gestion des sessions, des secrets et pratiques de déploiement plus sûres.
- Intégration d'habitudes secure-by-design sur [jane-energie.fr](https://jane-energie.fr) (Next.js), avec des contrôles CI pour détecter tôt les régressions.

### Développeur frontend Vue.js et WordPress — Shin Agency *Août 2023 – Sept. 2024*

- Durcissement des multi-sites WordPress (mises à jour, rôles, surfaces exposées) sur plus de quinze propriétés.
- Livraison d'intégrations front avec une vigilance particulière sur les risques XSS et l'hygiène des dépendances.

### Chef de Projet Digital — ${ADTAC} *Mai – Août 2022*

- Audits d'architecture applicative et de performance web sur l'extranet aube-champagne.com, pour faire remonter les risques structurels et de sécurité.
- Encadrement des specs et de la recette dans une approche de livraison attentive aux contraintes de sécurité.

## Formations

### MBA Expert en Cybersécurité — MBA ESG Paris *2025 – 2026*

- Politique de sécurité SI, EBIOS, pentesting, DevSecOps et RGPD, avec préparation CompTIA Security+ et AWS Security.

### Mastère Management de la Transformation Digitale — IIM / ESILV *2018 – 2024*

- Double diplôme couvrant le product management, l'agile, la data, l'IA appliquée, l'UX et le développement fullstack.

## Compétences

### Cybersécurité

- OWASP, sécurisation API, Auth & sessions
- DevSecOps, RGPD
- CI/CD sécurisé, hygiène des dépendances

### Complémentaire

- Node.js / NestJS, React, WordPress
- Docker, GitHub Actions

## Certifications

${CERTS_SEC_FR}

## Langues

- Anglais : professionnel, C1
- Espagnol : courant
</div>
`;
}
