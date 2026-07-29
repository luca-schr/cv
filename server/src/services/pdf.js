/**
 * Export PDF via Pandoc + WeasyPrint — remplissage A4 une page
 * (port de server/app/services/pdf.py).
 */
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { countPdfPagesFromFile } from "./pdf-fit.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SERVER_ROOT = path.resolve(__dirname, "../..");
const STYLE_FILE = path.join(SERVER_ROOT, "style.css");
const ASSETS_DIR = path.join(SERVER_ROOT, "assets");
const PHOTO_FILE = path.join(ASSETS_DIR, "lucas-schrever.jpg");
const PHOTO_PATH = "assets/lucas-schrever.jpg";

function which(cmd) {
  const r = spawnSync(process.platform === "win32" ? "where" : "which", [cmd], {
    encoding: "utf8",
  });
  return r.status === 0;
}

function weasyEnv() {
  const env = { ...process.env };
  if (process.platform === "win32") {
    env.WEASYPRINT_DLL_DIRECTORIES =
      process.env.WEASYPRINT_DLL_DIRECTORIES || "C:\\msys64\\mingw64\\bin";
  }
  return env;
}

function normalizePhotoPaths(markdown) {
  return String(markdown || "")
    .replace(/\]\(lucas-schrever\.jpg\)/g, `](${PHOTO_PATH})`)
    .replace(
      /src=["']lucas-schrever\.jpg["']/g,
      `src="${PHOTO_PATH}"`,
    );
}

function writeOverrideCss(tmpDir, layout) {
  const file = path.join(tmpDir, `cv-scale-${Date.now()}-${Math.random().toString(36).slice(2)}.css`);
  fs.writeFileSync(
    file,
    `:root {\n` +
      `  --cv-scale: ${layout.scale.toFixed(4)};\n` +
      `  --cv-gap-scale: ${layout.gapScale.toFixed(4)};\n` +
      `  --cv-line-height: ${layout.lineHeight.toFixed(3)};\n` +
      `}\n`,
    "utf8",
  );
  return file;
}

function runPandoc(mdPath, pdfPath, overrideCss, env) {
  if (!which("pandoc")) {
    throw new Error("Pandoc introuvable — installe pandoc et ajoute-le au PATH.");
  }
  const args = [
    mdPath,
    "-o",
    pdfPath,
    "--pdf-engine=weasyprint",
    `--css=${pathToFileURL(STYLE_FILE).href}`,
    `--css=${pathToFileURL(overrideCss).href}`,
    `--resource-path=${SERVER_ROOT}`,
  ];
  const r = spawnSync("pandoc", args, {
    cwd: SERVER_ROOT,
    encoding: "utf8",
    env,
  });
  if (r.status !== 0) {
    throw new Error((r.stderr || r.stdout || "Échec Pandoc / WeasyPrint").trim());
  }
}

function countSafe(pdfPath) {
  try {
    return countPdfPagesFromFile(pdfPath);
  } catch {
    return 1;
  }
}

function renderPdf(mdPath, pdfPath, env, layout, tmpDir) {
  const override = writeOverrideCss(tmpDir, layout);
  try {
    runPandoc(mdPath, pdfPath, override, env);
    const pdfBytes = fs.readFileSync(pdfPath);
    const pageCount = countSafe(pdfPath);
    return {
      pdfBytes,
      pageCount,
      scale: layout.scale,
      layout,
      fits: pageCount <= 1,
    };
  } finally {
    try {
      fs.unlinkSync(override);
    } catch {
      /* ignore */
    }
  }
}

function shrinkLayout(layout) {
  return {
    scale: Math.max(0.52, layout.scale - 0.035),
    gapScale: Math.max(0.62, layout.gapScale - 0.045),
    lineHeight: Math.max(1.1, layout.lineHeight - 0.018),
  };
}

function findFittingLayout(mdPath, pdfPath, env, tmpDir) {
  let layout = { scale: 1.0, gapScale: 1.0, lineHeight: 1.28 };
  let last = null;
  for (let i = 0; i < 14; i++) {
    last = renderPdf(mdPath, pdfPath, env, layout, tmpDir);
    if (last.fits) return { layout, best: last };
    layout = shrinkLayout(layout);
  }
  return { layout, best: last };
}

/**
 * Remplit au maximum la page A4 : recherche dichotomique sur l'échelle
 * (et les espacements) depuis un layout qui tient déjà sur 1 page.
 */
function maximizeFill(mdPath, pdfPath, env, base, seedBest, tmpDir) {
  let best = seedBest;
  if (!best || best.pageCount > 1) {
    best = renderPdf(mdPath, pdfPath, env, base, tmpDir);
  }
  if (best.pageCount > 1) return best;

  // Plafond : on cherche le plus grand scale qui reste sur 1 page
  let lo = base;
  let hiScale = Math.min(2.35, base.scale * 1.85);
  let hi = {
    scale: hiScale,
    gapScale: Math.min(1.55, base.gapScale * (hiScale / base.scale)),
    lineHeight: Math.min(1.4, base.lineHeight + 0.1),
  };

  // Si le plafond tient déjà, pousser encore un peu
  let hiTrial = renderPdf(mdPath, pdfPath, env, hi, tmpDir);
  if (hiTrial.fits) {
    best = hiTrial;
    lo = hi;
    hiScale = Math.min(2.6, hi.scale * 1.2);
    hi = {
      scale: hiScale,
      gapScale: Math.min(1.6, lo.gapScale * (hiScale / lo.scale)),
      lineHeight: Math.min(1.42, lo.lineHeight + 0.06),
    };
  }

  for (let i = 0; i < 12; i++) {
    const mid = {
      scale: (lo.scale + hi.scale) / 2,
      gapScale: (lo.gapScale + hi.gapScale) / 2,
      lineHeight: (lo.lineHeight + hi.lineHeight) / 2,
    };
    const trial = renderPdf(mdPath, pdfPath, env, mid, tmpDir);
    if (trial.fits) {
      lo = mid;
      best = trial;
    } else {
      hi = mid;
    }
  }

  return best;
}

function optimizeLayout(mdPath, pdfPath, env, tmpDir) {
  const { layout, best } = findFittingLayout(mdPath, pdfPath, env, tmpDir);
  return maximizeFill(mdPath, pdfPath, env, layout, best, tmpDir);
}

/**
 * @returns {{ pdf: Buffer, filename: string, pageCount: number, scale: number }}
 */
export function exportPdf(markdown, { filename = "cv" } = {}) {
  if (!fs.existsSync(STYLE_FILE)) {
    throw new Error("style.css introuvable à la racine du serveur");
  }
  if (!fs.existsSync(PHOTO_FILE)) {
    throw new Error(`Photo introuvable : ${PHOTO_FILE}`);
  }

  const md = normalizePhotoPaths(markdown);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "cv-pdf-"));
  const mdPath = path.join(tmp, "cv.md");
  const pdfPath = path.join(tmp, "cv.pdf");
  const env = weasyEnv();

  try {
    fs.writeFileSync(mdPath, md, "utf8");
    const result = optimizeLayout(mdPath, pdfPath, env, tmp);
    const safe =
      String(filename || "cv")
        .replace(/[^\w\-]+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-|-$/g, "") || "cv";
    return {
      pdf: result.pdfBytes,
      filename: `${safe}.pdf`,
      pageCount: result.pageCount,
      scale: result.scale,
    };
  } finally {
    try {
      fs.rmSync(tmp, { recursive: true, force: true });
    } catch {
      /* ignore */
    }
  }
}
