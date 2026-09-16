const VERSIONS_KEY = "cv-export-versions";

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

export function stem({ title, company, english }) {
  const parts = ["lucas-schrever", slugify(title, 40) || "profil", slugify(company, 24) || "defaut"];
  if (english) parts.push("en");
  return parts.join("-");
}

export function buildBasename(opts, version = 1) {
  return `${stem(opts)}-v${Math.max(1, Number(version) || 1)}`;
}

export function loadVersions() {
  try {
    const raw = JSON.parse(localStorage.getItem(VERSIONS_KEY) || "{}");
    return raw && typeof raw === "object" ? raw : {};
  } catch {
    return {};
  }
}

export function nextVersion(stemKey, versions = loadVersions()) {
  return (Number(versions[stemKey]) || 0) + 1;
}

export function rememberVersion(stemKey, version) {
  const versions = loadVersions();
  const current = Number(versions[stemKey]) || 0;
  const next = Math.max(current, Number(version) || 1);
  versions[stemKey] = next;
  localStorage.setItem(VERSIONS_KEY, JSON.stringify(versions));
  return versions;
}
