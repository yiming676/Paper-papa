CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS documents (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  source_file VARCHAR(500) NOT NULL,
  raw_text TEXT,
  markdown_content TEXT,
  annotated_markdown TEXT,
  study_report_json TEXT,
  asset_manifest_json TEXT,
  preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
  status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concepts (
  id SERIAL PRIMARY KEY,
  canonical_name VARCHAR(255) NOT NULL,
  normalized_name VARCHAR(255),
  concept_type VARCHAR(50) NOT NULL,
  generation_status VARCHAR(50) NOT NULL DEFAULT 'stub',
  short_explanation TEXT,
  long_explanation TEXT,
  prerequisites_json TEXT,
  aliases_json TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_concepts_normalized_name_type UNIQUE (normalized_name, concept_type)
);

CREATE TABLE IF NOT EXISTS document_entities (
  id SERIAL PRIMARY KEY,
  document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
  concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  raw_text VARCHAR(255) NOT NULL,
  normalized_text VARCHAR(255) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  first_occurrence_only BOOLEAN NOT NULL DEFAULT TRUE,
  position_start INTEGER NOT NULL,
  position_end INTEGER NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_relations (
  id SERIAL PRIMARY KEY,
  parent_concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  child_concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  relation_type VARCHAR(50) NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT uq_concept_relation UNIQUE (parent_concept_id, child_concept_id, relation_type)
);

CREATE TABLE IF NOT EXISTS user_concept_state (
  id SERIAL PRIMARY KEY,
  concept_id INTEGER NOT NULL UNIQUE REFERENCES concepts(id) ON DELETE CASCADE,
  status VARCHAR(50) NOT NULL DEFAULT 'unknown',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS concept_pages (
  id SERIAL PRIMARY KEY,
  concept_id INTEGER NOT NULL REFERENCES concepts(id) ON DELETE CASCADE,
  language VARCHAR(10) NOT NULL DEFAULT 'en',
  markdown_content TEXT NOT NULL,
  content_json TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_documents_id ON documents (id);
CREATE INDEX IF NOT EXISTS ix_concepts_id ON concepts (id);
CREATE INDEX IF NOT EXISTS ix_concepts_canonical_name ON concepts (canonical_name);
CREATE INDEX IF NOT EXISTS ix_concepts_normalized_name ON concepts (normalized_name);
CREATE INDEX IF NOT EXISTS ix_document_entities_document_id ON document_entities (document_id);
CREATE INDEX IF NOT EXISTS ix_document_entities_concept_id ON document_entities (concept_id);
CREATE INDEX IF NOT EXISTS ix_document_entities_normalized_text ON document_entities (normalized_text);
CREATE INDEX IF NOT EXISTS ix_user_concept_state_concept_id ON user_concept_state (concept_id);
