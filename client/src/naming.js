const PROFILE_SLUGS = {
  fullstack: { fr: "developpeur-fullstack", en: "fullstack-developer" },
};

const DEFAULT_COMPANY = { fr: "defaut", en: "default" };
const USED_KEY = "cv-used-basenames";

export function slugify(text, maxLen = 40) {
  const raw = String(text ?? "").trim();
  if (!raw) return "";
  return (
    raw
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/œ/gi, "oe")
      .replace(/æ/gi, "ae")
      .replace(/ß/g, "ss")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, maxLen) || ""
  );
}

export function profileKeyOf(profile) {
  return profile?.data?.key || (profile?.is_default ? "fullstack" : "") || "profil";
}

export function profileFileSlug(profile, english) {
  const key = profileKeyOf(profile);
  const lang = english ? "en" : "fr";
  if (PROFILE_SLUGS[key]?.[lang]) return PROFILE_SLUGS[key][lang];
  return slugify(profile?.name || key, 40) || "profil";
}

export function companyFileSlug(company, english) {
  const slug = slugify(company || "", 24);
  if (slug) return slug;
  return english ? DEFAULT_COMPANY.en : DEFAULT_COMPANY.fr;
}

export function suggestedBasename(profile, company, english) {
  const profileSlug = profileFileSlug(profile, english);
  const companySlug = companyFileSlug(company, english);
  const lang = english ? "en" : "fr";
  return `lucas-schrever-${profileSlug}-${companySlug}-${lang}`;
}

export function loadUsedBasenames() {
  try {
    const raw = JSON.parse(localStorage.getItem(USED_KEY) || "[]");
    return Array.isArray(raw) ? raw.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function saveUsedBasenames(names) {
  localStorage.setItem(USED_KEY, JSON.stringify(names));
}

export function uniqueBasename(base, used) {
  const root = (base || "lucas-schrever-cv").replace(/\.md$|\.pdf$/gi, "");
  if (!used.includes(root)) return root;
  let n = 1;
  while (used.includes(`${root}-${n}`)) n += 1;
  return `${root}-${n}`;
}

export function rememberBasename(base, used) {
  const name = (base || "").replace(/\.md$|\.pdf$/gi, "");
  if (!name) return used;
  if (used.includes(name)) return used;
  const next = [...used, name];
  saveUsedBasenames(next);
  return next;
}
