from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def run_lightweight_migrations(engine: Engine) -> None:
    inspector = inspect(engine)
    if "documents" not in inspector.get_table_names():
        return

    document_columns = {column["name"] for column in inspector.get_columns("documents")}
    if "preferred_language" not in document_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE documents "
                    "ADD COLUMN preferred_language VARCHAR(10) NOT NULL DEFAULT 'en'"
                )
            )
    if "study_report_json" not in document_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN study_report_json TEXT"))
    if "asset_manifest_json" not in document_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE documents ADD COLUMN asset_manifest_json TEXT"))

    if "concepts" in inspector.get_table_names():
        concept_columns = {column["name"] for column in inspector.get_columns("concepts")}
        if "normalized_name" not in concept_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE concepts ADD COLUMN normalized_name VARCHAR(255)"))
                connection.execute(text("UPDATE concepts SET normalized_name = lower(canonical_name) WHERE normalized_name IS NULL"))
        if "generation_status" not in concept_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE concepts ADD COLUMN generation_status VARCHAR(50) NOT NULL DEFAULT 'generated'"))
        if "aliases_json" not in concept_columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE concepts ADD COLUMN aliases_json TEXT"))

    if "concept_pages" not in inspector.get_table_names():
        return

    concept_page_columns = {column["name"] for column in inspector.get_columns("concept_pages")}
    if "language" not in concept_page_columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE concept_pages "
                    "ADD COLUMN language VARCHAR(10) NOT NULL DEFAULT 'en'"
                )
            )
    if "content_json" not in concept_page_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE concept_pages ADD COLUMN content_json TEXT"))
