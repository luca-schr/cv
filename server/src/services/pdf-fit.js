/**
 * Comptage de pages PDF via pypdf (même approche que FastAPI pdf_fit.py).
 * WeasyPrint compresse les objets — un parse regex du flux brut est insuffisant.
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const PY_COUNT_FILE = `
import sys
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader
print(len(PdfReader(sys.argv[1]).pages))
`.trim();

const PY_COUNT_STDIN = `
import sys, io
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader
data = sys.stdin.buffer.read()
print(len(PdfReader(io.BytesIO(data)).pages))
`.trim();

function runPython(args, { input } = {}) {
  for (const bin of ["python", "py"]) {
    const r = spawnSync(bin, args, {
      encoding: "utf8",
      input,
      windowsHide: true,
    });
    if (r.error?.code === "ENOENT") continue;
    if (r.status === 0) return r;
    if (r.status !== 0 && r.stderr) {
      throw new Error((r.stderr || r.stdout || "pypdf indisponible").trim());
    }
  }
  throw new Error("Python introuvable (requis pour compter les pages PDF via pypdf).");
}

export function countPdfPagesFromFile(pdfPath) {
  const r = runPython(["-c", PY_COUNT_FILE, pdfPath]);
  const n = Number.parseInt(String(r.stdout).trim(), 10);
  if (!Number.isFinite(n) || n < 1) {
    throw new Error(`Comptage pages invalide: ${r.stdout}`);
  }
  return n;
}

export function countPdfPages(pdfBytes) {
  const buf = Buffer.isBuffer(pdfBytes) ? pdfBytes : Buffer.from(pdfBytes);
  try {
    const r = runPython(["-c", PY_COUNT_STDIN], { input: buf });
    const n = Number.parseInt(String(r.stdout).trim(), 10);
    if (Number.isFinite(n) && n >= 1) return n;
  } catch {
    /* fallback fichier temporaire */
  }
  const tmp = path.join(os.tmpdir(), `cv-pages-${process.pid}-${Date.now()}.pdf`);
  try {
    fs.writeFileSync(tmp, buf);
    return countPdfPagesFromFile(tmp);
  } finally {
    try {
      fs.unlinkSync(tmp);
    } catch {
      /* ignore */
    }
  }
}
