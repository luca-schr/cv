/**
 * Extraction employeur + intitulé de poste depuis une fiche + nommage fichier.
 */

const LABEL_RE =
  /(?:^|\n)\s*(?:entreprise|soci[eé]t[eé]|employeur|company|client|organisme|structure|employer|groupe|cabinet|agence)\s*[:\-–—]\s*([^\n|,;]{2,80})/i;

/** "Entreprise Acme", "Société Acme Digital" en début de ligne */
const LABEL_INLINE_RE =
  /(?:^|\n)\s*(?:entreprise|soci[eé]t[eé]|employeur|company|groupe)\s+([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,40}(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,30}){0,3})\b/;

const ABOUT_KW_RE =
  /(?:rejoignez|rejoindre|au sein (?:de|d['’])|chez|pour le compte (?:de|d['’])|au sein d['’]?une?)\s+/gi;

const COMPANY_NAME_RE =
  /^([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{0,40}(?:\s+(?:et|&|de|du|des|la|le)?\s*[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ0-9][\wÀ-ÿ&.'’-]{1,30}){0,4})/;

/** "Acme Digital recrute", "ACME - CDI", "Offre Acme Digital" */
const RECRUTE_RE =
  /(?:^|\n)\s*([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,40}(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,30}){0,3})\s+(?:recrute|recherche|embauche)/i;

const DASH_LINE_RE =
  /(?:^|\n)\s*([A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,40}(?:\s+[A-ZÀÂÄÉÈÊËÏÎÔÙÛÜÇ][\wÀ-ÿ&.'’-]{1,30}){0,3})\s*[\-–—]\s*(?:CDI|CDD|Stage|Alternance|H\/F|F\/H)/i;

const JOB_TITLE_LABEL_RE =
  /(?:^|\n)\s*(?:intitul[eé]\s*(?:du\s*)?poste|titre\s*(?:du\s*)?poste|poste|job\s*title|position|r[oô]le)\s*[:\-–—]\s*([^\n]{3,100})/i;

const JOB_TITLE_HF_RE =
  /(?:^|\n)\s*([^\n]{5,90}?)\s*\((?:H\/F|F\/H|HF|M\/F)\)/i;

const JOB_TITLE_INLINE_RE =
  /(?:nous\s+(?:recherchons|cherchons)|recherche(?:ons)?)\s+(?:un[e]?\s+)?([^\n.]{5,80}?)(?:\s+(?:pour|afin|qui)\b|[.!]|$)/i;

const NOISE = new Set([
  "cdi",
  "cdd",
  "temps",
  "plein",
  "paris",
  "france",
  "remote",
  "hybride",
  "junior",
  "senior",
  "h/f",
  "hf",
  "f/h",
  "nous",
  "notre",
  "nos",
  "votre",
  "vos",
  "une",
  "un",
  "le",
  "la",
  "les",
  "des",
  "du",
  "poste",
  "offre",
  "emploi",
  "equipe",
  "équipes",
  "equipes",
  "team",
  "teams",
]);

export function slugFilename(name, { maxLen = 48 } = {}) {
  return (
    String(name || "")
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, maxLen)
      .replace(/-$/, "") || ""
  );
}

/**
 * Récupère l'employeur : LLM d'abord, puis heuristiques multiples.
 * @returns {string|null}
 */
export function extractCompany(jobText, llmCompany = null) {
  const fromLlm = cleanCompany(llmCompany);
  if (fromLlm) return fromLlm;

  const text = String(jobText || "");
  // Ordre de priorité (labels / recrute avant "chez/rejoindre" trop ambigus)
  const candidates = [];

  const labeled = text.match(LABEL_RE);
  if (labeled) candidates.push(labeled[1]);

  const labeledInline = text.match(LABEL_INLINE_RE);
  if (labeledInline) candidates.push(labeledInline[1]);

  const recrute = text.match(RECRUTE_RE);
  if (recrute) candidates.push(recrute[1]);

  const dash = text.match(DASH_LINE_RE);
  if (dash) candidates.push(dash[1]);

  const about = extractAboutCompany(text);
  if (about) candidates.push(about);

  // Domaine email / URL type careers.acme.com
  const mail = text.match(/@([a-z0-9-]+)\.(?:com|fr|io|co|net|org)\b/i);
  if (mail && !/gmail|outlook|hotmail|yahoo|proton/i.test(mail[1])) {
    candidates.push(titleCaseCompany(mail[1].replace(/-/g, " ")));
  }
  const url = text.match(
    /(?:https?:\/\/)?(?:www\.)?([a-z0-9-]+)\.(?:com|fr|io|co|net|org)\b/i,
  );
  if (url && !/linkedin|welcome|indeed|hellowork|google|github/i.test(url[1])) {
    candidates.push(titleCaseCompany(url[1].replace(/-/g, " ")));
  }

  for (const raw of candidates) {
    const c = cleanCompany(raw);
    if (c) return c;
  }
  return null;
}

/**
 * Extrait l'intitulé de poste déclaré dans la fiche (si présent).
 * @returns {string|null}
 */
export function extractJobTitle(jobText) {
  const text = String(jobText || "");
  const labeled = text.match(JOB_TITLE_LABEL_RE);
  if (labeled) {
    const t = cleanJobTitle(labeled[1]);
    if (t) return t;
  }
  const hf = text.match(JOB_TITLE_HF_RE);
  if (hf) {
    const t = cleanJobTitle(hf[1]);
    if (t) return t;
  }
  const inline = text.match(JOB_TITLE_INLINE_RE);
  if (inline && looksLikeJobTitle(inline[1])) {
    const t = cleanJobTitle(inline[1]);
    if (t) return t;
  }
  // Première ligne courte qui ressemble à un titre
  const first = text
    .split(/\n/)
    .map((l) => l.trim())
    .find((l) => l.length >= 8 && l.length <= 80);
  if (first && looksLikeJobTitle(first) && !looksLikeSentence(first)) {
    return cleanJobTitle(first);
  }
  return null;
}

function extractAboutCompany(text) {
  ABOUT_KW_RE.lastIndex = 0;
  let m;
  while ((m = ABOUT_KW_RE.exec(text)) !== null) {
    const rest = text.slice(m.index + m[0].length);
    // Préférer un nom propre (capitale)
    let name = rest.match(COMPANY_NAME_RE);
    if (!name) continue;
    const c = cleanCompany(name[1]);
    if (c) return c;
  }
  return null;
}

function cleanCompany(raw) {
  let t = String(raw || "")
    .replace(/\s+/g, " ")
    .replace(/[|•·].*$/, "")
    .replace(/\s*[-–—]\s*(cdi|cdd|stage|alternance|h\/f|f\/h).*$/i, "")
    .replace(/\s*\([^)]*\)\s*$/g, "")
    .replace(/[.,;:!?]+$/g, "")
    .trim();
  if (!t || t.length < 2 || t.length > 80) return null;

  // Refuse fragments de phrase / articles
  if (
    /^(une?|des?|du|la|le|les|nos?|notre|votre|vos|cette?|cet)\b/i.test(t)
  ) {
    return null;
  }
  if (/\b(équipe|equipes|équipes|teams?)\b/i.test(t) && !/\b(SAS|SA|SARL|Inc|Ltd)\b/i.test(t)) {
    return null;
  }

  const norm = t
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase();
  if (NOISE.has(norm)) return null;
  if (/^(poste|offre|mission|profil|description|intitule|titre)$/i.test(t)) return null;
  if (
    /^(developpeur|developer|ingenieur|ingénieur|chef|manager|expert|product|software)/i.test(
      t,
    ) &&
    t.split(/\s+/).length <= 3
  ) {
    // Évite de prendre un intitulé de poste pour une entreprise
    return null;
  }
  return t.slice(0, 80);
}

function cleanJobTitle(raw) {
  let t = String(raw || "")
    .replace(/\s+/g, " ")
    .replace(/\s*\((?:H\/F|F\/H|HF|M\/F)\)\s*/gi, " ")
    .replace(/\b(?:H\/F|F\/H|HF|M\/F)\b/gi, " ")
    .replace(/\s*[-–—]\s*(CDI|CDD|Stage|Alternance).*$/i, "")
    .replace(/[#*_`]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!t || t.length < 3 || t.length > 90) return null;
  if (/^(entreprise|societe|société|company|missions?|profil|description)/i.test(t)) return null;
  return t.slice(0, 90);
}

function looksLikeJobTitle(line) {
  return /developpeur|développeur|developer|engineer|ingénieur|chef de projet|product owner|manager|consultant|expert|fullstack|full-stack|frontend|backend/i.test(
    line,
  );
}

function looksLikeSentence(line) {
  return /^(chez|nous|rejoignez|vous|notre|dans|pour|avec)\b/i.test(line) || /[,.]/.test(line);
}

function titleCaseCompany(slug) {
  return String(slug)
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/**
 * Nom de fichier : {titre}-{entreprise}
 */
export function buildJobExportFilename(profileName, company) {
  const base = slugFilename(profileName, { maxLen: 48 }) || "cv";
  const org = slugFilename(company, { maxLen: 40 });
  return org ? `${base}-${org}` : base;
}
