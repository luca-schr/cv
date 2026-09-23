import type { NamingOpts } from "./types";

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

export function stem({ title, english }: NamingOpts): string {
  const parts = ["lucas-schrever", slugify(title, 40) || "profil"];
  if (english) parts.push("en");
  return parts.join("-");
}

export function buildBasename(opts: NamingOpts): string {
  return stem(opts);
}
