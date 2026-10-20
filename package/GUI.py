"""Review UI for Hebrew-to-English medical translations.

Run from the project root:

    streamlit run package/GUI.py
"""

from __future__ import annotations

import hashlib
import uuid
from collections import Counter
from datetime import date
from html import escape

import streamlit as st

import data

st.set_page_config(
    page_title="סקירת תרגומים",
    page_icon="✓",
    layout="wide",
    initial_sidebar_state="expanded",
)

SEVERITY_LABEL = {
    "minor": "נמוכה",
    "major": "גבוהה",
    "critical": "קריטית",
}
SEVERITY_COLOR = {
    "minor": ("#fef3c7", "#b45309"),
    "major": ("#ffedd5", "#c2410c"),
    "critical": ("#ffe4e6", "#e11d48"),
    None: ("#dcfce7", "#15803d"),
}
LIST_WIDTHS = [2.5, 1.35, 1.1, 1.4, 0.7, 0.7, 1.3]


APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  background: #f3f6f9;
}
.stApp {
  direction: rtl;
  color: #1f2937;
  font-family: "Heebo", "Arial Hebrew", Arial, sans-serif;
}
[data-testid="stSidebar"] {
  background: #ffffff;
  border-left: 1px solid #e6edf2;
}
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1440px;
  padding-top: 1.1rem;
}
[data-testid="stHeader"] { background: transparent; }
.page-head h1, .doc-title {
  margin: 0;
  font-size: 1.7rem;
  line-height: 1.25;
  font-weight: 700;
  color: #12232b;
}
.page-head p, .doc-meta {
  margin: 0.2rem 0 0;
  color: #64748b;
  font-size: 0.95rem;
}
.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  padding: 0.3rem 0.2rem 0.8rem;
}
.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #0f766e;
  color: white;
  display: grid;
  place-items: center;
  font-weight: 700;
}
.brand strong { display: block; font-size: 1rem; }
.brand span { color: #64748b; font-size: 0.82rem; }
.kpi {
  background: #fff;
  border: 1px solid #e6edf2;
  border-radius: 16px;
  padding: 0.9rem 1rem 0.75rem;
  min-height: 92px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.kpi-label { color: #64748b; font-size: 0.92rem; font-weight: 500; }
.kpi-value { font-size: 2rem; font-weight: 700; line-height: 1.15; margin-top: 0.15rem; }
.kpi-red { color: #e11d48; }
.kpi-teal { color: #0f766e; }
.kpi-slate { color: #1f2937; }
.th { color: #64748b; font-size: 0.8rem; font-weight: 600; }
.cell { color: #1f2937; font-size: 0.95rem; }
.cell-muted { color: #334155; font-size: 0.95rem; }
.count-pill {
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  font-weight: 700;
}
.status {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.18rem 0.7rem;
  font-size: 0.8rem;
  font-weight: 600;
  white-space: nowrap;
}
.status-new { background: #f1f5f9; color: #475569; }
.status-progress { background: #ccfbf1; color: #0f766e; }
.status-done { background: #dcfce7; color: #166534; }
.status-empty { background: #f8fafc; color: #64748b; }
hr.row-sep { margin: 0.1rem 0; border: none; border-top: 1px solid #eef2f6; }
.summary { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; margin: 0.35rem 0 0.2rem; }
.chip {
  border-radius: 999px;
  padding: 0.18rem 0.7rem;
  font-size: 0.82rem;
  font-weight: 650;
  background: #f8fafc;
  color: #334155;
}
.chip-total { background: #e6fffb; color: #0f766e; }
.chip-critical { background: #ffe4e6; color: #be123c; }
.chip-major { background: #ffedd5; color: #c2410c; }
.chip-minor { background: #fef3c7; color: #b45309; }
.chip-added { background: #e2e8f0; color: #334155; }
.quote {
  border-radius: 10px;
  padding: 0.45rem 0.7rem;
  line-height: 1.45;
  font-size: 0.92rem;
}
.quote-tr { background: #fff1f2; }
.quote-gt { background: #f0fdf4; }
.quote-label {
  display: block;
  color: #64748b;
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 0.12rem;
}
.finding-title { margin: 0; font-weight: 600; color: #1f2937; }
[class*="st-key-open-"] button,
[class*="st-key-unit-"] button {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  color: #1f2937 !important;
  font-weight: 650 !important;
  justify-content: flex-start !important;
  text-align: right !important;
  padding: 0.25rem 0.15rem !important;
}
[class*="st-key-open-"] button:hover,
[class*="st-key-unit-"] button:hover {
  color: #0f766e !important;
  background: #f0fdfa !important;
}
[class*="st-key-open-"] button p,
[class*="st-key-unit-"] button p { white-space: normal !important; font-size: 0.98rem !important; }
[class*="st-key-no-"] button[kind="primary"] {
  background-color: #be123c !important;
  border-color: #be123c !important;
  color: #ffffff !important;
}
#review-panels {
  height: calc(100vh - 292px);
  min-height: 460px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.panels {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  direction: rtl;
}
.panel {
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e6edf2;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.panel-head {
  padding: 0.65rem 0.9rem;
  font-weight: 700;
  border-bottom: 1px solid #eef2f6;
  background: #f8fafc;
}
.panel[data-role="translation"] .panel-head { background: #fff7f7; }
.panel[data-role="ground"] .panel-head { background: #f3fbf6; }
.panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0.9rem 1rem 1.1rem;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.7;
  font-size: 16px;
}
.panel-body::-webkit-scrollbar { width: 10px; }
.panel-body::-webkit-scrollbar-thumb { background: #d6dee6; border-radius: 999px; }
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.9rem;
  color: #64748b;
  font-size: 0.82rem;
  padding: 0 0.2rem;
}
.swatch {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 3px;
  margin-left: 0.25rem;
  vertical-align: -1px;
}
.swatch.tr { background: #fecdd3; }
.swatch.gt { background: #bbf7d0; }
mark.hl {
  border-radius: 3px;
  padding: 0 2px;
  color: inherit;
}
mark.hl.tr { background: #fecdd3; }
mark.hl.gt { background: #bbf7d0; }
mark.hl.human { outline: 1px dashed #64748b; }
mark.hl.focus { outline: 2px solid #0f766e; }
iframe { border: none !important; color-scheme: light; }
input[aria-label="ציטוט שגוי מהתרגום"],
input[aria-label="ציטוט נכון מתרגום הייחוס"] {
  direction: ltr;
  text-align: left;
}
@media (max-width: 760px) {
  #review-panels { height: auto; min-height: 0; }
  .panels { grid-template-columns: 1fr; }
  .panel-body { height: 280px; flex: none; }
}
</style>
"""


PANELS_SCRIPT = """
<script>
(function () {
  var root = document.getElementById("review-panels");
  if (!root || root.getAttribute("data-bound") === "1") return;
  root.setAttribute("data-bound", "1");
  var panels = Array.prototype.slice.call(root.querySelectorAll(".panel-body"));
  var docId = root.getAttribute("data-doc-id") || "";
  var focusToken = root.getAttribute("data-focus-token") || "";
  var storageKey = "shiba-scroll:" + docId;
  var focusKey = "shiba-focus:" + docId;
  var lock = false;
  var track = false;

  function maxScroll(el) {
    return el.scrollHeight - el.clientHeight;
  }
  function ratioOf(el) {
    var max = maxScroll(el);
    if (!(max > 0)) return 0;
    return el.scrollTop / max;
  }
  function applyRatio(source) {
    var ratio = ratioOf(source);
    panels.forEach(function (other) {
      if (other === source) return;
      var max = maxScroll(other);
      if (max > 0) other.scrollTop = ratio * max;
    });
    try { sessionStorage.setItem(storageKey, String(ratio)); } catch (err) {}
  }
  panels.forEach(function (src) {
    src.addEventListener("scroll", function () {
      if (!track || lock) return;
      lock = true;
      applyRatio(src);
      lock = false;
    });
  });
  function center(el) {
    var body = el.closest(".panel-body");
    if (!body) return;
    var top = el.offsetTop - body.clientHeight * 0.33;
    if (!(top > 0)) top = 0;
    body.scrollTop = top;
  }
  function restore() {
    var saved = parseFloat(sessionStorage.getItem(storageKey) || "0");
    if (!(saved > 0)) return;
    lock = true;
    panels.forEach(function (panel) {
      var max = maxScroll(panel);
      if (max > 0) panel.scrollTop = saved * max;
    });
    lock = false;
  }
  function focusNow() {
    var translation = root.querySelector('[data-role="translation"] [data-focus="1"]');
    var ground = root.querySelector('[data-role="ground"] [data-focus="1"]');
    var hebrew = root.querySelector('[data-role="hebrew"]');
    var last = "";
    try { last = sessionStorage.getItem(focusKey) || ""; } catch (err) {}
    if (focusToken && focusToken !== last && (translation || ground)) {
      lock = true;
      if (translation) center(translation);
      if (ground) center(ground);
      var source = translation ? translation.closest(".panel-body") : ground.closest(".panel-body");
      var ratio = ratioOf(source);
      var maxHebrew = hebrew ? maxScroll(hebrew) : 0;
      if (hebrew && maxHebrew > 0) hebrew.scrollTop = ratio * maxHebrew;
      try {
        sessionStorage.setItem(storageKey, String(ratio));
        sessionStorage.setItem(focusKey, focusToken);
      } catch (err) {}
    lock = false;
    return;
    }
    restore();
  }
  function whenReady(attempt) {
    var ready = panels.some(function (panel) { return maxScroll(panel) > 20; });
    if (!ready && attempt < 40) {
      setTimeout(function () { whenReady(attempt + 1); }, 50);
      return;
    }
    focusNow();
    // Wait until the programmatic scroll events have fired, then follow the user.
    setTimeout(function () { track = true; }, 200);
  }
  whenReady(0);
})();
</script>
"""


def widget_key(*parts: str) -> str:
    return hashlib.sha1("::".join(parts).encode()).hexdigest()[:12]


@st.cache_data(show_spinner=False)
def get_documents(_mtime: float) -> list[dict]:
    return data.load_documents()


def selected_document_id() -> str | None:
    raw = st.query_params.get("doc")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if not raw:
        return None
    return str(raw)


def open_document(document_id: str) -> None:
    st.session_state["focus_id"] = None
    st.session_state["focus_token"] = ""
    st.query_params["doc"] = document_id


def close_document() -> None:
    st.session_state["focus_id"] = None
    st.session_state["focus_token"] = ""
    if "doc" in st.query_params:
        del st.query_params["doc"]


def remember_remark(state_key: str, saved: str) -> None:
    if state_key not in st.session_state:
        st.session_state[state_key] = saved


def save_validator_remark(meta: dict, finding_id: str, state_key: str) -> None:
    data.save_remark(meta, finding_id, st.session_state.get(state_key, ""))


def save_human_remark(meta: dict, finding_id: str, state_key: str) -> None:
    data.save_added_remark(meta, finding_id, st.session_state.get(state_key, ""))


def save_verdict_click(
    meta: dict, finding_id: str, verdict: str, state_key: str
) -> None:
    data.save_verdict(meta, finding_id, verdict, st.session_state.get(state_key, ""))
    st.toast("נשמר")


def focus_finding(finding_id: str) -> None:
    st.session_state["focus_id"] = finding_id
    st.session_state["focus_token"] = uuid.uuid4().hex


def delete_finding_click(meta: dict, finding_id: str) -> None:
    data.delete_finding(meta, finding_id)
    if st.session_state.get("focus_id") == finding_id:
        st.session_state["focus_id"] = None
        st.session_state["focus_token"] = ""
    st.toast("הממצא נמחק")


def render_flash() -> None:
    flash = st.session_state.pop("flash", None)
    if not flash:
        return
    if flash["kind"] == "warning":
        st.warning(flash["text"])
    else:
        st.success(flash["text"])


def locate_spans(
    text: str, excerpt: str, kind: str, finding_id: str, focused: bool, human: bool
) -> list[dict]:
    _match, ranges = data.locate_excerpt(text, excerpt)
    return [
        {
            "start": start,
            "end": end,
            "kind": kind,
            "id": finding_id,
            "focused": focused,
            "human": human,
        }
        for start, end in ranges
    ]


def can_highlight(text: str, excerpt: str) -> bool:
    match, _ranges = data.locate_excerpt(text, excerpt)
    return match != "none"


def highlight(text: str, spans: list[dict]) -> str:
    def overlaps(start: int, end: int, occupied: list[tuple[int, int]]) -> bool:
        return any(not (end <= begin or start >= stop) for begin, stop in occupied)

    kept = []
    occupied: list[tuple[int, int]] = []
    # The finding the user asked to see wins over a longer overlapping phrase.
    groups = (
        [span for span in spans if span["focused"]],
        [span for span in spans if not span["focused"]],
    )
    for group in groups:
        for span in sorted(
            group, key=lambda item: (item["start"], item["start"] - item["end"])
        ):
            if overlaps(span["start"], span["end"], occupied):
                continue
            kept.append(span)
            occupied.append((span["start"], span["end"]))
    kept.sort(key=lambda span: span["start"])

    parts = []
    cursor = 0
    for span in kept:
        parts.append(escape(text[cursor : span["start"]]))
        classes = ["hl", span["kind"]]
        if span["human"]:
            classes.append("human")
        if span["focused"]:
            classes.append("focus")
        focus_attr = ' data-focus="1"' if span["focused"] else ""
        parts.append(
            f'<mark class="{" ".join(classes)}" data-finding="{escape(span["id"], quote=True)}"{focus_attr}>'
            f"{escape(text[span['start'] : span['end']])}</mark>"
        )
        cursor = span["end"]
    parts.append(escape(text[cursor:]))
    return "".join(parts)


def active_focus(document: dict, review: dict) -> tuple[str | None, str]:
    focus_id = st.session_state.get("focus_id")
    known = {error["id"] for error in document["errors"]}
    known.update(item.get("id") for item in review.get("added") or [])
    if focus_id not in known:
        return None, ""
    return focus_id, str(st.session_state.get("focus_token") or "")


def build_panels_html(
    document: dict, review: dict, focus_id: str | None, focus_token: str
) -> str:
    translation_spans: list[dict] = []
    ground_spans: list[dict] = []
    sources = [(error, False) for error in document["errors"]] + [
        (item, True) for item in review.get("added") or []
    ]
    for item, human in sources:
        finding_id = item["id"]
        focused = finding_id == focus_id
        translation_spans.extend(
            locate_spans(
                document["english"],
                item.get("translation_excerpt", ""),
                "tr",
                finding_id,
                focused,
                human,
            )
        )
        ground_spans.extend(
            locate_spans(
                document["ground_truth"],
                item.get("ground_truth_excerpt", ""),
                "gt",
                finding_id,
                focused,
                human,
            )
        )

    panels = [
        ("hebrew", "מקור בעברית", "rtl", escape(document["hebrew"])),
        (
            "translation",
            "תרגום",
            "ltr",
            highlight(document["english"], translation_spans),
        ),
        (
            "ground",
            "תרגום ייחוס",
            "ltr",
            highlight(document["ground_truth"], ground_spans),
        ),
    ]
    columns = []
    for role, title, direction, body in panels:
        columns.append(
            f'<section class="panel" data-role="{role}">'
            f'<div class="panel-head">{title}</div>'
            f'<div class="panel-body" data-role="{role}" dir="{direction}">{body}</div>'
            "</section>"
        )
    return (
        f'<div id="review-panels" data-doc-id="{escape(document["id"], quote=True)}" '
        f'data-focus-token="{escape(focus_token, quote=True)}">'
        f'<div class="panels">{"".join(columns)}</div>'
        '<div class="legend">'
        "<span>גלילה בחלונית אחת מזיזה את שלושתן</span>"
        '<span><i class="swatch tr"></i>קטע בתרגום</span>'
        '<span><i class="swatch gt"></i>קטע בתרגום הייחוס</span>'
        "</div>"
        f"{PANELS_SCRIPT}"
        "</div>"
    )


def render_panels(document: dict, review: dict) -> None:
    focus_id, focus_token = active_focus(document, review)
    # One frame holds all three texts so they can share a scroll position.
    st.iframe(
        """
        <style>
          html, body { margin: 0; height: 100%; background: #f3f6f9; overflow: hidden; }
          #review-panels { height: 100% !important; min-height: 0 !important; }
        </style>
        """
        + build_panels_html(document, review, focus_id, focus_token)
        + APP_CSS,
        height=560,
    )


def quote_block(label: str, text: str, kind: str) -> str:
    return (
        f'<div class="quote quote-{kind}">'
        f'<span class="quote-label">{label}</span>'
        f"{escape(text) if text else '—'}"
        "</div>"
    )


def render_remark(label_key: str, saved: str, on_change, args: tuple) -> None:
    remember_remark(label_key, saved)
    st.text_input(
        "הערה",
        key=label_key,
        label_visibility="collapsed",
        placeholder="הערה לממצא זה",
        on_change=on_change,
        args=args,
    )


def render_validator_finding(
    document: dict, review: dict, error: dict, meta: dict
) -> None:
    finding_id = error["id"]
    verdict = data.verdict_of(review, finding_id)
    state_key = f"remark-{widget_key(document['id'], finding_id)}"
    background, foreground = SEVERITY_COLOR.get(error["severity"], SEVERITY_COLOR[None])
    translation = error["translation_excerpt"]
    ground = error["ground_truth_excerpt"]
    can_show = can_highlight(document["english"], translation) or can_highlight(
        document["ground_truth"], ground
    )

    with st.container(border=True):
        head = st.columns([1.1, 4.2, 1.15], vertical_alignment="center")
        head[0].markdown(
            f"<span class='chip' style='background:{background};color:{foreground}'>"
            f"{escape(SEVERITY_LABEL.get(error['severity'], 'לא צוינה'))}</span>",
            unsafe_allow_html=True,
        )
        head[1].markdown(
            f"<p class='finding-title'>{escape(error['explanation'] or 'ממצא ללא הסבר')}</p>",
            unsafe_allow_html=True,
        )
        head[2].button(
            "הצג בטקסט",
            key=f"focus-{widget_key(document['id'], finding_id)}",
            disabled=not can_show,
            on_click=focus_finding,
            args=(finding_id,),
            width="stretch",
        )

        quotes = st.columns(2)
        quotes[0].markdown(
            quote_block("תרגום", translation, "tr"), unsafe_allow_html=True
        )
        quotes[1].markdown(
            quote_block("תרגום ייחוס", ground, "gt"), unsafe_allow_html=True
        )
        ground_match, _ranges = data.locate_excerpt(document["ground_truth"], ground)
        if ground and ground_match == "close":
            st.caption(
                "הנוסח הנכון לא מופיע כלשונו, לכן הודגש הקטע הקרוב בתרגום הייחוס."
            )
        elif ground and ground_match == "none":
            st.caption("הנוסח הנכון לא נמצא בתרגום הייחוס, ולכן אין הדגשה שם.")

        actions = st.columns([1.25, 1.25, 3.2], vertical_alignment="center")
        actions[0].button(
            "הזיהוי נכון",
            key=f"yes-{widget_key(document['id'], finding_id)}",
            type="primary" if verdict == "approved" else "secondary",
            help="הוולידטור צדק: זו שגיאת תרגום אמיתית.",
            on_click=save_verdict_click,
            args=(meta, finding_id, "approved", state_key),
            width="stretch",
        )
        actions[1].button(
            "הזיהוי שגוי",
            key=f"no-{widget_key(document['id'], finding_id)}",
            type="primary" if verdict == "rejected" else "secondary",
            help="הוולידטור טעה: זו לא שגיאת תרגום.",
            on_click=save_verdict_click,
            args=(meta, finding_id, "rejected", state_key),
            width="stretch",
        )
        with actions[2]:
            render_remark(
                state_key,
                data.remark_of(review, finding_id),
                save_validator_remark,
                (meta, finding_id, state_key),
            )


def render_human_finding(document: dict, review: dict, item: dict, meta: dict) -> None:
    finding_id = item["id"]
    state_key = f"human-remark-{widget_key(document['id'], finding_id)}"
    background, foreground = SEVERITY_COLOR.get(
        item.get("severity"), SEVERITY_COLOR[None]
    )
    translation = item.get("translation_excerpt") or ""
    ground = item.get("ground_truth_excerpt") or ""
    can_show = can_highlight(document["english"], translation) or can_highlight(
        document["ground_truth"], ground
    )
    with st.container(border=True):
        head = st.columns([1.1, 1.2, 3.2, 1.15], vertical_alignment="center")
        head[0].markdown(
            f"<span class='chip' style='background:{background};color:{foreground}'>"
            f"{escape(SEVERITY_LABEL.get(item.get('severity'), 'לא צוינה'))}</span>",
            unsafe_allow_html=True,
        )
        head[1].markdown(
            "<span class='chip chip-added'>נוסף ידנית</span>", unsafe_allow_html=True
        )
        head[2].markdown(
            "<p class='finding-title'>ממצא שהוולידטור פספס</p>", unsafe_allow_html=True
        )
        head[3].button(
            "הצג בטקסט",
            key=f"focus-{widget_key(document['id'], finding_id)}",
            disabled=not can_show,
            on_click=focus_finding,
            args=(finding_id,),
            width="stretch",
        )
        quotes = st.columns(2)
        quotes[0].markdown(
            quote_block("תרגום", translation, "tr"), unsafe_allow_html=True
        )
        quotes[1].markdown(
            quote_block("תרגום ייחוס", ground, "gt"), unsafe_allow_html=True
        )
        missing = []
        if translation and not can_highlight(document["english"], translation):
            missing.append("התרגום")
        if ground and not can_highlight(document["ground_truth"], ground):
            missing.append("תרגום הייחוס")
        if missing:
            where = "שני הטקסטים" if len(missing) == 2 else missing[0]
            st.caption(f"הציטוט לא נמצא ב{where}, ולכן אין הדגשה.")
        actions = st.columns([1.2, 4.2], vertical_alignment="center")
        actions[0].button(
            "מחיקה",
            key=f"del-{widget_key(document['id'], finding_id)}",
            on_click=delete_finding_click,
            args=(meta, finding_id),
            width="stretch",
        )
        with actions[1]:
            render_remark(
                state_key,
                item.get("remark") or "",
                save_human_remark,
                (meta, finding_id, state_key),
            )


def render_add_form(document: dict, meta: dict) -> None:
    nonce_key = f"add-nonce-{document['id']}"
    nonce = st.session_state.get(nonce_key, 0)
    with st.expander("הוספת ממצא שהוולידטור פספס"):
        st.caption("העתיקו קטע מדויק מכל טקסט. כך אפשר להדגיש אותו בשלוש החלוניות.")
        with st.form(f"add-{widget_key(document['id'])}-{nonce}", border=False):
            quotes = st.columns(2)
            translation = quotes[0].text_input(
                "ציטוט שגוי מהתרגום",
                placeholder="כפי שמופיע בתרגום",
            )
            ground = quotes[1].text_input(
                "ציטוט נכון מתרגום הייחוס",
                placeholder="כפי שמופיע בתרגום הייחוס",
            )
            extras = st.columns([1, 2])
            severity = extras[0].selectbox(
                "חומרה",
                options=["minor", "major", "critical"],
                index=1,
                format_func=lambda value: SEVERITY_LABEL[value],
            )
            remark = extras[1].text_input(
                "הערה", placeholder="מה השגיאה, ולמה היא חשובה"
            )
            submitted = st.form_submit_button("שמירת הממצא", type="primary")

        if not submitted:
            return
        translation = (translation or "").strip()
        ground = (ground or "").strip()
        remark = (remark or "").strip()
        if not translation or not ground:
            st.warning("צריך למלא את הציטוט מהתרגום ואת הציטוט מתרגום הייחוס.")
            return

        finding_id = data.add_finding(meta, severity, translation, ground, remark)
        st.session_state["focus_id"] = finding_id
        st.session_state["focus_token"] = uuid.uuid4().hex
        st.session_state[nonce_key] = nonce + 1
        missing = []
        if not can_highlight(document["english"], translation):
            missing.append("התרגום")
        if not can_highlight(document["ground_truth"], ground):
            missing.append("תרגום הייחוס")
        if missing:
            where = "שני הטקסטים" if len(missing) == 2 else missing[0]
            st.session_state["flash"] = {
                "kind": "warning",
                "text": f"הממצא נשמר. הציטוט לא נמצא ב{where}, ולכן אין הדגשה.",
            }
        else:
            st.session_state["flash"] = {
                "kind": "success",
                "text": "הממצא נשמר והודגש בטקסט.",
            }
        st.rerun()


def listed_documents(documents: list[dict]) -> list[dict]:
    unit = st.session_state.get("filter_unit", "all")
    model = st.session_state.get("filter_model", "all")
    query = str(st.session_state.get("filter_query") or "").strip()
    visible = [
        document
        for document in documents
        if document_matches(document, unit, model, query)
    ]
    return visible or list(documents)


def render_document_nav(document: dict, documents: list[dict]) -> None:
    visible = listed_documents(documents)
    if document["id"] not in {item["id"] for item in visible}:
        visible = list(documents)
    index = next(i for i, item in enumerate(visible) if item["id"] == document["id"])
    previous_id = visible[index - 1]["id"] if index > 0 else None
    next_id = visible[index + 1]["id"] if index + 1 < len(visible) else None

    nav = st.columns([1.15, 1.15, 1.05, 4.2], vertical_alignment="center")
    nav[0].button(
        "הקודם",
        key="nav-prev",
        icon=":material/chevron_right:",
        width="stretch",
        disabled=previous_id is None,
        on_click=open_document if previous_id else None,
        args=(previous_id,) if previous_id else None,
    )
    nav[1].button(
        "הבא",
        key="nav-next",
        icon=":material/chevron_left:",
        width="stretch",
        disabled=next_id is None,
        on_click=open_document if next_id else None,
        args=(next_id,) if next_id else None,
    )
    nav[2].markdown(
        f"<div class='cell-muted'>{index + 1} מתוך {len(visible)}</div>",
        unsafe_allow_html=True,
    )


def render_detail(document: dict, review: dict, documents: list[dict]) -> None:
    meta = data.review_meta(document)
    view = data.status_view(document, review)
    header = st.columns([4.2, 1.45], vertical_alignment="center")
    with header[0]:
        st.markdown(
            f"<h1 class='doc-title'>{escape(document['label'])}</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p class='doc-meta'>{escape(document['model'])} · {escape(document['date'])}</p>",
            unsafe_allow_html=True,
        )
    header[1].button(
        "חזרה לרשימה",
        key="back-to-list",
        icon=":material/chevron_right:",
        on_click=close_document,
        width="stretch",
    )
    render_document_nav(document, documents)
    counts = Counter(error["severity"] for error in document["errors"])
    added = len(review.get("added") or [])
    chips = [
        f"<span class='chip chip-total'>{len(document['errors'])} ממצאים</span>",
        f"<span class='chip chip-critical'>קריטית {counts.get('critical', 0)}</span>",
        f"<span class='chip chip-major'>גבוהה {counts.get('major', 0)}</span>",
        f"<span class='chip chip-minor'>נמוכה {counts.get('minor', 0)}</span>",
        f"<span class='status status-{view['kind']}'>{escape(view['label'])}</span>",
    ]
    if added:
        chips.append(f"<span class='chip chip-added'>נוספו ידנית {added}</span>")
    st.markdown(
        "<div class='summary'><span class='cell-muted'>סיכום ממצאי המאמת</span>"
        + "".join(chips)
        + "</div>",
        unsafe_allow_html=True,
    )

    render_flash()
    render_panels(document, review)
    st.caption("אשרו אם הוולידטור צדק, ודחו אם הממצא שגוי. ההערה נשמרת ביציאה מהשדה.")

    findings = document["errors"]
    added_items = list(review.get("added") or [])
    total_cards = len(findings) + len(added_items)
    if total_cards == 0:
        st.info("הוולידטור לא דיווח על שגיאות. אם מצאתם שגיאה, הוסיפו אותה למטה.")
    else:
        container_kwargs = (
            {"height": 250, "gap": "small"} if total_cards > 2 else {"gap": "small"}
        )
        with st.container(**container_kwargs):
            for error in findings:
                render_validator_finding(document, review, error, meta)
            if added_items:
                st.markdown("**ממצאים שהוספתם**")
                for item in added_items:
                    render_human_finding(document, review, item, meta)
    render_add_form(document, meta)


def render_sidebar(on_detail: bool) -> None:
    with st.sidebar:
        st.markdown(
            """
            <div class="brand">
              <div class="brand-mark">✓</div>
              <div><strong>בקרת תרגום</strong><span>סקירת תרגומים רפואיים</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.button(
            "סקירת תרגומים",
            key="nav-home",
            type="primary",
            icon=":material/fact_check:",
            width="stretch",
            on_click=close_document if on_detail else None,
        )
        # st.caption("עשרה מסמכי דוגמה. הבחירות נשמרות במחשב זה.")


def render_kpis(documents: list[dict], reviews: dict) -> None:
    counts = data.dashboard_counts(documents, reviews, date.today().isoformat())
    cards = st.columns(3)
    items = [
        (
            "ממצאים פתוחים",
            counts["open_findings"],
            "kpi-red",
            "ממצאי ולידטור שעדיין אין להם אישור או דחייה",
        ),
        (
            "הושלמו היום",
            counts["finished_today"],
            "kpi-teal",
            "מסמכים שכל ממצאי הוולידטור שלהם נשפטו היום",
        ),
        (
            "ממתינים לבדיקה",
            counts["waiting_documents"],
            "kpi-slate",
            "מסמכים עם ממצאים שטרם נשפטו עד הסוף",
        ),
    ]
    for column, (label, value, tone, hint) in zip(cards, items):
        with column:
            st.markdown(
                f'<div class="kpi" title="{escape(hint)}">'
                f'<div class="kpi-label">{label}</div>'
                f'<div class="kpi-value {tone}">{value}</div>'
                "</div>",
                unsafe_allow_html=True,
            )


def render_filters(documents: list[dict]) -> tuple[str, str, str]:
    units = sorted({document["unit"] for document in documents})
    models = sorted({document["model"] for document in documents})
    filters = st.columns([1, 1, 1.6], vertical_alignment="bottom")
    unit = filters[0].selectbox(
        "יחידה",
        options=["all", *units],
        format_func=lambda value: "כל היחידות" if value == "all" else value,
        key="filter_unit",
    )
    model = filters[1].selectbox(
        "מודל",
        options=["all", *models],
        format_func=lambda value: "כל המודלים" if value == "all" else value,
        key="filter_model",
    )
    query = filters[2].text_input(
        "חיפוש",
        placeholder="חיפוש לפי סוג הטקסט, יחידה או מילים מהמקור",
        icon=":material/search:",
        key="filter_query",
    )
    return unit, model, (query or "").strip()


def document_matches(document: dict, unit: str, model: str, query: str) -> bool:
    if unit != "all" and document["unit"] != unit:
        return False
    if model != "all" and document["model"] != model:
        return False
    if not query:
        return True
    haystack = " ".join(
        [
            document["label"],
            document["unit"],
            document["text_type"],
            document["model"],
            document["date"],
            document["hebrew"],
        ]
    )
    return query.casefold() in haystack.casefold()


def render_document_row(document: dict, review: dict) -> None:
    view = data.status_view(document, review)
    background, foreground = SEVERITY_COLOR.get(
        document["severity"], SEVERITY_COLOR[None]
    )
    columns = st.columns(LIST_WIDTHS, vertical_alignment="center")
    columns[0].button(
        document["text_type"],
        key=f"open-{widget_key(document['id'])}",
        type="tertiary",
        width="stretch",
        wrap=True,
        on_click=open_document,
        args=(document["id"],),
    )
    columns[1].button(
        document["unit"],
        key=f"unit-{widget_key(document['id'])}",
        type="tertiary",
        width="stretch",
        wrap=True,
        on_click=open_document,
        args=(document["id"],),
    )
    columns[2].markdown(
        f"<div class='cell'>{escape(document['date'])}</div>", unsafe_allow_html=True
    )
    columns[3].markdown(
        f"<div class='cell'>{escape(document['model'])}</div>", unsafe_allow_html=True
    )
    columns[4].markdown(
        f"<div class='cell-muted'>{document['word_count']}</div>",
        unsafe_allow_html=True,
    )
    columns[5].markdown(
        f"<div class='count-pill' style='background:{background};color:{foreground}'>"
        f"{len(document['errors'])}</div>",
        unsafe_allow_html=True,
    )
    columns[6].markdown(
        f"<span class='status status-{view['kind']}'>{escape(view['label'])}</span>",
        unsafe_allow_html=True,
    )
    st.markdown("<hr class='row-sep'/>", unsafe_allow_html=True)


def render_list(documents: list[dict], reviews: dict) -> None:
    st.markdown(
        """
        <div class="page-head">
          <h1>סקירת תרגומים</h1>
          <p>בדיקת תרגומים רפואיים מעברית לאנגלית</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    render_kpis(documents, reviews)
    unit, model, query = render_filters(documents)
    visible = [
        document
        for document in documents
        if document_matches(document, unit, model, query)
    ]
    st.caption(
        f"מציג {len(visible)} מתוך {len(documents)} · לחצו על סוג הטקסט או על המחלקה כדי לפתוח"
    )

    with st.container(border=True):
        header = st.columns(LIST_WIDTHS, vertical_alignment="center")
        for column, title in zip(
            header,
            ["סוג הטקסט", "מחלקה", "תאריך", "מודל", "מילים", "ממצאים", "סטטוס"],
        ):
            column.markdown(f"<div class='th'>{title}</div>", unsafe_allow_html=True)
        st.markdown("<hr class='row-sep'/>", unsafe_allow_html=True)
        if not visible:
            st.info("אין מסמכים שתואמים לסינון.")
            return
        for document in visible:
            render_document_row(
                document, reviews.get(document["id"]) or data.blank_review()
            )


def main() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)
    if not data.EXCEL_PATH.exists():
        st.error(f"לא נמצא קובץ הנתונים: {data.EXCEL_PATH}")
        st.stop()

    documents = get_documents(data.EXCEL_PATH.stat().st_mtime)
    reviews = data.load_reviews()
    chosen_id = selected_document_id()
    chosen = next(
        (document for document in documents if document["id"] == chosen_id), None
    )
    render_sidebar(chosen is not None)

    if chosen_id and chosen is None:
        st.error("המסמך לא נמצא ברשימה.")
        st.button("חזרה לרשימה", on_click=close_document)
        return
    if chosen is None:
        render_list(documents, reviews)
        return
    render_detail(chosen, reviews.get(chosen["id"]) or data.blank_review(), documents)


main()
