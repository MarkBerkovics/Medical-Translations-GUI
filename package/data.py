"""Load the translation workbook and persist reviewer decisions."""

from __future__ import annotations

import json
import math
import re
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXCEL_PATH = ROOT / "docs" / "artificial data.xlsx"
REVIEWS_PATH = ROOT / "data" / "reviews.json"

SEVERITIES = ("minor", "major", "critical")
VERDICTS = ("approved", "rejected")

_ERROR_HEADING = re.compile(r"טעות\s+\d+")
_COUNT_AND_SEVERITY = re.compile(
    r"(\d+)\s*[-–—]\s*(minor|major|critical)",
    re.IGNORECASE,
)
_TOKEN = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
_STOP_WORDS = {
    "a",
    "an",
    "the",
    "of",
    "on",
    "in",
    "at",
    "to",
    "for",
    "and",
    "or",
    "with",
    "was",
    "were",
    "is",
    "are",
    "be",
    "by",
    "from",
    "that",
    "this",
    "still",
}


def clean_text(value: object) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def parse_num_errors(value: object) -> tuple[int, str | None]:
    """Return the reported count and the document-level severity."""
    if isinstance(value, bool):
        raise ValueError(f"Unexpected Num_Errors value: {value!r}")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return 0, None
        return int(value), None

    text = clean_text(value)
    if not text:
        return 0, None
    if text.isdigit():
        return int(text), None

    match = _COUNT_AND_SEVERITY.fullmatch(text)
    if match is None:
        raise ValueError(f"Unexpected Num_Errors value: {value!r}")
    return int(match.group(1)), match.group(2).lower()


def parse_error_details(raw: object, severity: str | None) -> list[dict]:
    """Split the validator report into translation quote, reference quote, explanation."""
    text = clean_text(raw)
    if not text:
        return []

    errors = []
    for block in _ERROR_HEADING.split(text):
        chunks = [
            chunk.strip() for chunk in re.split(r"\n\s*\n", block) if chunk.strip()
        ]
        if not chunks:
            continue
        errors.append(
            {
                "id": f"v-{len(errors) + 1}",
                "severity": severity,
                "translation_excerpt": chunks[0],
                "ground_truth_excerpt": chunks[1] if len(chunks) > 1 else "",
                "explanation": "\n".join(chunks[2:]),
            }
        )
    return errors


def word_count(text: str) -> int:
    return len(text.split())


def _tokens(value: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end()) for match in _TOKEN.finditer(value)
    ]


def _content_words(excerpt: str) -> list[str]:
    words = [token.lower() for token, _, _ in _tokens(excerpt)]
    content = [word for word in words if word not in _STOP_WORDS and len(word) > 2]
    return content or words


def _close_span(text: str, excerpt: str) -> tuple[int, int] | None:
    """Find the ground-truth passage that best matches a non-exact validator phrase."""
    targets = _content_words(excerpt)
    tokens = _tokens(text)
    if not targets or not tokens:
        return None

    best: tuple[tuple[int, float, int], int, int] | None = None
    lookahead = 8
    for index, (word, start, _end) in enumerate(tokens):
        for offset, target in enumerate(targets):
            if word.lower() != target:
                continue
            cursor = index
            matched = 0
            first = start
            last = _end
            for target_word in targets[offset:]:
                found_at = None
                for look in range(cursor, min(len(tokens), cursor + lookahead)):
                    if tokens[look][0].lower() == target_word:
                        found_at = look
                        break
                if found_at is None:
                    break
                matched += 1
                last = tokens[found_at][2]
                cursor = found_at + 1
            if matched == 0:
                continue
            width = last - first
            if width > max(180, len(excerpt) * 5):
                continue
            coverage = matched / len(targets)
            if matched < 2 and width < 8:
                continue
            if coverage < 0.5 and matched < 2:
                continue
            score = (matched, coverage, -width)
            if best is None or score > best[0]:
                best = (score, first, last)
    if best is None:
        return None
    return best[1], best[2]


def locate_excerpt(text: str, excerpt: str) -> tuple[str, list[tuple[int, int]]]:
    """Return how an excerpt was found, and the character ranges to highlight.

    Exact quotes win. Otherwise the closest passage in the text is used, so a
    paraphrased ground-truth phrase still gets a highlight.
    """
    excerpt = excerpt.strip()
    if not text or not excerpt:
        return "none", []

    ranges: list[tuple[int, int]] = []
    start = 0
    while True:
        found = text.find(excerpt, start)
        if found < 0:
            break
        ranges.append((found, found + len(excerpt)))
        start = found + len(excerpt)
    if ranges:
        return "exact", ranges

    close = _close_span(text, excerpt)
    if close is None:
        return "none", []
    return "close", [close]


def load_documents(path: Path = EXCEL_PATH) -> list[dict]:
    frame = pd.read_excel(path)
    documents = []
    for offset, row in frame.iterrows():
        reported_count, severity = parse_num_errors(row["Num_Errors"])
        errors = parse_error_details(row["Error_Details"], severity)
        date = clean_text(row["Date"])
        unit = clean_text(row["Unit"])
        text_type = clean_text(row["Text_type"])
        documents.append(
            {
                "id": f"{date}|{unit}|{text_type}",
                "row": int(offset) + 2,
                "date": date,
                "unit": unit,
                "text_type": text_type,
                "label": f"{text_type} — {unit}",
                "hebrew": clean_text(row["Text_Hebrew"]),
                "english": clean_text(row["Text_English"]),
                "ground_truth": clean_text(row["Ground_Truth"]),
                "model": clean_text(row["Model"]),
                "severity": severity,
                "reported_count": reported_count,
                "word_count": word_count(clean_text(row["Text_Hebrew"])),
                "errors": errors,
            }
        )
    return documents


def blank_review() -> dict:
    return {
        "verdicts": {},
        "added": [],
        "completed_at": None,
        "updated_at": None,
        "label": "",
        "date": "",
    }


def load_reviews(path: Path = REVIEWS_PATH) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(payload, dict):
        return {}
    reviews = payload.get("reviews", payload)
    if not isinstance(reviews, dict):
        return {}
    return reviews


def save_reviews(reviews: dict, path: Path = REVIEWS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "reviews": reviews}
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _ensure_review(reviews: dict, meta: dict) -> dict:
    review = reviews.get(meta["id"])
    if not isinstance(review, dict):
        review = blank_review()
        reviews[meta["id"]] = review
    review.setdefault("verdicts", {})
    review.setdefault("added", [])
    review["label"] = meta["label"]
    review["date"] = meta["date"]
    return review


def _refresh_completion(review: dict, validator_ids: list[str]) -> None:
    if not validator_ids:
        return
    finished = all(
        (review["verdicts"].get(finding_id) or {}).get("verdict") in VERDICTS
        for finding_id in validator_ids
    )
    if finished and not review.get("completed_at"):
        review["completed_at"] = now_iso()
    elif not finished:
        review["completed_at"] = None


def _touch(meta: dict, mutate) -> dict:
    reviews = load_reviews()
    review = _ensure_review(reviews, meta)
    mutate(review)
    _refresh_completion(review, list(meta["validator_ids"]))
    review["updated_at"] = now_iso()
    save_reviews(reviews)
    return review


def review_meta(document: dict) -> dict:
    return {
        "id": document["id"],
        "label": document["label"],
        "date": document["date"],
        "validator_ids": [error["id"] for error in document["errors"]],
    }


def save_verdict(meta: dict, finding_id: str, verdict: str, remark: str) -> None:
    if verdict not in VERDICTS:
        raise ValueError(f"Unexpected verdict: {verdict}")

    def mutate(review: dict) -> None:
        review["verdicts"][finding_id] = {
            "verdict": verdict,
            "remark": remark,
            "updated_at": now_iso(),
        }

    _touch(meta, mutate)


def save_remark(meta: dict, finding_id: str, remark: str) -> None:
    def mutate(review: dict) -> None:
        current = review["verdicts"].get(finding_id) or {}
        review["verdicts"][finding_id] = {
            "verdict": current.get("verdict"),
            "remark": remark,
            "updated_at": now_iso(),
        }

    _touch(meta, mutate)


def save_added_remark(meta: dict, finding_id: str, remark: str) -> None:
    def mutate(review: dict) -> None:
        for item in review["added"]:
            if item.get("id") == finding_id:
                item["remark"] = remark
                item["updated_at"] = now_iso()
                break

    _touch(meta, mutate)


def add_finding(
    meta: dict,
    severity: str,
    translation_excerpt: str,
    ground_truth_excerpt: str,
    remark: str,
) -> str:
    if severity not in SEVERITIES:
        raise ValueError(f"Unexpected severity: {severity}")
    finding_id = f"h-{uuid.uuid4().hex[:10]}"

    def mutate(review: dict) -> None:
        review["added"].append(
            {
                "id": finding_id,
                "severity": severity,
                "translation_excerpt": translation_excerpt.strip(),
                "ground_truth_excerpt": ground_truth_excerpt.strip(),
                "remark": remark.strip(),
                "created_at": now_iso(),
            }
        )

    _touch(meta, mutate)
    return finding_id


def delete_finding(meta: dict, finding_id: str) -> None:
    def mutate(review: dict) -> None:
        review["added"] = [
            item for item in review["added"] if item.get("id") != finding_id
        ]

    _touch(meta, mutate)


def verdict_of(review: dict, finding_id: str) -> str | None:
    verdict = (review.get("verdicts") or {}).get(finding_id, {}).get("verdict")
    if verdict in VERDICTS:
        return verdict
    return None


def remark_of(review: dict, finding_id: str) -> str:
    return str((review.get("verdicts") or {}).get(finding_id, {}).get("remark") or "")


def status_view(document: dict, review: dict) -> dict:
    total = len(document["errors"])
    judged = sum(1 for error in document["errors"] if verdict_of(review, error["id"]))
    added = len(review.get("added") or [])
    if total == 0:
        label = "אין ממצאים" if added == 0 else f"אין ממצאים · {added} נוספו"
        kind = "empty"
    elif judged == 0:
        label = "לא התחיל"
        kind = "new"
    elif judged < total:
        label = f"בבדיקה ({judged}/{total})"
        kind = "progress"
    else:
        label = "הושלם"
        kind = "done"
    return {
        "kind": kind,
        "label": label,
        "judged": judged,
        "total": total,
        "added": added,
    }


def dashboard_counts(documents: list[dict], reviews: dict, today: str) -> dict:
    open_findings = 0
    waiting_documents = 0
    finished_today = 0
    for document in documents:
        review = reviews.get(document["id"]) or blank_review()
        view = status_view(document, review)
        open_findings += view["total"] - view["judged"]
        if view["kind"] in {"new", "progress"}:
            waiting_documents += 1
        completed = str(review.get("completed_at") or "")
        if completed[:10] == today:
            finished_today += 1
    return {
        "open_findings": open_findings,
        "waiting_documents": waiting_documents,
        "finished_today": finished_today,
    }
