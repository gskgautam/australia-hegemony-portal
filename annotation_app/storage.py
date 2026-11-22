"""
Annotation storage.

Records live in one SQLite table, as the consortium recommends an SQL database
(#faqs, 19 Oct 2026). Each row keeps the full record as JSON,
plus a few indexed columns for filtering.
"""

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime

from config import COUNTRY, DB_PATH, HEADERS, HEGEMONY_AXES, MODEL_KEYS, PROMPT_TYPES


# =====================================================
# DATABASE
# =====================================================

def _connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_storage():
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS annotations (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE,
                timestamp TEXT,
                annotator_name TEXT,
                state TEXT,
                record_json TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_annotations_state ON annotations(state)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_annotations_annotator ON annotations(annotator_name)")


def _row_values(record):
    return (
        record["id"],
        record.get("timestamp"),
        record.get("annotator_name"),
        record.get("state"),
        json.dumps(record, ensure_ascii=False),
    )


def load_records():
    """All records, oldest first (insertion order)."""
    with closing(_connect()) as conn:
        rows = conn.execute("SELECT record_json FROM annotations ORDER BY seq").fetchall()
    return [json.loads(row["record_json"]) for row in rows]


def save_record(record):
    """Insert a record, or replace it in place if its id already exists."""
    with closing(_connect()) as conn, conn:
        conn.execute(
            """
            INSERT INTO annotations (id, timestamp, annotator_name, state, record_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                timestamp = excluded.timestamp,
                annotator_name = excluded.annotator_name,
                state = excluded.state,
                record_json = excluded.record_json
            """,
            _row_values(record),
        )


def update_record_fields(record_id, field_updates):
    """Merge field_updates into one stored record. Returns True if it existed."""
    with closing(_connect()) as conn, conn:
        row = conn.execute(
            "SELECT record_json FROM annotations WHERE id = ?", (record_id,)
        ).fetchone()
        if not row:
            return False
        record = json.loads(row["record_json"])
        record.update(field_updates)
        conn.execute(
            "UPDATE annotations SET record_json = ? WHERE id = ?",
            (json.dumps(record, ensure_ascii=False), record_id),
        )
    return True


def delete_records(record_ids):
    ids = [str(i) for i in record_ids if i]
    if not ids:
        return 0
    with closing(_connect()) as conn, conn:
        cur = conn.executemany("DELETE FROM annotations WHERE id = ?", [(i,) for i in ids])
        return cur.rowcount


# =====================================================
# HEGEMONY EXTRACTION
# =====================================================

def extract_hegemony(form, prefix):
    """prefix is f"{model_key}_{kind}", e.g. "qwen3_8_27b_base"."""
    result = {}

    for axis in HEGEMONY_AXES:
        present = form.get(f"{prefix}_{axis}_hegemony", "no")
        impact = form.get(f"{prefix}_{axis}_impact", "").strip()

        if present == "no" or impact == "" or impact.upper() == "NULL":
            impact = ""

        result[axis] = {"present": present, "impact": impact}

    return result


# =====================================================
# RECORD BUILDER (CANONICAL)
# =====================================================

def build_record(form):
    outputs = {}
    for model_key in MODEL_KEYS:
        outputs[model_key] = {}
        for kind in PROMPT_TYPES:
            prefix = f"{model_key}_{kind}"
            outputs[model_key][kind] = {
                "text": form.get(f"{prefix}_output"),
                "hallucination": "yes" if form.get(f"{prefix}_hallucination") == "yes" else "no",
                "hegemony": extract_hegemony(form, prefix),
            }

    return {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "annotator_name": form["annotator_name"],
        "country": COUNTRY,
        "region": form["region"],
        "state": form["state"],
        "prompts": {"base": form.get("base_prompt")},
        "outputs": outputs,
        "ground_truth": form.get("ground_truth"),
        "references": form.get("references", ""),
        "expert_reviews": form.get("expert_reviews", ""),
        "isAccept": form.get("isAccept", ""),
        "annotator_addressed": form.get("annotator_addressed", ""),
    }


# =====================================================
# CSV FLATTENING (column order = config.HEADERS)
# =====================================================

def json_to_row(record):
    row = [
        record.get("id", ""),
        record.get("timestamp", ""),
        record.get("annotator_name", ""),
        record.get("country", COUNTRY),
        record.get("region", ""),
        record.get("state", ""),
        (record.get("prompts") or {}).get("base", ""),
    ]

    outputs = record.get("outputs") or {}
    for model_key in MODEL_KEYS:
        for kind in PROMPT_TYPES:
            block = (outputs.get(model_key) or {}).get(kind) or {}
            row.append(block.get("text", ""))
            row.append(block.get("hallucination", ""))
            hegemony = block.get("hegemony") or {}
            for axis in HEGEMONY_AXES:
                axis_data = hegemony.get(axis) or {}
                row.append(axis_data.get("present", "no"))
                row.append(axis_data.get("impact", ""))

    row += [
        record.get("ground_truth", ""),
        record.get("references", ""),
        record.get("expert_reviews", ""),
        record.get("isAccept", ""),
        record.get("annotator_addressed", ""),
    ]

    assert len(row) == len(HEADERS)
    return row
