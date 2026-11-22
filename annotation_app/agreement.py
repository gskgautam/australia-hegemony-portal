"""
Inter-annotator agreement from blind labels.

Each unit is one model answer (item x model). Its raters are the item's author
plus the peer reviewers who labelled it blind. Only units with at least
MIN_RATERS independent labels are used, and labels are never taken from
adjudicated or expert-revised values.
"""

from collections import defaultdict

from config import MODELS

MIN_RATERS = 3

_MODEL_LABELS = {m["key"]: m["label"] for m in MODELS}


def long_format_rows(records, blind_rows, fields):
    """
    One row per (item, model, prompt type, decision, rater).
    The author's labels come from the submitted record; reviewers' from blind labelling.
    """
    records_by_id = {r.get("id"): r for r in records}
    rows = []

    reviewed_ids = {row["annotation_id"] for row in blind_rows}
    for annotation_id in sorted(reviewed_ids):
        record = records_by_id.get(annotation_id)
        if not record:
            continue
        for model_key, kinds in (record.get("outputs") or {}).items():
            for kind, block in (kinds or {}).items():
                for field in fields:
                    if field == "hallucination":
                        label = block.get("hallucination", "")
                    else:
                        label = ((block.get("hegemony") or {}).get(field) or {}).get("present", "")
                    rows.append(_row(record, model_key, kind, field, record.get("annotator_name", ""), "author", label))

    for blind in blind_rows:
        record = records_by_id.get(blind["annotation_id"])
        if not record:
            continue
        for field in fields:
            rows.append(_row(record, blind["model_key"], blind["prompt_type"], field,
                             blind["reviewer_name"], "reviewer", blind[field]))
    return rows


def _row(record, model_key, kind, field, rater, role, label):
    return {
        "annotation_id": record.get("id", ""),
        "state": record.get("state", ""),
        "model_key": model_key,
        "model_label": _MODEL_LABELS.get(model_key, model_key),
        "prompt_type": kind,
        "decision": field,
        "rater": rater,
        "rater_role": role,
        "label": label,
    }


def fleiss_kappa_binary(units):
    """units: list of label lists ('yes'/'no'), each with the same number of raters n >= 2."""
    if not units:
        return None
    n = len(units[0])
    total_yes = sum(u.count("yes") for u in units)
    p_yes = total_yes / (len(units) * n)
    p_e = p_yes ** 2 + (1 - p_yes) ** 2
    p_i = [
        (u.count("yes") ** 2 + u.count("no") ** 2 - n) / (n * (n - 1))
        for u in units
    ]
    p_bar = sum(p_i) / len(p_i)
    if p_e == 1:
        return None  # every label identical: kappa undefined
    return (p_bar - p_e) / (1 - p_e)


def agreement_summary(long_rows, fields, min_raters=MIN_RATERS):
    """Per decision: units used, Yes prevalence, raw (all-raters-agree) agreement, Fleiss' kappa."""
    units = defaultdict(list)
    for row in long_rows:
        if row["label"] not in ("yes", "no"):
            continue
        key = (row["annotation_id"], row["model_key"], row["prompt_type"], row["decision"])
        units[key].append(row["label"])

    summary = []
    for field in fields:
        field_units = [
            labels[:min_raters]
            for (_, _, _, decision), labels in units.items()
            if decision == field and len(labels) >= min_raters
        ]
        if not field_units:
            summary.append({"decision": field, "units": 0, "yes_prevalence": None,
                            "raw_agreement": None, "fleiss_kappa": None})
            continue
        all_labels = [label for u in field_units for label in u]
        summary.append({
            "decision": field,
            "units": len(field_units),
            "yes_prevalence": all_labels.count("yes") / len(all_labels),
            "raw_agreement": sum(1 for u in field_units if len(set(u)) == 1) / len(field_units),
            "fleiss_kappa": fleiss_kappa_binary(field_units),
        })
    return summary
