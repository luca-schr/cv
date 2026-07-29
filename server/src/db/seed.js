/**
 * Reseed / sync profils depuis seed-data.js (écrase markdown & métadonnées).
 * Usage: npm run seed
 */
import { openDb } from "./index.js";
import { CATEGORIES, PROFILES } from "./seed-data.js";

const db = openDb();

for (const cat of CATEGORIES) {
  const existing = db.prepare("SELECT id FROM categories WHERE name = ?").get(cat.name);
  if (existing) {
    db.prepare("UPDATE categories SET label_fr = ? WHERE id = ?").run(cat.label_fr, existing.id);
  } else {
    db.prepare("INSERT INTO categories (name, label_fr) VALUES (?, ?)").run(cat.name, cat.label_fr);
  }
}

const cats = db.prepare("SELECT id, name FROM categories").all();
const catByName = Object.fromEntries(cats.map((c) => [c.name, c.id]));

db.prepare("UPDATE profiles SET is_default = 0").run();

// Anciens profils fusionnés / renommés
const OBSOLETE = [
  "Développeur fullstack .NET/React",
  "Développeur fullstack Node/React",
];
for (const name of OBSOLETE) {
  db.prepare("DELETE FROM profiles WHERE name = ?").run(name);
}

for (const p of PROFILES) {
  const row = db.prepare("SELECT id FROM profiles WHERE name = ?").get(p.name);
  if (row) {
    db.prepare(
      `UPDATE profiles SET
        category_id = ?, is_default = ?, title = ?, title_en = ?,
        summary = ?, summary_en = ?, markdown = ?, markdown_en = ?, keywords = ?
      WHERE id = ?`,
    ).run(
      catByName[p.category],
      p.is_default ? 1 : 0,
      p.title,
      p.title_en,
      p.summary,
      p.summary_en,
      p.markdown,
      p.markdown_en,
      p.keywords,
      row.id,
    );
  } else {
    db.prepare(
      `INSERT INTO profiles (
        name, category_id, is_default, title, title_en,
        summary, summary_en, markdown, markdown_en, keywords
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    ).run(
      p.name,
      catByName[p.category],
      p.is_default ? 1 : 0,
      p.title,
      p.title_en,
      p.summary,
      p.summary_en,
      p.markdown,
      p.markdown_en,
      p.keywords,
    );
  }
}

const profiles = db.prepare("SELECT id, name, is_default FROM profiles").all();
console.log("synced profiles:", profiles.length);
for (const p of profiles) {
  console.log(`  ${p.is_default ? "*" : " "} ${p.id} ${p.name}`);
}
db.close();
