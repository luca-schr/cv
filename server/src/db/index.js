import { DatabaseSync } from "node:sqlite";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { CATEGORIES, PROFILES } from "./seed-data.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const DATA_DIR = path.join(REPO_ROOT, "data");
const DB_PATH = path.join(DATA_DIR, "cv.db");

function ensureDir(dir) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

/** Thin wrapper so routes keep `.prepare().all/get/run` style. */
function wrapDb(raw) {
  return {
    prepare(sql) {
      const stmt = raw.prepare(sql);
      return {
        all(...params) {
          return stmt.all(...params);
        },
        get(...params) {
          return stmt.get(...params);
        },
        run(...params) {
          return stmt.run(...params);
        },
      };
    },
    exec(sql) {
      raw.exec(sql);
    },
    close() {
      raw.close();
    },
  };
}

export function openDb() {
  ensureDir(DATA_DIR);
  const raw = new DatabaseSync(DB_PATH);
  raw.exec("PRAGMA journal_mode = WAL;");
  raw.exec("PRAGMA foreign_keys = ON;");
  const db = wrapDb(raw);
  migrate(db);
  seedIfEmpty(db);
  return db;
}

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS categories (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      label_fr TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS profiles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE RESTRICT,
      is_default INTEGER NOT NULL DEFAULT 0,
      title TEXT,
      title_en TEXT,
      summary TEXT,
      summary_en TEXT,
      markdown TEXT NOT NULL,
      markdown_en TEXT,
      keywords TEXT,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_profiles_category ON profiles(category_id);
    CREATE INDEX IF NOT EXISTS idx_profiles_name ON profiles(name);
  `);
}

function seedIfEmpty(db) {
  const count = db.prepare("SELECT COUNT(*) AS n FROM categories").get().n;
  if (count > 0) {
    const hasDefault = db.prepare("SELECT id FROM profiles WHERE is_default = 1 LIMIT 1").get();
    if (!hasDefault) {
      const net = db
        .prepare(
          "SELECT id FROM profiles WHERE name LIKE '%Fullstack%' OR name LIKE '%fullstack%' LIMIT 1",
        )
        .get();
      if (net) {
        db.prepare("UPDATE profiles SET is_default = 1 WHERE id = ?").run(net.id);
      }
    }
    return;
  }

  const insertCat = db.prepare(
    "INSERT INTO categories (name, label_fr) VALUES (?, ?)",
  );
  for (const cat of CATEGORIES) {
    insertCat.run(cat.name, cat.label_fr);
  }

  const cats = db.prepare("SELECT id, name FROM categories").all();
  const catByName = Object.fromEntries(cats.map((c) => [c.name, c.id]));

  const insertProfile = db.prepare(`
    INSERT INTO profiles (
      name, category_id, is_default, title, title_en,
      summary, summary_en, markdown, markdown_en, keywords
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  for (const p of PROFILES) {
    insertProfile.run(
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

export { DB_PATH };
