-- Base de dados do conteúdo escolar (fonte: Google Drive "Estudo tê")
-- Objetivo: guardar o texto real dos scans + exercícios derivados dele.
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS subjects (
  id      INTEGER PRIMARY KEY,
  slug    TEXT NOT NULL UNIQUE,          -- castellano, mates, sociais, ingles, galego
  name    TEXT NOT NULL,                 -- nome como aparece no Drive
  drive_id TEXT
);

CREATE TABLE IF NOT EXISTS documents (
  id          INTEGER PRIMARY KEY,
  subject_id  INTEGER NOT NULL REFERENCES subjects(id),
  origin      TEXT NOT NULL,             -- livro | caderno
  drive_id    TEXT NOT NULL UNIQUE,
  name        TEXT NOT NULL,
  local_path  TEXT NOT NULL,
  sha256      TEXT NOT NULL,
  bytes       INTEGER NOT NULL,
  downloaded_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pages (
  id          INTEGER PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  page_no     INTEGER NOT NULL,
  UNIQUE(document_id, page_no)
);

CREATE TABLE IF NOT EXISTS page_text (
  page_id     INTEGER PRIMARY KEY REFERENCES pages(id) ON DELETE CASCADE,
  lang        TEXT NOT NULL,
  engine      TEXT NOT NULL,
  text        TEXT NOT NULL,
  chars       INTEGER NOT NULL,
  ocr_at      TEXT NOT NULL
);

-- Exercícios: nascem de uma página (source='ocr') ou são gerados a partir dela
-- (source='gerado'), sempre com a página de origem para auditoria.
CREATE TABLE IF NOT EXISTS exercises (
  id         INTEGER PRIMARY KEY,
  subject_id INTEGER NOT NULL REFERENCES subjects(id),
  page_id    INTEGER REFERENCES pages(id),
  unit       TEXT,                       -- unidade/tema detectado
  topic      TEXT,                       -- ex.: sumas con llevadas, sílabas
  kind       TEXT NOT NULL DEFAULT 'aberta', -- escolha_multipla|resposta_curta|calculo|aberta
  statement  TEXT NOT NULL,              -- enunciado (castellano)
  answer     TEXT,
  options    TEXT,                       -- JSON ["a","b","c"]
  difficulty INTEGER NOT NULL DEFAULT 1, -- 1..3
  lang       TEXT NOT NULL DEFAULT 'es-ES',
  source     TEXT NOT NULL DEFAULT 'ocr',
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ex_subject ON exercises(subject_id, topic);
CREATE INDEX IF NOT EXISTS idx_ex_page    ON exercises(page_id);
