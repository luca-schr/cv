import type { NamingOpts, VersionMap } from "./types";

const VERSIONS_KEY = "cv-export-versions";

export function slugify(text: string | null | undefined, maxLen = 40): string {
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

export function stem({ title, company, english }: NamingOpts): string {
  const parts = ["lucas-schrever", slugify(title, 40) || "profil", slugify(company, 24) || "defaut"];
  if (english) parts.push("en");
  return parts.join("-");
}

export function buildBasename(opts: NamingOpts, version = 1): string {
  return `${stem(opts)}-v${Math.max(1, Number(version) || 1)}`;
}

export function loadVersions(): VersionMap {
  try {
    const raw: unknown = JSON.parse(localStorage.getItem(VERSIONS_KEY) || "{}");
    if (raw && typeof raw === "object" && !Array.isArray(raw)) {
      return raw as VersionMap;
    }
    return {};
  } catch {
    return {};
  }
}

export function nextVersion(stemKey: string, versions: VersionMap = loadVersions()): number {
  return (Number(versions[stemKey]) || 0) + 1;
}

export function rememberVersion(stemKey: string, version: number): VersionMap {
  const versions = loadVersions();
  const current = Number(versions[stemKey]) || 0;
  const next = Math.max(current, Number(version) || 1);
  versions[stemKey] = next;
  localStorage.setItem(VERSIONS_KEY, JSON.stringify(versions));
  return versions;
}
