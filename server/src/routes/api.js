import { Router } from "express";
import { adaptProfileToJob, repairCvMarkdownHeadings } from "../services/adapt.js";
import { checkOllamaStatus } from "../services/ollama.js";
import { exportPdf } from "../services/pdf.js";
import {
  buildJobExportFilename,
  extractCompany,
  slugFilename,
} from "../services/filename.js";

export function createApiRouter(db) {
  const router = Router();

  router.get("/ping", (_req, res) => {
    res.json({ ok: true });
  });

  router.get("/llm/status", async (_req, res) => {
    try {
      const status = await checkOllamaStatus();
      res.json(status);
    } catch (err) {
      res.status(500).json({ detail: err.message || "Status Ollama impossible" });
    }
  });

  router.get("/categories", (_req, res) => {
    const rows = db
      .prepare("SELECT id, name, label_fr FROM categories ORDER BY label_fr")
      .all();
    res.json({ items: rows });
  });

  router.get("/profiles", (req, res) => {
    const q = String(req.query.q || "").trim();
    const category = String(req.query.category || "").trim();
    const params = [];
    let sql = `
      SELECT p.id, p.name, p.is_default, p.title, p.title_en, p.summary, p.summary_en,
             p.keywords, p.created_at,
             c.id AS category_id, c.name AS category_name, c.label_fr AS category_label
      FROM profiles p
      JOIN categories c ON c.id = p.category_id
      WHERE 1=1
    `;
    if (q) {
      sql += ` AND (
        p.name LIKE ? OR p.title LIKE ? OR p.summary LIKE ? OR p.keywords LIKE ?
        OR c.label_fr LIKE ? OR c.name LIKE ?
      )`;
      const like = `%${q}%`;
      params.push(like, like, like, like, like, like);
    }
    if (category) {
      if (/^\d+$/.test(category)) {
        sql += " AND c.id = ?";
        params.push(Number(category));
      } else {
        sql += " AND c.name = ?";
        params.push(category);
      }
    }
    sql += " ORDER BY p.is_default DESC, p.name ASC";
    const items = db.prepare(sql).all(...params).map(mapProfileSummary);
    res.json({ items, total: items.length });
  });

  router.get("/profiles/default", (_req, res) => {
    const row = db
      .prepare(
        `SELECT p.*, c.name AS category_name, c.label_fr AS category_label
         FROM profiles p JOIN categories c ON c.id = p.category_id
         WHERE p.is_default = 1 LIMIT 1`,
      )
      .get();
    if (!row) return res.status(404).json({ detail: "Aucun profil par défaut" });
    res.json(mapProfileDetail(row));
  });

  router.get("/profiles/:id", (req, res) => {
    const row = db
      .prepare(
        `SELECT p.*, c.name AS category_name, c.label_fr AS category_label
         FROM profiles p JOIN categories c ON c.id = p.category_id
         WHERE p.id = ?`,
      )
      .get(Number(req.params.id));
    if (!row) return res.status(404).json({ detail: "Profil introuvable" });
    res.json(mapProfileDetail(row));
  });

  router.delete("/profiles/:id", (req, res) => {
    const id = Number(req.params.id);
    const row = db.prepare("SELECT id, is_default FROM profiles WHERE id = ?").get(id);
    if (!row) return res.status(404).json({ detail: "Profil introuvable" });
    if (row.is_default) {
      return res.status(400).json({ detail: "Impossible de supprimer le profil par défaut." });
    }
    db.prepare("DELETE FROM profiles WHERE id = ?").run(id);
    res.status(204).end();
  });

  /**
   * Fiche de poste → profil le plus proche (sélection UI ou matching) →
   * adapte titre générique, descriptif & compétences. Ne modifie pas la base.
   */
  router.post("/analyze", async (req, res) => {
    try {
      const jobText = String(req.body?.job_text || "").trim();
      const english = Boolean(req.body?.english);
      const profileId = Number(req.body?.profile_id);

      if (jobText.length < 10) {
        return res.status(400).json({ detail: "Colle une offre (min. 10 caractères)." });
      }

      const all = db
        .prepare(
          `SELECT p.*, c.name AS category_name, c.label_fr AS category_label,
                  c.id AS category_id
           FROM profiles p JOIN categories c ON c.id = p.category_id`,
        )
        .all();

      let row = null;
      let matchedVia = "selected";

      if (Number.isFinite(profileId) && profileId > 0) {
        row = all.find((p) => p.id === profileId) || null;
        if (!row) return res.status(404).json({ detail: "Profil introuvable" });
      } else {
        const { findBestProfile } = await import("../services/match.js");
        const best = findBestProfile(jobText, all);
        if (!best.matched || !best.profile) {
          return res.json({
            matched: false,
            adapted: false,
            message: best.message || "Aucun profil assez proche",
            profile: null,
          });
        }
        row = best.profile;
        matchedVia = "closest";
      }

      const base = mapProfileDetail(row, english);
      const adapted = await adaptProfileToJob(base, jobText, { english });
      const company = adapted.company || extractCompany(jobText, null);
      const filename = buildJobExportFilename(adapted.title || base.name, company);

      const profile = {
        ...base,
        title: adapted.title || base.title,
        summary: adapted.summary || base.summary,
        markdown: adapted.markdown,
        filename,
        company,
      };

      res.json({
        matched: true,
        adapted: true,
        matched_via: matchedVia,
        message:
          matchedVia === "closest"
            ? `${adapted.message} (profil le plus proche)`
            : adapted.message,
        reason: adapted.reason,
        source: adapted.source,
        fallback: Boolean(adapted.fallback),
        company,
        profile,
      });
    } catch (err) {
      console.error("[analyze]", err);
      if (!res.headersSent) {
        res.status(503).json({
          detail: err.message || "Adaptation impossible",
        });
      }
    }
  });

  router.post("/export/pdf", (req, res) => {
    const markdown = repairCvMarkdownHeadings(String(req.body?.markdown || "").trim());
    const filename = String(req.body?.filename || "cv").trim() || "cv";
    if (!markdown) return res.status(400).json({ detail: "Markdown vide." });
    try {
      const { pdf, filename: outName } = exportPdf(markdown, { filename });
      res.setHeader("Content-Type", "application/pdf");
      res.setHeader("Content-Disposition", `attachment; filename="${outName}"`);
      res.send(pdf);
    } catch (err) {
      res.status(503).json({ detail: err.message || "Export PDF impossible" });
    }
  });

  return router;
}

function mapProfileSummary(row) {
  return {
    id: row.id,
    name: row.name,
    is_default: Boolean(row.is_default),
    title: row.title,
    title_en: row.title_en,
    summary: row.summary,
    category: {
      id: row.category_id,
      name: row.category_name,
      label_fr: row.category_label,
    },
    created_at: row.created_at,
  };
}

function mapProfileDetail(row, english = false) {
  const useEn = english && row.markdown_en;
  return {
    ...mapProfileSummary(row),
    summary: useEn && row.summary_en ? row.summary_en : row.summary,
    title: useEn && row.title_en ? row.title_en : row.title,
    markdown: useEn ? row.markdown_en : row.markdown,
    markdown_en: row.markdown_en,
    keywords: row.keywords,
    filename: slugFilename(row.name) || "cv",
  };
}
