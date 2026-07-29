import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CONFIG_PATH = path.resolve(__dirname, "../../config/llm.yaml");

function parseSimpleYaml(text) {
  const out = {};
  for (const line of String(text || "").split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const m = /^([A-Za-z0-9_]+)\s*:\s*(.+)$/.exec(trimmed);
    if (!m) continue;
    let val = m[2].trim();
    if (val === "true") val = true;
    else if (val === "false") val = false;
    else if (/^\d+$/.test(val)) val = Number(val);
    else if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    out[m[1]] = val;
  }
  return out;
}

export function loadLlmConfig() {
  const defaults = {
    enabled: false,
    provider: "ollama",
    model: "llama3.2",
    base_url: "http://localhost:11434",
    timeout_seconds: 25,
  };
  if (!fs.existsSync(CONFIG_PATH)) return defaults;
  try {
    const parsed = parseSimpleYaml(fs.readFileSync(CONFIG_PATH, "utf8"));
    return { ...defaults, ...parsed };
  } catch {
    return defaults;
  }
}

export async function checkOllamaStatus() {
  const config = loadLlmConfig();
  const model = config.model || "llama3.2";
  const baseUrl = String(config.base_url || "http://localhost:11434").replace(/\/$/, "");
  const result = {
    enabled: Boolean(config.enabled),
    model,
    base_url: baseUrl,
    server_ok: false,
    model_ready: false,
    message: "Ollama : vérification…",
  };
  if (!result.enabled) {
    result.message = "Ollama désactivé (config/llm.yaml)";
    return result;
  }
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 2500);
    const res = await fetch(`${baseUrl}/api/tags`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    result.server_ok = true;
    const installed = new Set(
      (body.models || []).map((m) => String(m.name || "").split(":")[0]),
    );
    result.model_ready = installed.has(model);
    result.message = result.model_ready
      ? `Ollama OK — ${model}`
      : `Modèle absent — ollama pull ${model}`;
  } catch {
    result.message = "Ollama inaccessible — lance ollama serve";
  }
  return result;
}

/**
 * Appel Ollama /api/chat format JSON.
 * @returns {object} parsed JSON
 */
export async function chatJson(messages, { temperature = 0.2, timeoutSeconds } = {}) {
  const config = loadLlmConfig();
  if (!config.enabled) {
    throw new Error("Ollama désactivé");
  }
  const baseUrl = String(config.base_url || "http://localhost:11434").replace(/\/$/, "");
  const timeoutMs =
    Math.max(5, Number(timeoutSeconds ?? config.timeout_seconds) || 25) * 1000;
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const res = await fetch(`${baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: ctrl.signal,
      body: JSON.stringify({
        model: config.model || "llama3.2",
        messages,
        stream: false,
        format: "json",
        options: { temperature },
      }),
    });
    if (!res.ok) {
      throw new Error(`Ollama HTTP ${res.status}`);
    }
    const body = await res.json();
    const raw = String(body?.message?.content || "").trim();
    try {
      return parseJsonLoose(raw);
    } catch {
      throw new Error("Réponse Ollama JSON invalide");
    }
  } catch (err) {
    if (err?.name === "AbortError") {
      throw new Error("Ollama timeout");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

function parseJsonLoose(raw) {
  let text = raw.trim();
  if (text.startsWith("```")) {
    text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  }
  return JSON.parse(text);
}
