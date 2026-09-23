import type { Lang, ProfileDetail, ProfileSummary } from "./types";

type ErrorPayload = {
  detail?: string | Array<{ msg?: string } | string>;
};

export function errorDetail(payload: ErrorPayload | null | undefined, fallback: string): string {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => (typeof item === "string" ? item : item.msg || JSON.stringify(item)))
      .join(" · ");
  }
  return fallback;
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const payload = (await res.json().catch(() => ({}))) as ErrorPayload;
    throw new Error(errorDetail(payload, `Erreur ${res.status}`));
  }
  if (res.status === 204) return null as T;
  const type = res.headers.get("content-type") || "";
  if (type.includes("application/json")) return (await res.json()) as T;
  return res as T;
}

export const api = {
  profiles: () => request<ProfileSummary[]>("/api/selectprofile"),
  profile: (id: string, lang: Lang = "fr") =>
    request<ProfileDetail>(`/api/selectprofile/${id}?lang=${lang}`),
  exportPdf: (markdown: string, filename: string) =>
    request<Response>("/api/export/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown, filename }),
    }),
  applyDefault: (id: string, markdown: string, lang: Lang) =>
    request<{
      id: string;
      lang: Lang;
      other_lang: Lang;
      ok: boolean;
      translated: boolean;
      error?: string | null;
    }>("/api/applydefault", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile_id: id, markdown, lang }),
    }),
};
