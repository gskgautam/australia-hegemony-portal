import sqlite3
from pathlib import Path

from datetime import datetime

from config import BASE_DIR, HEGEMONY_AXES, MODELS, PROMPT_TYPES


IAA_DB_PATH = Path(BASE_DIR) / "data" / "iaa_reviews.db"
# One block of reviewer questions per model output (model1_base .. model4_base).
MODEL_OUTPUT_TARGETS = [
    f"{m['review_slot']}_{kind}" for m in MODELS for kind in PROMPT_TYPES
]

IAA_REVIEW_COLUMNS = [
    "annotation_id",
    "reviewer_name",
    "reviewer_state",
    "annotation_creator",
    "review_timestamp",
    "editable",
    "completed",
    "prompt_q1",
    "prompt_q1_comment",
    "prompt_q2",
    "prompt_q2_comment",
    "prompt_q3",
    "prompt_q3_comment",
    "prompt_q4",
    "prompt_q4_comment",
]

for target in MODEL_OUTPUT_TARGETS:
    IAA_REVIEW_COLUMNS.extend([
        f"{target}_q1",
        f"{target}_q1_comment",
        f"{target}_q2",
        f"{target}_q2_comment",
        f"{target}_q3",
        f"{target}_q3_comment",
    ])

IAA_REVIEW_COLUMNS.extend([
    "ground_truth_q1",
    "ground_truth_q1_comment",
    "full_annotation_q1",
    "full_annotation_q1_comment",
    "full_annotation_q2",
    "full_annotation_q2_comment",
    "optional_comment",
    "admin_notes",
])

INTEGER_COLUMNS = {
    "editable",
    "completed",
    "prompt_q1",
    "prompt_q2",
    "prompt_q3",
    "prompt_q4",
    "ground_truth_q1",
    "full_annotation_q1",
    "full_annotation_q2",
}

for target in MODEL_OUTPUT_TARGETS:
    INTEGER_COLUMNS.update({
        f"{target}_q1",
        f"{target}_q2",
        f"{target}_q3",
    })


def _column_type(column_name):
    return "INTEGER" if column_name in INTEGER_COLUMNS else "TEXT"


def _connect():
    IAA_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(IAA_DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn):
    column_definitions = ",\n            ".join(
        f"{column} {_column_type(column)}"
        for column in IAA_REVIEW_COLUMNS
        if column not in {
            "annotation_id",
            "reviewer_name",
            "reviewer_state",
            "annotation_creator",
            "review_timestamp",
            "editable",
            "completed",
        }
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS iaa_reviews (
            review_id INTEGER PRIMARY KEY AUTOINCREMENT,
            annotation_id TEXT NOT NULL,
            reviewer_name TEXT NOT NULL,
            reviewer_state TEXT,
            annotation_creator TEXT,
            review_timestamp TEXT,
            editable INTEGER NOT NULL DEFAULT 1,
            completed INTEGER NOT NULL DEFAULT 0,
            {column_definitions},
            UNIQUE(annotation_id, reviewer_name)
        )
        """
    )
    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(iaa_reviews)").fetchall()
    }
    for column in IAA_REVIEW_COLUMNS:
        if column in existing_columns:
            continue
        conn.execute(f"ALTER TABLE iaa_reviews ADD COLUMN {column} {_column_type(column)}")
    _ensure_blind_label_schema(conn)
    conn.commit()


# =====================================================
# BLIND LABELS
# Before seeing the author's labels, each peer reviewer gives their own
# Yes/No label on every axis plus a hallucination decision for every model
# answer. These independent labels are what inter-annotator agreement
# (Cohen's / Fleiss' kappa) is computed from. Rows are write-once.
# =====================================================

BLIND_LABEL_FIELDS = ["hallucination", *HEGEMONY_AXES]


def _ensure_blind_label_schema(conn):
    label_columns = ",\n            ".join(
        f"{field} TEXT NOT NULL CHECK ({field} IN ('yes', 'no'))" for field in BLIND_LABEL_FIELDS
    )
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS iaa_blind_labels (
            label_id INTEGER PRIMARY KEY AUTOINCREMENT,
            annotation_id TEXT NOT NULL,
            reviewer_name TEXT NOT NULL,
            reviewer_state TEXT,
            model_key TEXT NOT NULL,
            prompt_type TEXT NOT NULL DEFAULT 'base',
            {label_columns},
            created_at TEXT NOT NULL,
            UNIQUE(annotation_id, reviewer_name, model_key, prompt_type)
        )
        """
    )


def fetch_blind_labels(annotation_id, reviewer_name):
    """{model_key: {kind: {field: 'yes'|'no'}}} for one reviewer, or {} if none yet."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM iaa_blind_labels WHERE annotation_id = ? AND reviewer_name = ?",
            (annotation_id, reviewer_name),
        ).fetchall()
    labels = {}
    for row in rows:
        labels.setdefault(row["model_key"], {})[row["prompt_type"]] = {
            field: row[field] for field in BLIND_LABEL_FIELDS
        }
    return labels


def has_blind_labels(annotation_id, reviewer_name):
    expected = len(MODELS) * len(PROMPT_TYPES)
    with _connect() as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM iaa_blind_labels WHERE annotation_id = ? AND reviewer_name = ?",
            (annotation_id, reviewer_name),
        ).fetchone()[0]
    return count >= expected


def save_blind_labels(annotation_id, reviewer_name, reviewer_state, labels):
    """
    labels: {model_key: {kind: {field: 'yes'|'no'}}} covering every model and prompt type.
    Raises PermissionError if this reviewer already labelled this item (labels are write-once).
    """
    rows = []
    for m in MODELS:
        for kind in PROMPT_TYPES:
            values = labels[m["key"]][kind]
            if any(values.get(field) not in ("yes", "no") for field in BLIND_LABEL_FIELDS):
                raise ValueError(f"Incomplete blind labels for {m['key']} {kind}.")
            rows.append((
                annotation_id, reviewer_name, reviewer_state, m["key"], kind,
                *[values[field] for field in BLIND_LABEL_FIELDS],
                datetime.utcnow().isoformat(),
            ))

    placeholders = ", ".join("?" for _ in rows[0])
    columns = ", ".join(
        ["annotation_id", "reviewer_name", "reviewer_state", "model_key", "prompt_type",
         *BLIND_LABEL_FIELDS, "created_at"]
    )
    with _connect() as conn:
        if conn.execute(
            "SELECT 1 FROM iaa_blind_labels WHERE annotation_id = ? AND reviewer_name = ? LIMIT 1",
            (annotation_id, reviewer_name),
        ).fetchone():
            raise PermissionError("Blind labels already submitted for this item.")
        conn.executemany(f"INSERT INTO iaa_blind_labels ({columns}) VALUES ({placeholders})", rows)
        conn.commit()


def list_blind_labels_for_export():
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM iaa_blind_labels ORDER BY annotation_id, model_key, reviewer_name"
        ).fetchall()
    return [dict(row) for row in rows]


def initialize_iaa_storage():
    with _connect():
        return str(IAA_DB_PATH)


def fetch_iaa_review(annotation_id, reviewer_name):
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM iaa_reviews
            WHERE annotation_id = ? AND reviewer_name = ?
            LIMIT 1
            """,
            (str(annotation_id or "").strip(), str(reviewer_name or "").strip()),
        ).fetchone()
    return dict(row) if row else None


def list_completed_iaa_annotation_ids_for_reviewer(reviewer_name):
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT annotation_id
            FROM iaa_reviews
            WHERE reviewer_name = ? AND completed = 1
            """,
            (str(reviewer_name or "").strip(),),
        ).fetchall()
    return {
        str(row["annotation_id"]).strip()
        for row in rows
        if str(row["annotation_id"]).strip()
    }


def count_completed_iaa_reviews_by_annotation():
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT annotation_id, COUNT(*) AS review_count
            FROM iaa_reviews
            WHERE completed = 1
            GROUP BY annotation_id
            """
        ).fetchall()
    return {
        str(row["annotation_id"]).strip(): int(row["review_count"] or 0)
        for row in rows
        if str(row["annotation_id"]).strip()
    }


def list_completed_iaa_review_counts_by_state_and_reviewer():
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT
                COALESCE(NULLIF(TRIM(reviewer_state), ''), 'Unknown') AS reviewer_state,
                COALESCE(NULLIF(TRIM(reviewer_name), ''), 'Unknown') AS reviewer_name,
                COUNT(*) AS completed_review_count
            FROM iaa_reviews
            WHERE completed = 1
            GROUP BY reviewer_state, reviewer_name
            ORDER BY reviewer_state COLLATE NOCASE ASC,
                     completed_review_count DESC,
                     reviewer_name COLLATE NOCASE ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def save_iaa_review(payload):
    annotation_id = str(payload.get("annotation_id") or "").strip()
    reviewer_name = str(payload.get("reviewer_name") or "").strip()
    if not annotation_id or not reviewer_name:
        raise ValueError("annotation_id and reviewer_name are required.")

    with _connect() as conn:
        existing = conn.execute(
            """
            SELECT review_id, completed, editable
            FROM iaa_reviews
            WHERE annotation_id = ? AND reviewer_name = ?
            LIMIT 1
            """,
            (annotation_id, reviewer_name),
        ).fetchone()

        if existing and int(existing["completed"] or 0) and not int(existing["editable"] or 0):
            raise PermissionError("This IAA review has already been submitted and locked.")

        values = [payload.get(column) for column in IAA_REVIEW_COLUMNS]
        if existing:
            set_clause = ", ".join(f"{column} = ?" for column in IAA_REVIEW_COLUMNS)
            conn.execute(
                f"""
                UPDATE iaa_reviews
                SET {set_clause}
                WHERE review_id = ?
                """,
                values + [int(existing["review_id"])],
            )
            conn.commit()
            return int(existing["review_id"]), "updated"

        placeholders = ", ".join("?" for _ in IAA_REVIEW_COLUMNS)
        conn.execute(
            f"""
            INSERT INTO iaa_reviews ({", ".join(IAA_REVIEW_COLUMNS)})
            VALUES ({placeholders})
            """,
            values,
        )
        conn.commit()
        return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0]), "created"


def list_iaa_reviews_for_export():
    with _connect() as conn:
        rows = conn.execute(
            f"""
            SELECT review_id, {", ".join(IAA_REVIEW_COLUMNS)}
            FROM iaa_reviews
            ORDER BY review_id ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]
