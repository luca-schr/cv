export function errorDetail(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg || JSON.stringify(item)).join(" · ");
  }
  return fallback;
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    throw new Error(errorDetail(payload, `Erreur ${res.status}`));
  }
  if (res.status === 204) return null;
  const type = res.headers.get("content-type") || "";
  if (type.includes("application/json")) return res.json();
  return res;
}

export const api = {
  profiles: () => request("/api/profiles"),
  profile: (id, lang = "fr") => request(`/api/profiles/${id}?lang=${lang}`),
  exportPdf: (markdown, filename) =>
    request("/api/export/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ markdown, filename }),
    }),
};
