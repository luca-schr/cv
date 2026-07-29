import cors from "cors";
import express from "express";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { openDb } from "./db/index.js";
import { createApiRouter } from "./routes/api.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../..");
const PORT = Number(process.env.PORT || 8000);

const db = openDb();
const app = express();

app.use(cors());
app.use(express.json({ limit: "2mb" }));

app.get("/health", (_req, res) => res.json({ ok: true }));
app.use("/api", createApiRouter(db));

const clientDist = path.join(REPO_ROOT, "client", "dist");
app.use(express.static(clientDist));
app.get("*", (req, res, next) => {
  if (req.path.startsWith("/api")) return next();
  res.sendFile(path.join(clientDist, "index.html"), (err) => {
    if (err) res.status(404).end();
  });
});

const server = app.listen(PORT, () => {
  console.log(`CV API http://127.0.0.1:${PORT}`);
});

// Évite ECONNRESET sur les appels Ollama longs (proxy Vite)
server.keepAliveTimeout = 190_000;
server.headersTimeout = 195_000;
