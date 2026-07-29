/**
 * Matching offre ↔ profil : keywords + shortlist pour Ollama.
 */

function normalize(text) {
  return String(text || "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .replace(/[^a-z0-9+.#/\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const STOP = new Set([
  "de",
  "du",
  "des",
  "le",
  "la",
  "les",
  "et",
  "en",
  "un",
  "une",
  "the",
  "and",
  "or",
  "for",
  "with",
]);

function tokenize(text) {
  return normalize(text)
    .split(/[\s,/|;]+/)
    .map((t) => t.trim())
    .filter((t) => t.length >= 2 && !STOP.has(t));
}

/**
 * @param {string} jobText
 * @param {object} profile row with name, title, keywords, summary
 * @returns {{ score: number, hits: string[] }}
 */
export function scoreProfile(jobText, profile) {
  const blob = normalize(jobText);
  if (!blob || blob.length < 10) return { score: 0, hits: [] };

  const keywords = String(profile.keywords || "")
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);

  const nameTokens = tokenize(`${profile.name} ${profile.title || ""}`);
  const pool = [...new Set([...keywords, ...nameTokens])];

  let score = 0;
  const hits = [];

  for (const raw of pool) {
    const k = normalize(raw);
    if (!k || k.length < 2) continue;
    const escaped = k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const re = new RegExp(`(?:^|[^a-z0-9])${escaped}(?:[^a-z0-9]|$)`, "i");
    if (re.test(blob) || blob.includes(k)) {
      const weight = k.length >= 4 ? 3 : 2;
      score += weight;
      hits.push(raw);
    }
  }

  const title = normalize(profile.title || profile.name || "");
  if (title && blob.includes(title.slice(0, Math.min(title.length, 24)))) {
    score += 4;
  }

  return { score, hits: [...new Set(hits)].slice(0, 12) };
}

/** Seuil minimal pour accepter une adéquation keywords. */
export const MATCH_THRESHOLD = 6;

/** Sous ce score : pas d'appel Ollama, écart trop grand. */
export const LOW_SCORE_SKIP_OLLAMA = 3;

export const SHORTLIST_SIZE = 5;

/** Message unique quand l'écart compétences est trop grand. */
export const NEED_BETTER_CV_MSG = "Besoin de créer un CV plus pertinent";

/** Part de compétences offre absentes du profil au-delà de laquelle on alerte. */
export const SKILL_GAP_RATIO = 0.55;

/** Minimum de compétences détectées dans l'offre pour juger l'écart. */
export const SKILL_GAP_MIN_JOB_SKILLS = 3;

/**
 * Compétences « techniques » citées dans l'offre (heuristique légère).
 */
export function extractJobSkillHints(jobText) {
  const blob = normalize(jobText);
  const hints = new Set();
  // Tokens alphanumériques / technos (.net, c#, node.js…)
  const re = /(?:^|[^a-z0-9])([a-z][a-z0-9+#.]{1,24}|c#|\.net|node\.?js|next\.?js|vue\.?js)(?=[^a-z0-9]|$)/gi;
  let m;
  while ((m = re.exec(blob))) {
    const t = normalize(m[1]);
    if (t.length >= 2 && !STOP.has(t) && !/^\d+$/.test(t)) hints.add(t);
  }
  return [...hints];
}

/**
 * Écart compétences offre ↔ profil (keywords + nom).
 * @returns {{ gap: boolean, missing: string[], jobSkills: string[], covered: number, ratio: number }}
 */
export function assessSkillGap(jobText, profile) {
  const jobSkills = extractJobSkillHints(jobText);
  const profilePool = [
    ...String(profile?.keywords || "")
      .split(",")
      .map((k) => normalize(k.trim()))
      .filter(Boolean),
    ...tokenize(`${profile?.name || ""} ${profile?.title || ""} ${profile?.summary || ""}`),
  ];
  const profileSet = new Set(profilePool);

  const missing = [];
  let covered = 0;
  for (const js of jobSkills) {
    const hit =
      profileSet.has(js) ||
      [...profileSet].some(
        (p) => p.length >= 3 && js.length >= 3 && (p.includes(js) || js.includes(p)),
      );
    if (hit) covered += 1;
    else missing.push(js);
  }

  const total = jobSkills.length;
  const ratio = total > 0 ? missing.length / total : 0;
  const gap =
    total >= SKILL_GAP_MIN_JOB_SKILLS && ratio >= SKILL_GAP_RATIO;

  return {
    gap,
    missing: missing.slice(0, 10),
    jobSkills: jobSkills.slice(0, 16),
    covered,
    ratio,
  };
}

function withGapFields(result, jobText, profile) {
  const skillGap = profile
    ? assessSkillGap(jobText, profile)
    : { gap: true, missing: [], jobSkills: extractJobSkillHints(jobText), covered: 0, ratio: 1 };
  const needsBetter =
    !result.matched || skillGap.gap || (result.score != null && result.score < MATCH_THRESHOLD);
  return {
    ...result,
    needs_better_cv: needsBetter,
    missing_skills: skillGap.missing,
    skill_gap_ratio: skillGap.ratio,
    message: needsBetter && !result.matched
      ? NEED_BETTER_CV_MSG
      : needsBetter && result.matched
        ? `${result.message} — ${NEED_BETTER_CV_MSG}`
        : result.message,
  };
}

/**
 * Classe tous les profils par score décroissant.
 */
export function rankProfiles(jobText, profiles) {
  return (profiles || [])
    .map((profile) => {
      const { score, hits } = scoreProfile(jobText, profile);
      return { profile, score, hits };
    })
    .sort((a, b) => b.score - a.score);
}

/**
 * Matching keywords seul (fallback).
 */
export function findBestProfile(jobText, profiles) {
  const ranked = rankProfiles(jobText, profiles);
  const best = ranked[0] || null;
  if (!best || best.score < MATCH_THRESHOLD) {
    return withGapFields(
      {
        matched: false,
        message: NEED_BETTER_CV_MSG,
        score: best?.score ?? 0,
        hits: best?.hits ?? [],
        profile: null,
        shortlist: [],
      },
      jobText,
      best?.profile || null,
    );
  }
  return withGapFields(
    {
      matched: true,
      message: `Profil proposé : ${best.profile.name}`,
      score: best.score,
      hits: best.hits,
      profile: best.profile,
      shortlist: ranked.slice(0, SHORTLIST_SIZE),
    },
    jobText,
    best.profile,
  );
}

/**
 * Prépare shortlist pour Ollama. null shortlist = skip Ollama (trop faible).
 */
export function buildMatchContext(jobText, profiles) {
  const ranked = rankProfiles(jobText, profiles);
  const best = ranked[0] || null;
  if (!best || best.score < LOW_SCORE_SKIP_OLLAMA) {
    const gap = withGapFields(
      {
        skipOllama: true,
        matched: false,
        message: NEED_BETTER_CV_MSG,
        score: best?.score ?? 0,
        hits: best?.hits ?? [],
        profile: null,
        shortlist: [],
      },
      jobText,
      best?.profile || null,
    );
    return gap;
  }
  const shortlist = ranked
    .filter((r) => r.score > 0)
    .slice(0, SHORTLIST_SIZE)
    .map((r) => ({
      id: r.profile.id,
      name: r.profile.name,
      category: r.profile.category_name || r.profile.category_label || "",
      title: r.profile.title,
      summary: r.profile.summary,
      keywords: r.profile.keywords,
      score: r.score,
      hits: r.hits,
      profile: r.profile,
    }));
  if (!shortlist.length) {
    return withGapFields(
      {
        skipOllama: true,
        matched: false,
        message: NEED_BETTER_CV_MSG,
        score: best.score,
        hits: best.hits,
        profile: null,
        shortlist: [],
      },
      jobText,
      best.profile,
    );
  }
  return {
    skipOllama: false,
    bestKeywords: best,
    shortlist,
    ranked,
  };
}

/**
 * Résout la décision Ollama contre la shortlist + fallback keywords.
 */
export function resolveOllamaDecision(decision, context, jobText = "") {
  const shortlist = context.shortlist || [];
  const ids = new Set(shortlist.map((s) => Number(s.id)));
  const best = context.bestKeywords;
  const reason = String(decision?.reason || "").trim().slice(0, 220);
  let profileId = decision?.profile_id;
  if (profileId === "null" || profileId === "") profileId = null;
  if (profileId != null) profileId = Number(profileId);
  const confidence = Number(decision?.confidence);
  const lowConfidence = Number.isFinite(confidence) && confidence < 0.45;

  if (profileId != null && ids.has(profileId) && !lowConfidence) {
    const hit = shortlist.find((s) => Number(s.id) === profileId);
    return withGapFields(
      {
        matched: true,
        message: `Profil proposé : ${hit.name}`,
        score: hit.score,
        hits: hit.hits,
        profile: hit.profile,
        reason,
        source: "ollama",
        fallback: false,
      },
      jobText,
      hit.profile,
    );
  }

  // Ollama dit null, confidence basse, ou id invalide
  if (best && best.score >= MATCH_THRESHOLD && !lowConfidence && profileId != null) {
    return withGapFields(
      {
        matched: true,
        message: `Profil proposé : ${best.profile.name}`,
        score: best.score,
        hits: best.hits,
        profile: best.profile,
        reason: reason || "Fallback matching local (réponse Ollama invalide).",
        source: "keywords",
        fallback: true,
      },
      jobText,
      best.profile,
    );
  }

  if (best && best.score >= MATCH_THRESHOLD && (profileId == null || lowConfidence)) {
    // Match keywords existe mais Ollama / écart compétences → alerte CV
    return withGapFields(
      {
        matched: true,
        message: `Profil proposé : ${best.profile.name}`,
        score: best.score,
        hits: best.hits,
        profile: best.profile,
        reason: reason || NEED_BETTER_CV_MSG,
        source: profileId == null ? "ollama" : "keywords",
        fallback: profileId == null,
      },
      jobText,
      best.profile,
    );
  }

  return withGapFields(
    {
      matched: false,
      message: NEED_BETTER_CV_MSG,
      score: best?.score ?? 0,
      hits: best?.hits ?? [],
      profile: null,
      reason: reason || undefined,
      source: "ollama",
      fallback: false,
    },
    jobText,
    best?.profile || null,
  );
}
