/**
 * Adaptation d'un profil statique à une fiche de poste
 * (descriptif + compétences — expériences inchangées).
 */
import { chatJson, loadLlmConfig } from "./ollama.js";
import { extractCompany, extractJobTitle } from "./filename.js";

const PROFIL_TITLES = ["## Profil", "## Summary"];
const SKILLS_TITLES = [
  "## Compétences techniques",
  "## Compétences",
  "## Technical skills",
  "## Skills",
];

/**
 * @param {object} profile row mappé (markdown, title, name…)
 * @param {string} jobText
 * @param {{ english?: boolean }} opts
 */
export async function adaptProfileToJob(profile, jobText, { english = false } = {}) {
  const markdown = String(profile.markdown || "");
  const profilSection = extractSection(markdown, PROFIL_TITLES);
  const skillsSection = extractSection(markdown, SKILLS_TITLES);
  const jobTitleDetected = extractJobTitle(jobText);
  const companyHeuristic = extractCompany(jobText, null);

  const config = loadLlmConfig();
  let adapted;
  let source = "local";
  let fallback = false;
  let reason = null;

  if (config.enabled) {
    try {
      adapted = await adaptWithOllama({
        jobText,
        english,
        profileName: profile.name,
        profileTitle: profile.title,
        jobTitleDetected,
        companyHint: companyHeuristic,
        profil: profilSection?.body || profile.summary || "",
        skillsMarkdown: skillsSection?.full || "",
        category: profile.category?.name || profile.category_name,
      });
      source = "ollama";
      reason = adapted.reason || null;
    } catch (err) {
      adapted = adaptLocally({
        jobText,
        english,
        profil: profilSection?.body || profile.summary || "",
        skillsMarkdown: skillsSection?.full || "",
        profileTitle: profile.title,
        profileName: profile.name,
        jobTitleDetected,
      });
      source = "local";
      fallback = true;
      reason = "Ollama indisponible — adaptation locale";
    }
  } else {
    adapted = adaptLocally({
      jobText,
      english,
      profil: profilSection?.body || profile.summary || "",
      skillsMarkdown: skillsSection?.full || "",
      profileTitle: profile.title,
      profileName: profile.name,
      jobTitleDetected,
    });
    reason = "Adaptation locale (Ollama désactivé)";
  }

  // Entreprise : LLM → heuristique (garanti autant que possible)
  const company =
    extractCompany(jobText, adapted.company) || companyHeuristic || null;

  // Titre : si fiche a un intitulé et LLM a gardé le titre de base → interpréter
  let title = cleanTitle(adapted.title) || profile.title;
  if (
    jobTitleDetected &&
    (!title ||
      normalizeLoose(title) === normalizeLoose(profile.title) ||
      normalizeLoose(title) === normalizeLoose(profile.name))
  ) {
    title =
      synthesizeTitleLocally({
        english,
        profileTitle: profile.title,
        profileName: profile.name,
        jobTitleDetected,
        jobText,
      }) || title;
  }

  let next = markdown;
  if (adapted.profil) {
    next = replaceSectionBody(next, PROFIL_TITLES, adapted.profil);
  }
  if (adapted.skills_markdown) {
    const skills = normalizeSkillsMarkdown(adapted.skills_markdown);
    next = replaceSectionFull(next, SKILLS_TITLES, skills);
  }
  if (title) {
    next = replaceCvRole(next, title);
  }

  return {
    markdown: repairCvMarkdownHeadings(next),
    title: title || profile.title,
    summary: adapted.profil || profile.summary,
    company,
    job_title_detected: jobTitleDetected,
    reason,
    source,
    fallback,
    message: english
      ? `Profile adapted · ${profile.name}`
      : `Profil adapté · ${profile.name}`,
  };
}

async function adaptWithOllama({
  jobText,
  english,
  profileName,
  profileTitle,
  jobTitleDetected = null,
  companyHint = null,
  profil,
  skillsMarkdown,
  category,
}) {
  const lang = english ? "English" : "French";
  const langRule = english
    ? `CRITICAL: title, profil, skills_markdown, reason MUST be English only.`
    : `RÈGLE LANGUE ABSOLUE: title, profil, skills_markdown et reason DOIVENT être en FRANÇAIS.
Interdit: phrases anglaises du type "Experienced…", "Skilled…", "Proven track record…".
Écris le profil à la 1ère personne ou impersonnel professionnel FR (ex. "Chef de projet digital, j'assure le cadrage…").`;

  const system = `Tu adaptes un CV à une fiche de poste. Le résultat DOIT être VISIBLEMENT différent du CV de base.
${langRule}

Réponds en JSON strict :
{
  "title": "<intitulé CV pertinent, court, ${lang}>",
  "company": "<employeur court si présent dans l'offre, sinon null>",
  "profil": "<2 à 3 phrases NOUVELLES en ${lang}, clairement réécrites pour l'offre>",
  "skills_markdown": "<bloc markdown ## Compétences… avec ### et puces>",
  "added_skills": [{"name":"<skill>", "pertinence":"haute|moyenne|basse"}],
  "reason": "<1 phrase en ${lang} listant ce qui a changé>"
}

Règles :
1) TITRE (priorité) :
   - Compare job_title_detected (intitulé dans la fiche) avec profile_name / profile_title.
   - Génère un title pertinent = interprétation crédible entre l'offre et le profil
     (ex. fiche "Product Owner Agile" + profil "Chef de projet digital" → "Product Owner" ou "Chef de projet / Product Owner").
   - Si job_title_detected est null, déduis l'intitulé depuis job_text.
   - Sans stack technique (pas de "React/Node"). Max ~60 caractères. Langue : ${lang}.

2) COMPANY (si visible dans l'offre) :
   - Extrais le nom court (Entreprise:, Chez X, X recrute…).
   - company_hint est un indice heuristique : valide-le ou corrige-le.
   - N'invente jamais. null seulement si aucune entreprise identifiable.

3) PROFIL :
   - RÉÉCRIRE entièrement pour coller à l'offre. Pas d'expérience inventée.

4) COMPÉTENCES :
   - Réordonne + ajoute les skills manquantes DANS les ### existants.
   - PAS de section "Issues de l'offre", PAS de "pertinence haute" dans les puces.
   - Retour à la ligne AVANT chaque ###.

5) added_skills : skills ajoutées avec pertinence pour tri interne (max 8).
6) Expériences : ne pas les modifier.`;

  const user = {
    output_language: lang,
    profile_name: profileName,
    profile_title: profileTitle,
    job_title_detected: jobTitleDetected,
    company_hint: companyHint,
    category,
    current_profil: profil,
    current_skills_markdown: skillsMarkdown,
    job_text: String(jobText).slice(0, 9000),
    must_change: [
      "title_from_job_vs_profile",
      "rewritten_profil",
      "reordered_and_possibly_added_skills",
      "company_if_present",
    ],
  };

  const raw = await chatJson(
    [
      { role: "system", content: system },
      { role: "user", content: JSON.stringify(user) },
    ],
    { temperature: 0.35, timeoutSeconds: 90 },
  );

  const profilBase = String(profil || "").trim();
  const skillsBase = String(skillsMarkdown || "").trim();
  let nextProfil = String(raw?.profil || "").trim();
  let nextSkills = String(raw?.skills_markdown || "").trim();
  let title =
    cleanTitle(raw?.title) ||
    synthesizeTitleLocally({
      english,
      profileTitle,
      profileName,
      jobTitleDetected,
      jobText,
    });
  const added = Array.isArray(raw?.added_skills) ? raw.added_skills : [];

  if (!english && nextProfil && looksEnglish(nextProfil)) {
    nextProfil = rewriteProfilLocally({
      english: false,
      profil: profilBase,
      profileTitle: title,
      jobText,
    });
  }
  if (english && nextProfil && looksFrench(nextProfil)) {
    nextProfil = rewriteProfilLocally({
      english: true,
      profil: profilBase,
      profileTitle: title,
      jobText,
    });
  }

  // Si Ollama a recopié le profil de base → forcer une réécriture locale
  if (nextProfil && profilBase && normalizeLoose(nextProfil) === normalizeLoose(profilBase)) {
    nextProfil = rewriteProfilLocally({
      english,
      profil: profilBase,
      profileTitle: title,
      jobText,
    });
  }

  if (
    !english &&
    nextSkills &&
    (looksEnglish(nextSkills) || /##\s*(Skills|Technical skills)\b/i.test(nextSkills))
  ) {
    nextSkills = skillsBase;
  }

  nextSkills = mergeAddedSkills(nextSkills || skillsBase, added, english);
  nextSkills = stripOfferSkillsSection(nextSkills);
  nextSkills = stripPertinenceLabels(nextSkills);
  nextSkills = normalizeSkillsMarkdown(nextSkills);

  return {
    title,
    company:
      raw?.company && String(raw.company).toLowerCase() !== "null"
        ? String(raw.company).trim()
        : null,
    profil: nextProfil,
    skills_markdown: nextSkills,
    reason: String(raw?.reason || "").trim() || null,
  };
}

function normalizeLoose(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function looksEnglish(text) {
  const t = String(text || "").toLowerCase();
  const en = (t.match(/\b(the|with|and|experienced|skilled|proven|strong|focus|successful|development|manager|track|record|teams)\b/g) || []).length;
  const fr = (t.match(/\b(je|j'ai|avec|dans|pour|une|des|expérience|compétences|équipe|projet|assure|intervient)\b/g) || []).length;
  return en >= 3 && en > fr;
}

function looksFrench(text) {
  const t = String(text || "").toLowerCase();
  const fr = (t.match(/\b(je|j'ai|avec|dans|pour|expérience|compétences|équipe|projet|assure)\b/g) || []).length;
  const en = (t.match(/\b(the|with|experienced|skilled|proven|strong)\b/g) || []).length;
  return fr >= 2 && fr > en;
}

function rewriteProfilLocally({ english, profil, profileTitle, jobText }) {
  const tokens = extractJobTokens(String(jobText || "").toLowerCase()).slice(0, 5);
  const focus = tokens.length
    ? tokens.join(", ")
    : english
      ? "the target role"
      : "le poste visé";
  const role = profileTitle || (english ? "Professional" : "Professionnel");
  if (english) {
    return `${role} with hands-on delivery experience, I align my profile with ${focus}. I emphasize coordination, execution quality and the skills most relevant to this offer while staying grounded in my real track record.`;
  }
  return `${role}, j'adapte mon positionnement à ${focus}. Je mets en avant le cadrage, la livraison et les compétences les plus pertinentes pour cette offre, en m'appuyant sur mon parcours réel.`;
}

/** Intègre les skills de l'offre dans les ### existants (sans section dédiée ni label pertinence). */
function mergeAddedSkills(skillsMarkdown, addedSkills, english) {
  let md = stripOfferSkillsSection(String(skillsMarkdown || "").trim());
  md = stripPertinenceLabels(md);

  const items = [];
  for (const item of addedSkills || []) {
    const name = String(item?.name || item || "").trim();
    if (!name || name.length < 2 || name.length > 60) continue;
    if (md.toLowerCase().includes(name.toLowerCase())) continue;
    items.push({
      name,
      score: pertinenceScore(item?.pertinence),
      line: `- ${name}`,
    });
  }
  if (!items.length) return md;

  items.sort((a, b) => b.score - a.score);

  const lines = md ? md.split(/\r?\n/) : [
    english ? "## Skills" : "## Compétences",
    "",
  ];

  // Index des ### groupes : { startLine, header, endLine }
  const groups = [];
  for (let i = 0; i < lines.length; i++) {
    if (/^###\s+/.test(lines[i].trim())) {
      groups.push({ index: i, header: lines[i].trim() });
    }
  }

  for (const skill of items) {
    const target = pickSkillGroup(groups, skill.name, english);
    if (target) {
      // Insérer après le header (et éventuelle ligne vide), avant le prochain ### ou ## 
      let insertAt = target.index + 1;
      while (insertAt < lines.length && lines[insertAt].trim() === "") insertAt++;
      // Haute pertinence → en tête du groupe ; sinon en fin de groupe
      if (skill.score >= 3) {
        lines.splice(insertAt, 0, skill.line);
        // recalculer indices des groupes suivants
        for (const g of groups) {
          if (g.index >= insertAt) g.index += 1;
        }
      } else {
        let end = insertAt;
        while (
          end < lines.length &&
          !/^#{2,3}\s/.test(lines[end].trim())
        ) {
          end += 1;
        }
        lines.splice(end, 0, skill.line);
        for (const g of groups) {
          if (g.index >= end) g.index += 1;
        }
      }
    } else {
      // Aucun ### : créer un groupe générique cohérent
      const h = guessNewGroupHeader(skill.name, english);
      lines.push("", h, "", skill.line);
      groups.push({ index: lines.length - 3, header: h });
    }
  }

  return lines.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}

function stripOfferSkillsSection(md) {
  return String(md || "")
    .replace(
      /\n*###\s*(Issues de l'offre|From the job posting)\s*\n[\s\S]*?(?=\n##\s|\n###\s|$)/gi,
      "\n",
    )
    .trim();
}

function stripPertinenceLabels(md) {
  return String(md || "")
    .replace(/\s*[—\-–]\s*(pertinence|relevance)\s+(haute|moyenne|basse|high|medium|low)/gi, "")
    .replace(/[ \t]+\n/g, "\n");
}

function pertinenceScore(raw) {
  const t = String(raw || "").toLowerCase();
  if (/high|haut/.test(t)) return 3;
  if (/low|bas/.test(t)) return 1;
  return 2;
}

function pickSkillGroup(groups, skillName, english) {
  if (!groups.length) return null;
  const n = skillName.toLowerCase();
  const rules = [
    {
      re: /scrum|agile|jira|kanban|waterfall|cascade|planning|backlog|stakeholder|pilotage|management|product owner|recette|specs/,
      headers: /pilotage|management|project|agile|scrum/i,
    },
    {
      re: /figma|ux|ui|design|seo|semrush|pardot/,
      headers: /design|ux|ui|seo/i,
    },
    {
      re: /react|vue|angular|html|css|javascript|typescript|next|tailwind|wordpress|php|front/,
      headers: /front|web|design|complémentaire|complementary/i,
    },
    {
      re: /node|nest|\.net|dotnet|c#|api|java|python|express|back/,
      headers: /back|api|server|runtime/i,
    },
    {
      re: /mongo|sql|postgres|data/,
      headers: /data|devops|back/i,
    },
    {
      re: /docker|kubernetes|aws|azure|ci\/cd|devops|github/,
      headers: /devops|data|ops|delivery|ingénierie|engineering/i,
    },
    {
      re: /salesforce|pardot|crm|marketing/,
      headers: /web|complémentaire|complementary|design|seo/i,
    },
  ];
  for (const rule of rules) {
    if (!rule.re.test(n)) continue;
    const hit = groups.find((g) => rule.headers.test(g.header));
    if (hit) return hit;
  }
  // défaut : dernier groupe (souvent "Web complémentaire")
  return groups[groups.length - 1];
}

function guessNewGroupHeader(skillName, english) {
  const n = skillName.toLowerCase();
  if (/react|vue|html|css|front|wordpress|php/.test(n)) {
    return english ? "### Front-end" : "### Front-end";
  }
  if (/node|nest|\.net|api|back/.test(n)) {
    return english ? "### Back-end" : "### Back-end";
  }
  if (/docker|aws|devops|kubernetes/.test(n)) {
    return english ? "### Data & DevOps" : "### Data & DevOps";
  }
  if (/scrum|agile|jira|planning/.test(n)) {
    return english ? "### Project management" : "### Pilotage & management";
  }
  return english ? "### Complementary" : "### Web complémentaire";
}

/** Fallback sans LLM : réordonne + ajoute skills détectées dans l'offre. */
function adaptLocally({
  jobText,
  english,
  profil,
  skillsMarkdown,
  profileTitle,
  profileName,
  jobTitleDetected = null,
}) {
  const job = String(jobText || "").toLowerCase();
  const tokens = extractJobTokens(job);
  let skills = reorderSkillsMarkdown(skillsMarkdown, tokens) || skillsMarkdown;

  const existing = String(skills || "").toLowerCase();
  const missing = tokens.filter((t) => !existing.includes(t)).slice(0, 6);
  const added = missing.map((name, i) => ({
    name: prettifyToken(name),
    pertinence: i < 2 ? "haute" : i < 4 ? "moyenne" : "basse",
  }));
  skills = mergeAddedSkills(skills, added, english);
  skills = normalizeSkillsMarkdown(skills);

  const genericTitle = synthesizeTitleLocally({
    english,
    profileTitle,
    profileName,
    jobTitleDetected,
    jobText,
  });
  const nextProfil = rewriteProfilLocally({
    english,
    profil,
    profileTitle: genericTitle,
    jobText,
  });

  return {
    title: genericTitle,
    company: extractCompany(jobText, null),
    profil: nextProfil,
    skills_markdown: skills,
    reason: english
      ? "Local adaptation (title, profile wording, skills)"
      : "Adaptation locale (titre, descriptif, skills)",
  };
}

/**
 * Titre CV = interprétation entre intitulé fiche et profil.
 */
function synthesizeTitleLocally({
  english,
  profileTitle,
  profileName,
  jobTitleDetected,
  jobText,
}) {
  const jobTitle =
    cleanTitle(jobTitleDetected) ||
    cleanTitle(extractJobTitle(jobText)) ||
    null;
  const inferred = inferGenericTitle(String(jobText || "").toLowerCase(), english);
  const profile = cleanTitle(profileTitle) || cleanTitle(profileName) || profileTitle;

  if (!jobTitle) return inferred || profile;

  const jt = jobTitle.toLowerCase();
  const pt = String(profile || "").toLowerCase();

  // Même famille → privilégier l'intitulé de la fiche (nettoyé)
  if (
    (/(product\s*owner|\bpo\b)/.test(jt) && /projet|product|owner|manager|digital/.test(pt)) ||
    (/(chef de projet|project manager)/.test(jt) && /projet|manager|digital|product/.test(pt)) ||
    (/(developpeur|développeur|developer|fullstack|engineer|ingénieur)/.test(jt) &&
      /(developpeur|développeur|fullstack|engineer|software)/.test(pt)) ||
    (/(cyber|securite|sécurité|security)/.test(jt) && /(cyber|securite|sécurité|security|expert)/.test(pt))
  ) {
    return jobTitle;
  }

  // Croisement léger si familles proches
  if (/product\s*owner/.test(jt) && /chef de projet|project manager/.test(pt)) {
    return english ? "Product Owner" : "Product Owner";
  }
  if (/chef de projet/.test(jt) && /product owner/.test(pt)) {
    return english ? "Digital project manager" : "Chef de projet digital";
  }

  return inferred || jobTitle || profile;
}

function prettifyToken(t) {
  const map = {
    "next.js": "Next.js",
    nextjs: "Next.js",
    "node.js": "Node.js",
    node: "Node.js",
    nestjs: "NestJS",
    ".net": ".NET",
    dotnet: ".NET",
    "c#": "C#",
    csharp: "C#",
    react: "React",
    typescript: "TypeScript",
    javascript: "JavaScript",
    mongodb: "MongoDB",
    docker: "Docker",
    figma: "Figma",
    scrum: "Scrum",
    agile: "Agile",
    seo: "SEO",
    wordpress: "WordPress",
  };
  return map[t] || t.charAt(0).toUpperCase() + t.slice(1);
}

function inferGenericTitle(jobLower, english) {
  if (/product\s*owner|\bpo\b/.test(jobLower)) {
    return "Product Owner";
  }
  if (/software\s*engineer|ingénieur\s+logiciel|ingénieur\s+études/.test(jobLower)) {
    return "Software Engineer";
  }
  if (/chef\s+de\s+projet\s+web|project\s+manager\s+web/.test(jobLower)) {
    return english ? "Web project manager" : "Chef de projet web";
  }
  if (/chef\s+de\s+projet|project\s+manager/.test(jobLower)) {
    return english ? "Digital project manager" : "Chef de projet digital";
  }
  if (/cyber|sécurité|security|owasp|devsecops/.test(jobLower)) {
    return english ? "Application security expert" : "Expert cybersécurité applicative";
  }
  if (/fullstack|full-stack|full\s*stack|développeur|developer|front|back/.test(jobLower)) {
    return english ? "Full-stack developer" : "Développeur Fullstack";
  }
  return null;
}

function extractJobTokens(jobLower) {
  const known = [
    "react",
    "next.js",
    "nextjs",
    "vue",
    "angular",
    "typescript",
    "javascript",
    "node.js",
    "nodejs",
    "node",
    "nestjs",
    "express",
    ".net",
    "dotnet",
    "c#",
    "csharp",
    "python",
    "java",
    "php",
    "wordpress",
    "mongodb",
    "postgresql",
    "sql",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "scrum",
    "agile",
    "figma",
    "seo",
    "ux",
    "ui",
    "owasp",
    "devops",
    "ci/cd",
    "graphql",
    "rest",
    "api",
    "tailwind",
    "pardot",
    "salesforce",
    "jira",
    "kanban",
  ];
  const hits = known.filter((k) => tokenInJob(jobLower, k));
  return [...new Set(hits)].slice(0, 12);
}

function tokenInJob(jobLower, token) {
  const raw = String(token || "").toLowerCase();
  if (!raw) return false;
  if (raw.length <= 3 || raw === ".net" || raw === "node" || raw === "java" || raw === "net") {
    const escaped = raw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(?:^|[^a-z0-9])${escaped}(?:[^a-z0-9]|$)`, "i").test(jobLower);
  }
  return jobLower.includes(raw) || jobLower.includes(raw.replace(/\./g, ""));
}

function reorderSkillsMarkdown(skillsMarkdown, tokens) {
  const normalized = normalizeSkillsMarkdown(skillsMarkdown);
  if (!normalized || !tokens.length) return normalized;
  const lines = String(normalized).split(/\r?\n/);
  const blocks = [];
  let current = null;

  for (const line of lines) {
    if (/^#{2,3}\s/.test(line)) {
      if (current) blocks.push(current);
      current = { header: line, items: [] };
    } else if (current && /^\s*-\s+/.test(line)) {
      current.items.push(line);
    } else if (current) {
      current.items.push(line);
    } else {
      blocks.push({ header: line, items: [] });
    }
  }
  if (current) blocks.push(current);

  const scoreLine = (line) => {
    const low = line.toLowerCase();
    return tokens.reduce((s, t) => (low.includes(t) ? s + 1 : s), 0);
  };

  const out = [];
  for (const b of blocks) {
    if (b.header) out.push(b.header);
    const items = b.items.filter((l) => /^\s*-\s+/.test(l));
    const other = b.items.filter((l) => !/^\s*-\s+/.test(l));
    items.sort((a, b) => scoreLine(b) - scoreLine(a));
    out.push(...items, ...other);
  }
  return normalizeSkillsMarkdown(out.join("\n"));
}

/**
 * Corrige les ### collés aux puces (bug fréquent Ollama / Pandoc).
 * Ex. "- Planning… ### Design" → deux lignes distinctes.
 */
export function normalizeSkillsMarkdown(raw) {
  let s = String(raw || "").replace(/\r\n/g, "\n").trim();
  if (!s) return s;

  // "texte ### Titre" ou "texte## Titre" → saut de ligne avant le titre
  s = s.replace(/([^\n#])\s*(#{2,3})\s+/g, "$1\n\n$2 ");
  // "- item### Titre" sans espace
  s = s.replace(/(-\s[^\n]*?)\s*(#{2,3})\s+/g, "$1\n\n$2 ");
  // Titre collé à la puce suivante : "### Design- Figma"
  s = s.replace(/(#{2,3}\s+[^\n]+?)\s*(-\s+)/g, "$1\n$2");
  // Nettoyage lignes vides excessives
  s = s.replace(/\n{3,}/g, "\n\n");

  const lines = s.split("\n").map((line) => {
    const t = line.trimEnd();
    if (/^#{2,3}\s+\S/.test(t.trim())) return t.trim();
    if (/^-\s+/.test(t.trim())) return `- ${t.trim().replace(/^-\s+/, "")}`;
    return t;
  });

  return lines.join("\n").trim();
}

function extractSection(markdown, titles) {
  const md = String(markdown || "");
  for (const title of titles) {
    const re = new RegExp(
      `(^|\\n)(${escapeRe(title)})\\s*\\n([\\s\\S]*?)(?=\\n##\\s|\\n</div>|$)`,
      "i",
    );
    const m = md.match(re);
    if (m) {
      return {
        title: m[2],
        body: m[3].trim(),
        full: `${m[2]}\n\n${m[3].trim()}`,
        index: m.index + (m[1] ? m[1].length : 0),
      };
    }
  }
  return null;
}

function replaceSectionBody(markdown, titles, newBody) {
  const md = String(markdown || "");
  for (const title of titles) {
    const re = new RegExp(
      `((?:^|\\n)(${escapeRe(title)})\\s*\\n)([\\s\\S]*?)(?=\\n##\\s|\\n</div>|$)`,
      "i",
    );
    if (re.test(md)) {
      return md.replace(re, `$1\n${String(newBody).trim()}\n`);
    }
  }
  return md;
}

function replaceSectionFull(markdown, titles, newFull) {
  const md = String(markdown || "");
  for (const title of titles) {
    const re = new RegExp(
      `(^|\\n)(${escapeRe(title)})\\s*\\n[\\s\\S]*?(?=\\n##\\s|\\n</div>|$)`,
      "i",
    );
    if (re.test(md)) {
      const block = String(newFull).trim();
      return md.replace(re, `$1${block}\n`);
    }
  }
  // insert before certifications / languages / closing div
  const insertBefore = md.search(/\n## (Certifications|Langues|Languages)\b/i);
  if (insertBefore >= 0) {
    return `${md.slice(0, insertBefore)}\n\n${String(newFull).trim()}\n${md.slice(insertBefore)}`;
  }
  return `${md.trimEnd()}\n\n${String(newFull).trim()}\n`;
}

function replaceCvRole(markdown, title) {
  return String(markdown || "").replace(
    /(<p class="cv-role">)([\s\S]*?)(<\/p>)/i,
    `$1${escapeHtml(title)}$3`,
  );
}

function cleanTitle(raw) {
  let t = String(raw || "")
    .replace(/[#*_`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  // Retire les stacks du type "… React/Node" ou "… (.NET / React)"
  t = t
    .replace(/\s*[\-–—|:]\s*.+$/, (m, offset, s) => {
      // ne coupe que si la queue semble une liste de technos
      return /react|node|\.net|vue|angular|typescript|java/i.test(m) ? "" : m;
    })
    .replace(/\s*\([^)]*(react|node|\.net|vue)[^)]*\)\s*$/i, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!t || t.length > 60) return null;
  return t;
}

function escapeRe(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Répare les ### collés aux puces dans tout le markdown CV. */
export function repairCvMarkdownHeadings(markdown) {
  let md = String(markdown || "");
  md = md.replace(/([^\n#])\s*(#{2,3})\s+/g, "$1\n\n$2 ");
  md = md.replace(/(#{2,3}\s+[^\n]+?)\s*(-\s+)/g, "$1\n$2");
  md = md.replace(/\n{3,}/g, "\n\n");
  return md;
}
