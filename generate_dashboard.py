#!/usr/bin/env python3
"""Build MARVEL_TRL_Dashboard.html from TRL report, scored corpus, DSM, gaps, and optional overlays."""
from __future__ import annotations

import html
import json
import os
from typing import Optional, Tuple

from config.subsystems import MARVEL_SUBSYSTEMS

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(REPO_ROOT, "data", "trl", "MARVEL_TRL_REPORT.json")
OUT_PATH = os.path.join(REPO_ROOT, "MARVEL_TRL_Dashboard.html")
DSM_EDGES_PATH = os.path.join(REPO_ROOT, "config", "marvel_dsm_edges.json")
MATURITY_OVERLAY_PATH = os.path.join(
    REPO_ROOT, "data", "trl", "maturity_dimensions_overlay.json"
)
GAP_REPORT_PATH = os.path.join(
    REPO_ROOT, "data", "gaps", "MARVEL_GAP_REPORT.json"
)
ARCH_TREE_PATH = os.path.join(REPO_ROOT, "config", "marvel_architecture_tree.json")

# Display order + short labels for DSM-lite
SUB_KEYS = list(MARVEL_SUBSYSTEMS.keys())
DSM_LABELS = {
    "heat_transport": "Heat transp.",
    "reactor_core": "Core / fuel",
    "power_conversion": "Power conv.",
    "control_systems": "I&C",
    "safety_systems": "Safety",
    "grid_integration": "Grid / load",
}

def load_dsm_state() -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], str]]:
    """
    Build symmetric coupling matrix + type hint per cell from config/marvel_dsm_edges.json.
    Falls back to legacy S/M/W pairs if file is missing.
    """
    cells: dict[tuple[str, str], str] = {}
    types: dict[tuple[str, str], str] = {}
    for a in SUB_KEYS:
        cells[(a, a)] = "—"
        types[(a, a)] = ""

    edges_data: list = []
    if os.path.isfile(DSM_EDGES_PATH):
        with open(DSM_EDGES_PATH, encoding="utf-8") as f:
            edges_data = json.load(f).get("edges") or []
    if not edges_data:
        # legacy fallback (coupling only)
        legacy = [
            ("heat_transport", "reactor_core", "S"),
            ("heat_transport", "power_conversion", "S"),
            ("heat_transport", "safety_systems", "S"),
            ("reactor_core", "safety_systems", "S"),
            ("reactor_core", "control_systems", "M"),
            ("power_conversion", "grid_integration", "S"),
            ("power_conversion", "control_systems", "M"),
            ("control_systems", "safety_systems", "S"),
            ("control_systems", "grid_integration", "M"),
            ("safety_systems", "grid_integration", "W"),
            ("reactor_core", "power_conversion", "M"),
            ("heat_transport", "control_systems", "M"),
            ("reactor_core", "grid_integration", "W"),
            ("heat_transport", "grid_integration", "W"),
            ("safety_systems", "power_conversion", "M"),
        ]
        for x, y, c in legacy:
            cells[(x, y)] = c
            cells[(y, x)] = c

    for e in edges_data:
        x = e.get("from")
        y = e.get("to")
        if x not in SUB_KEYS or y not in SUB_KEYS or x == y:
            continue
        c = str(e.get("coupling", "M")).upper()[:1]
        if c not in ("S", "M", "W"):
            c = "M"
        tlist = e.get("types") or []
        type_str = ", ".join(str(t) for t in tlist) if tlist else ""
        cells[(x, y)] = c
        cells[(y, x)] = c
        types[(x, y)] = type_str
        types[(y, x)] = type_str

    for i, ri in enumerate(SUB_KEYS):
        for j, cj in enumerate(SUB_KEYS):
            if (ri, cj) not in cells:
                cells[(ri, cj)] = "W" if i != j else "—"
            if (ri, cj) not in types:
                types[(ri, cj)] = ""
    return cells, types


def load_maturity_overlay() -> dict:
    if not os.path.isfile(MATURITY_OVERLAY_PATH):
        return {}
    with open(MATURITY_OVERLAY_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def load_gap_report() -> Optional[dict]:
    if not os.path.isfile(GAP_REPORT_PATH):
        return None
    with open(GAP_REPORT_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_architecture_tree() -> Optional[dict]:
    if not os.path.isfile(ARCH_TREE_PATH):
        return None
    with open(ARCH_TREE_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_critical_dsm_rollup_html() -> str:
    """Roll-up lines for DSM edges marked critical."""
    if not os.path.isfile(DSM_EDGES_PATH):
        return ""
    try:
        with open(DSM_EDGES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return ""
    edges = data.get("edges") or []
    seen: set[tuple[str, str]] = set()
    phrases: list[str] = []
    for e in edges:
        if not e.get("critical"):
            continue
        x, y = e.get("from"), e.get("to")
        if x not in SUB_KEYS or y not in SUB_KEYS or x == y:
            continue
        pair = tuple(sorted([str(x), str(y)]))
        if pair in seen:
            continue
        seen.add(pair)
        nx = MARVEL_SUBSYSTEMS[x]["name"]
        ny = MARVEL_SUBSYSTEMS[y]["name"]
        types = ", ".join(str(t) for t in (e.get("types") or []))
        note = (e.get("note") or "").strip()
        bit = f"{html.escape(nx)} ↔ {html.escape(ny)}"
        if types:
            bit += f" ({html.escape(types)})"
        if note:
            bit += f" — {html.escape(note[:100])}{'…' if len(note) > 100 else ''}"
        phrases.append(bit)
    if not phrases:
        return ""
    return (
        '<p class="rollup-critical"><strong>Critical couplings</strong> · '
        f"{'; '.join(phrases)}</p>"
    )


def build_architecture_section_html(tree: Optional[dict]) -> str:
    """Ontology / decomposition preview (layer 1)."""
    if not tree or not isinstance(tree.get("subsystems"), dict):
        return (
            '<section class="arch-section" id="architecture" aria-label="Architecture">'
            "<h2>Architecture</h2>"
            '<p class="arch-note">No decomposition data.</p>'
            "</section>"
        )
    subs = tree["subsystems"]
    blocks: list[str] = []
    for key in SUB_KEYS:
        name = MARVEL_SUBSYSTEMS[key]["name"]
        items = subs.get(key)
        if not items:
            lis = "<li class='arch-empty'><em>—</em></li>"
        else:
            lis = "".join(f"<li>{html.escape(str(c))}</li>" for c in items)
        blocks.append(
            '<div class="arch-block" '
            f'id="arch-{html.escape(key)}">'
            f'<h3 class="arch-heading"><a href="#card-{html.escape(key)}">'
            f"{html.escape(name)}</a></h3>"
            f"<ul class='arch-list'>{lis}</ul></div>"
        )
    return (
        '<section class="arch-section" id="architecture" aria-label="Architecture">'
        "<h2>Architecture</h2>"
        '<p class="arch-note">Subsystem → components · headings link to TRL cards</p>'
        f'<div class="arch-grid">{"".join(blocks)}</div>'
        "</section>"
    )


def build_gap_section_html(gap_report: Optional[dict]) -> str:
    """Evidence gap analysis section (proposal GAP ANALYZER)."""
    if not gap_report:
        return (
            '<section class="gap-section" id="gaps" aria-label="Gap analysis">'
            "<h2>Gap analysis</h2>"
            '<p class="gap-note">No gap data.</p>'
            "</section>"
        )

    summary = gap_report.get("summary") or {}
    subs = gap_report.get("subsystems") or {}
    framing = html.escape(str(summary.get("framing", "")))
    peer = gap_report.get("peer_median_document_count", "")
    hg = summary.get("highest_gap_pressure_subsystems") or []
    hg_line = " · ".join(
        html.escape(str(subs.get(k, {}).get("name", k))) for k in hg if subs.get(k)
    )

    rows: list[str] = []
    for key in SUB_KEYS:
        s = subs.get(key, {})
        name = html.escape(str(s.get("name", key)))
        cov = html.escape(str(s.get("coverage_label", "—")))
        idx = int(s.get("gap_index", 0))
        m = s.get("metrics") or {}
        m_docs = m.get("total_documents", "—")
        m_hq = m.get("high_quality_ratio", "—")
        g_lang = m.get("gap_language_doc_fraction", "—")
        sim_f = m.get("simulation_heavy_doc_fraction", "—")
        c = m.get("top5_contrast") or {}
        c_hi = c.get("higher_quality_score")
        c_lo = c.get("lower_quality_score")
        if c_hi is not None and c_lo is not None:
            c_txt = f"{c_hi:.3f}→{c_lo:.3f}"
        else:
            c_txt = "—"
        sigs = s.get("signals") or []
        sig0 = (
            html.escape(sigs[0][:160] + ("…" if len(sigs[0]) > 160 else ""))
            if sigs
            else "—"
        )
        rows.append(
            "<tr>"
            f"<td>{name}</td><td>{cov}</td><td>{idx}</td><td>{m_docs}</td>"
            f"<td>{m_hq}</td><td>{g_lang}</td><td>{sim_f}</td><td>{c_txt}</td><td>{sig0}</td>"
            "</tr>"
        )

    detail_chunks: list[str] = []
    for key in SUB_KEYS:
        s = subs.get(key, {})
        nm = str(s.get("name", key))
        sigs = s.get("signals") or []
        lis = "".join(f"<li>{html.escape(t)}</li>" for t in sigs)
        ft = s.get("from_trl_report") or {}
        lim = (ft.get("limiting_factor") or "").strip()
        nxt = (ft.get("next_step") or "").strip()
        m = s.get("metrics") or {}
        c = m.get("top5_contrast") or {}
        chi = c.get("higher_quality_title")
        clo = c.get("lower_quality_title")
        extra = ""
        if chi and clo:
            extra += (
                '<p class="gap-trl-ref"><strong>Top-5 contrast:</strong> '
                f"«{html.escape(str(chi)[:180])}» vs «{html.escape(str(clo)[:180])}»</p>"
            )
        if lim:
            extra += (
                '<p class="gap-trl-ref"><strong>LIMIT:</strong> '
                f"{html.escape(lim[:450])}{'…' if len(lim) > 450 else ''}</p>"
            )
        if nxt:
            extra += (
                '<p class="gap-trl-ref"><strong>NEXT:</strong> '
                f"{html.escape(nxt[:450])}{'…' if len(nxt) > 450 else ''}</p>"
            )
        detail_chunks.append(
            '<details class="gap-details">'
            f"<summary>{html.escape(nm)} — signals</summary>"
            f"<ul class='gap-signal-list'>{lis}</ul>{extra}"
            "</details>"
        )

    peer_bits: list[str] = []
    if peer != "" and peer is not None:
        peer_bits.append(
            f'Peer median (docs): <strong>{html.escape(str(peer))}</strong>'
        )
    if framing:
        peer_bits.append(framing)
    gap_intro = ""
    if peer_bits:
        gap_intro = (
            '<p class="gap-note">' + " · ".join(peer_bits) + "</p>"
        )

    return (
        '<section class="gap-section" id="gaps" aria-label="Gap analysis">'
        "<h2>Gap analysis</h2>"
        + gap_intro
        + (
            f'<p class="gap-highlight"><strong>Gap pressure:</strong> {hg_line}</p>'
            if hg_line
            else ""
        )
        + '<div class="gap-table-wrap"><table class="gap-table">'
        "<thead><tr>"
        "<th>Subsystem</th><th>Coverage</th><th>Gap idx</th><th>Docs</th>"
        "<th>HQ ratio</th><th>Gap lang</th><th>Sim-heavy</th><th>Contrast</th><th>Primary signal</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        + '<div class="gap-expandable">'
        + "".join(detail_chunks)
        + "</div>"
        "</section>"
    )


def parse_trl_range(s: str) -> tuple[int, int]:
    s = (s or "").strip().replace("–", "-")
    if "-" in s:
        a, b = s.split("-", 1)
        return int(a.strip()), int(b.strip())
    n = int(s)
    return n, n


def trl_bar_percent(lo: int, hi: int) -> int:
    mid = (lo + hi) / 2.0
    return max(5, min(100, round(mid / 9.0 * 100)))


def trl_badge_class(lo: int, hi: int) -> str:
    if hi <= 4:
        return "trl-34"
    if lo >= 7:
        return "trl-78"
    return "trl-56"


def trl_bar_gradient_class(lo: int, hi: int) -> str:
    if hi <= 4:
        return "bar-orange"
    if lo >= 7:
        return "bar-green"
    return "bar-yellow"


def confidence_pill_class(conf: str) -> str:
    c = (conf or "").upper().strip()
    return {
        "HIGH": "conf-high",
        "MEDIUM": "conf-medium",
        "LOW": "conf-low",
    }.get(c, "conf-unknown")


def normalize_title(t: str) -> str:
    s = (t or "").strip().lower().replace("?", " ").replace("…", " ")
    return " ".join(s.split())


def resolve_evidence_link(evidence_title: str, docs: list) -> tuple[str, str]:
    """
    Match inferencer evidence line to a scored document; return (url, source).
    URL prefers `url`, then `doi_url`.
    """
    if not docs:
        return "", ""
    nt = normalize_title(evidence_title)
    for d in docs:
        if normalize_title(d.get("title") or "") == nt:
            u = (d.get("url") or "").strip() or (d.get("doi_url") or "").strip()
            return u, str(d.get("source") or "")

    candidates = []
    for d in docs:
        dtitle = d.get("title") or ""
        dtn = normalize_title(dtitle)
        if not dtn or not nt:
            continue
        if nt in dtn or dtn in nt:
            if min(len(nt), len(dtn)) >= 14:
                candidates.append(d)
    if len(candidates) == 1:
        d = candidates[0]
        u = (d.get("url") or "").strip() or (d.get("doi_url") or "").strip()
        return u, str(d.get("source") or "")
    return "", ""


def load_scored_summary(key: str) -> dict:
    path = os.path.join(REPO_ROOT, "data", "scored", f"{key}_scored.json")
    if not os.path.isfile(path):
        return {
            "total_documents": 0,
            "high_quality": 0,
            "osti": 0,
            "arxiv": 0,
            "documents": [],
        }
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    summary = data.get("scoring_summary") or {}
    docs = data.get("scored_documents") or []
    osti = sum(1 for d in docs if str(d.get("source", "")).upper() == "OSTI")
    arxiv = sum(1 for d in docs if "arxiv" in str(d.get("source", "")).lower())
    return {
        "total_documents": int(summary.get("total_documents", len(docs))),
        "high_quality": int(summary.get("high_quality", 0)),
        "osti": osti,
        "arxiv": arxiv,
        "documents": docs,
    }


def safe_parse_trl_range(s: str) -> Optional[Tuple[int, int]]:
    try:
        return parse_trl_range(str(s))
    except ValueError:
        return None


def format_trl_display(lo: int, hi: int) -> str:
    if lo == hi:
        return str(lo)
    return f"{lo}–{hi}"


def build_dsm_table(
    dsm_cells: dict[tuple[str, str], str],
    dsm_types: dict[tuple[str, str], str],
) -> str:
    headers = "".join(
        f'<th scope="col">{html.escape(DSM_LABELS[k])}</th>' for k in SUB_KEYS
    )
    rows = []
    for ri in SUB_KEYS:
        row_cells = [f'<th scope="row">{html.escape(DSM_LABELS[ri])}</th>']
        for cj in SUB_KEYS:
            v = dsm_cells.get((ri, cj), "—")
            th = (dsm_types.get((ri, cj)) or "").strip()
            if ri == cj:
                inner = html.escape(v)
            elif th:
                title_attr = html.escape(th, quote=True)
                inner = (
                    f'<span class="dsm-coupling">{html.escape(v)}</span>'
                    f'<span class="dsm-types" title="{title_attr}">'
                    f"{html.escape(th)}</span>"
                )
            else:
                inner = f'<span class="dsm-coupling">{html.escape(v)}</span>'
            row_cells.append(f"<td>{inner}</td>")
        rows.append("<tr>" + "".join(row_cells) + "</tr>")
    return (
        '<table class="dsm-table" aria-label="Subsystem coupling (typed DSM)">'
        f"<thead><tr><th></th>{headers}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_maturity_dimensions_block(key: str, overlay: dict) -> str:
    m = overlay.get(key)
    if not m or not isinstance(m, dict):
        return ""
    labels = (
        ("regulatory_readiness", "Regulatory"),
        ("manufacturing_readiness", "Manufacturing"),
        ("integration_readiness", "Integration"),
    )
    rows = []
    for field, label in labels:
        val = (m.get(field) or "").strip()
        if val:
            rows.append(
                '<div class="detail-row">'
                f'<div class="detail-key">{html.escape(label)}</div>'
                f'<div class="detail-val">{html.escape(val)}</div>'
                "</div>"
            )
    if not rows:
        return ""
    return (
        '<div class="maturity-dims">'
        '<div class="maturity-kicker">RRL / MRL / IRL (overlay)</div>'
        + "".join(rows)
        + "</div>"
    )


def render_card(
    key: str,
    entry: dict,
    scored: dict,
    index: int,
    maturity_overlay: Optional[dict] = None,
) -> str:
    docs = scored.get("documents") or []
    trl_raw = entry.get("trl_range", "?")
    try:
        lo, hi = parse_trl_range(str(trl_raw))
    except ValueError:
        lo, hi = 0, 0
    badge = trl_badge_class(lo, hi)
    bar_pct = trl_bar_percent(lo, hi)
    bar_cls = trl_bar_gradient_class(lo, hi)
    conf = confidence_pill_class(entry.get("confidence", ""))
    title = entry.get("subsystem") or MARVEL_SUBSYSTEMS[key]["name"]
    summary = entry.get("summary") or ""
    key_ev = entry.get("key_evidence") or ""
    lim = entry.get("limiting_factor") or ""
    nxt = (entry.get("next_step") or "").strip()
    evidence_used = entry.get("evidence_used") or []
    top_scores = entry.get("top_doc_scores") or []

    ev_rows = []
    for i, title_doc in enumerate(evidence_used):
        score = top_scores[i] if i < len(top_scores) else None
        score_s = f"{score:.3f}" if isinstance(score, (int, float)) else "—"
        link_url, src = resolve_evidence_link(str(title_doc), docs)
        title_esc = html.escape(str(title_doc))
        if link_url:
            title_html = (
                f'<a class="ev-link" href="{html.escape(link_url, quote=True)}" '
                'target="_blank" rel="noopener noreferrer">'
                f"{title_esc}</a>"
            )
            src_bit = (
                f' <span class="ev-src">{html.escape(src)}</span>'
                if src
                else ""
            )
        else:
            title_html = f'<span class="ev-title">{title_esc}</span>'
            src_bit = ""
        ev_rows.append(
            "<li>"
            f"{title_html}{src_bit}"
            f' <span class="ev-score">· relevance {html.escape(score_s)}</span>'
            "</li>"
        )
    evidence_block = (
        "<ul class='evidence-list'>" + "".join(ev_rows) + "</ul>"
        if ev_rows
        else "<p class='muted-small'>—</p>"
    )

    next_row = ""
    if nxt:
        next_row = (
            "<div class='detail-row'><div class='detail-key'>NEXT</div>"
            f"<div class='detail-val'>{html.escape(nxt)}</div></div>"
        )

    key_row = ""
    if key_ev:
        key_row = (
            "<div class='detail-row'><div class='detail-key'>KEY</div>"
            f"<div class='detail-val'>{html.escape(key_ev)}</div></div>"
        )

    delay = 0.1 * (index + 1)
    card_id = f"card-{key}"
    maturity_html = render_maturity_dimensions_block(key, maturity_overlay or {})

    return f"""
    <div class="subsystem-card" id="{card_id}" style="animation-delay: {delay:.1f}s">
      <div class="card-header">
        <div class="card-title">{html.escape(title)}</div>
        <div class="trl-badge {badge}">{html.escape(format_trl_display(lo, hi))}</div>
      </div>
      <div class="trl-bar-track"><div class="trl-bar-fill {bar_cls}" style="width:{bar_pct}%"></div></div>
      <div class="trl-bar-labels"><span>TRL 1</span><span>TRL 3</span><span>TRL 5</span><span>TRL 7</span><span>TRL 9</span></div>
      <div class="confidence-row">
        <div class="conf-label">Confidence</div>
        <div class="conf-pill {conf}">{html.escape((entry.get("confidence") or "—").upper())}</div>
      </div>
      {maturity_html}
      <div class="card-summary">{html.escape(summary)}</div>
      {key_row}
      <div class="detail-row"><div class="detail-key">LIMIT</div><div class="detail-val">{html.escape(lim)}</div></div>
      {next_row}
      <div class="evidence-count">
        <div class="ev-item"><span>{scored["osti"]}</span>OSTI</div>
        <div class="ev-item"><span>{scored["arxiv"]}</span>arXiv</div>
        <div class="ev-item"><span>{scored["high_quality"]}</span>HIGH Q</div>
      </div>
      <details class="evidence-details">
        <summary>Sources (ranked)</summary>
        {evidence_block}
      </details>
    </div>
    """


def main() -> None:
    with open(REPORT_PATH, encoding="utf-8") as f:
        report: dict = json.load(f)

    scored_by_key = {k: load_scored_summary(k) for k in SUB_KEYS}
    total_docs = sum(scored_by_key[k]["total_documents"] for k in SUB_KEYS)
    total_hq = sum(scored_by_key[k]["high_quality"] for k in SUB_KEYS)

    report_parse_errors = [
        k
        for k in SUB_KEYS
        if k in report and safe_parse_trl_range(report[k].get("trl_range", "")) is None
    ]

    # TRL roll-up: conservative min of lower bounds (subsystems with valid TRL only)
    lows = []
    for k in SUB_KEYS:
        if k not in report:
            continue
        parsed = safe_parse_trl_range(report[k].get("trl_range", ""))
        if parsed is None:
            continue
        lo, hi = parsed
        lows.append((lo, k, hi))

    if lows:
        min_lo, bneck_key, bneck_hi = min(lows, key=lambda x: x[0])
        bneck_name = report.get(bneck_key, {}).get(
            "subsystem", MARVEL_SUBSYSTEMS[bneck_key]["name"]
        )
        at_floor = [
            report[k].get("subsystem", MARVEL_SUBSYSTEMS[k]["name"])
            for lo, k, _hi in lows
            if lo == min_lo
        ]
    else:
        min_lo, bneck_key, bneck_hi = 0, SUB_KEYS[0], 0
        bneck_name = "—"
        at_floor = []

    mids = []
    for k in SUB_KEYS:
        if k not in report:
            continue
        parsed = safe_parse_trl_range(report[k].get("trl_range", ""))
        if parsed is None:
            continue
        lo, hi = parsed
        mids.append((lo + hi) / 2)
    avg_mid = sum(mids) / max(1, len(mids))

    if report_parse_errors:
        err_names = " · ".join(
            MARVEL_SUBSYSTEMS[k]["name"] for k in report_parse_errors
        )
        health_html = (
            '<div class="report-health" role="alert">'
            "<strong>TRL parse issue:</strong> "
            f"{html.escape(err_names)}"
            "</div>"
        )
    else:
        health_html = ""

    floor_line = ""
    if at_floor:
        floor_line = (
            '<p class="rollup-floor"><strong>At floor:</strong> '
            f"{html.escape(' · '.join(at_floor))}</p>"
        )

    maturity_overlay = load_maturity_overlay()
    dsm_cells, dsm_types = load_dsm_state()

    cards_html = ""
    for i, k in enumerate(SUB_KEYS):
        if k not in report:
            continue
        cards_html += render_card(
            k, report[k], scored_by_key[k], i, maturity_overlay
        )

    dsm_html = build_dsm_table(dsm_cells, dsm_types)
    arch_html = build_architecture_section_html(load_architecture_tree())
    gap_html = build_gap_section_html(load_gap_report())
    critical_dsm_html = build_critical_dsm_rollup_html()

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MARVEL Microreactor — TRL Assessment Dashboard</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Barlow:wght@300;400;600;700&family=Barlow+Condensed:wght@700;900&display=swap');

  :root {{
    --bg: #050a0f;
    --panel: #0a1520;
    --border: #1a3a5c;
    --accent: #00d4ff;
    --green: #00ff88;
    --yellow: #ffd700;
    --orange: #ff6b35;
    --text: #c8e6f5;
    --muted: #4a7a9b;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Barlow', sans-serif;
    min-height: 100vh;
  }}

  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,212,255,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,255,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
  }}

  .wrapper {{ position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; padding: 40px 24px; }}

  .top-nav {{
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px 18px;
    margin: -8px -24px 22px -24px;
    padding: 14px 24px 16px 24px;
    border-bottom: 1px solid var(--border);
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 2px;
    background: rgba(5, 10, 15, 0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
  }}
  .top-nav a {{
    color: var(--accent);
    text-decoration: none;
    text-transform: uppercase;
  }}
  .top-nav a:hover {{ color: #fff; text-decoration: underline; text-underline-offset: 3px; }}

  .report-health {{
    background: rgba(255,107,53,0.1);
    border: 1px solid var(--orange);
    border-left-width: 4px;
    padding: 14px 18px;
    margin-bottom: 24px;
    font-size: 12px;
    line-height: 1.5;
    color: var(--text);
  }}
  .report-health strong {{ color: #fff; }}

  #rollup, #dsm, #architecture, #stats, #gaps, #subsystems {{ scroll-margin-top: 16px; }}

  .header {{ border-left: 4px solid var(--accent); padding-left: 24px; margin-bottom: 32px; }}
  .header-label {{ font-family: 'Share Tech Mono', monospace; font-size: 11px; letter-spacing: 4px; color: var(--accent); text-transform: uppercase; margin-bottom: 8px; }}
  .header h1 {{ font-family: 'Barlow Condensed', sans-serif; font-size: clamp(32px, 5vw, 52px); font-weight: 900; color: #fff; line-height: 1; margin-bottom: 6px; }}
  .header h1 span {{ color: var(--accent); }}
  .header-sub {{ font-size: 13px; color: var(--muted); letter-spacing: 1px; }}

  .rollup-banner {{
    background: linear-gradient(90deg, rgba(0,212,255,0.12), rgba(0,212,255,0.02));
    border: 1px solid var(--border);
    border-left: 4px solid var(--accent);
    padding: 16px 20px;
    margin-bottom: 24px;
    font-size: 13px;
    line-height: 1.55;
  }}
  .rollup-banner strong {{ color: #fff; }}
  .rollup-banner .rollup-kicker {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 8px;
  }}
  .rollup-banner .rollup-floor {{
    margin-top: 10px;
    font-size: 12px;
    color: var(--muted);
  }}
  .rollup-banner .rollup-floor strong {{ color: var(--text); }}
  .rollup-banner .rollup-critical {{
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--border);
    font-size: 12px;
    color: var(--muted);
    line-height: 1.5;
  }}
  .rollup-banner .rollup-critical strong {{ color: var(--yellow); }}

  .dsm-section {{
    margin-bottom: 32px;
  }}
  .arch-section {{
    margin-bottom: 36px;
  }}
  .arch-section h2 {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--yellow);
    text-transform: uppercase;
    margin-bottom: 10px;
    font-weight: 400;
  }}
  .arch-note {{
    font-size: 11px;
    color: var(--muted);
    margin-bottom: 16px;
    max-width: 820px;
    line-height: 1.5;
  }}
  .arch-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }}
  @media (max-width: 768px) {{
    .arch-grid {{ grid-template-columns: 1fr; }}
  }}
  .arch-block {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 16px 18px;
    border-top: 3px solid var(--yellow);
  }}
  .arch-heading {{
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 10px;
  }}
  .arch-heading a {{
    color: #fff;
    text-decoration: none;
  }}
  .arch-heading a:hover {{ color: var(--accent); }}
  .arch-list {{
    margin: 0;
    padding-left: 18px;
    font-size: 11px;
    color: var(--text);
    line-height: 1.55;
  }}
  .arch-list li {{ margin-bottom: 6px; }}
  .arch-empty {{ color: var(--muted); list-style: none; margin-left: -18px; }}

  .dsm-section h2 {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--accent);
    text-transform: uppercase;
    margin-bottom: 10px;
    font-weight: 400;
  }}
  .dsm-note {{ font-size: 11px; color: var(--muted); margin-bottom: 12px; max-width: 720px; line-height: 1.5; }}
  .dsm-legend {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; color: var(--muted); margin-bottom: 10px; }}
  .dsm-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
    background: var(--panel);
    border: 1px solid var(--border);
  }}
  .dsm-table th, .dsm-table td {{
    border: 1px solid var(--border);
    padding: 8px 6px;
    text-align: center;
  }}
  .dsm-table th {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px;
    color: var(--accent);
    font-weight: 400;
  }}
  .dsm-table th[scope="row"] {{
    text-align: right;
    padding-right: 10px;
    white-space: nowrap;
  }}
  .dsm-table td {{
    vertical-align: middle;
    line-height: 1.35;
  }}
  .dsm-coupling {{
    font-family: 'Share Tech Mono', monospace;
    font-weight: 700;
    font-size: 12px;
    display: block;
  }}
  .dsm-types {{
    display: block;
    font-size: 8px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 4px;
    word-break: break-word;
  }}

  .maturity-dims {{
    margin-bottom: 14px;
    padding: 12px 12px 2px 12px;
    background: rgba(0,212,255,0.04);
    border: 1px solid var(--border);
    border-left: 3px solid var(--green);
  }}
  .maturity-kicker {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px;
    letter-spacing: 2px;
    color: var(--green);
    text-transform: uppercase;
    margin-bottom: 10px;
  }}

  .gap-section {{
    margin-bottom: 40px;
  }}
  .gap-section h2 {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 3px;
    color: var(--orange);
    text-transform: uppercase;
    margin-bottom: 12px;
    font-weight: 400;
  }}
  .gap-note, .gap-highlight {{
    font-size: 12px;
    line-height: 1.55;
    color: var(--muted);
    margin-bottom: 12px;
    max-width: 900px;
  }}
  .gap-highlight {{
    color: var(--text);
    border-left: 3px solid var(--orange);
    padding-left: 12px;
  }}
  .gap-highlight strong {{ color: #fff; }}
  .gap-table-wrap {{
    overflow-x: auto;
    margin-bottom: 20px;
    border: 1px solid var(--border);
    background: var(--panel);
  }}
  .gap-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11px;
  }}
  .gap-table th, .gap-table td {{
    border: 1px solid var(--border);
    padding: 10px 8px;
    text-align: left;
    vertical-align: top;
  }}
  .gap-table th {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px;
    color: var(--orange);
    letter-spacing: 1px;
    text-transform: uppercase;
    white-space: nowrap;
  }}
  .gap-table td:nth-child(3), .gap-table td:nth-child(4) {{
    font-family: 'Share Tech Mono', monospace;
    color: var(--accent);
  }}
  .gap-expandable {{
    display: grid;
    gap: 10px;
  }}
  .gap-details {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 10px 14px;
  }}
  .gap-details summary {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    color: var(--accent);
    cursor: pointer;
  }}
  .gap-signal-list {{
    margin: 12px 0 0 18px;
    font-size: 11px;
    color: var(--text);
    line-height: 1.5;
  }}
  .gap-signal-list li {{ margin-bottom: 6px; }}
  .gap-trl-ref {{
    font-size: 11px;
    color: var(--muted);
    margin-top: 10px;
    line-height: 1.45;
  }}
  .gap-trl-ref strong {{ color: var(--accent); }}

  .stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 40px; }}
  .stat-card {{ background: var(--panel); border: 1px solid var(--border); padding: 20px; position: relative; }}
  .stat-card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px; background: var(--accent); }}
  .stat-value {{ font-family: 'Share Tech Mono', monospace; font-size: 30px; color: var(--accent); }}
  .stat-label {{ font-size: 10px; letter-spacing: 2px; color: var(--muted); text-transform: uppercase; margin-top: 4px; }}

  .subsystems-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 40px; }}

  .subsystem-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 24px;
    transition: border-color 0.3s, transform 0.3s;
  }}
  .subsystem-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}

  .card-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 16px; }}
  .card-title {{ font-family: 'Barlow Condensed', sans-serif; font-size: 15px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase; color: #fff; max-width: 65%; line-height: 1.2; }}

  .trl-badge {{ font-family: 'Share Tech Mono', monospace; font-size: 20px; font-weight: 700; padding: 6px 12px; border: 2px solid; line-height: 1; }}
  .trl-56  {{ color: var(--yellow); border-color: var(--yellow); background: rgba(255,215,0,0.08); }}
  .trl-78  {{ color: var(--green);  border-color: var(--green);  background: rgba(0,255,136,0.08); }}
  .trl-34  {{ color: var(--orange); border-color: var(--orange); background: rgba(255,107,53,0.08); }}
  .trl-err {{ color: var(--muted);  border-color: var(--muted);  background: rgba(74,122,155,0.08); }}

  .trl-bar-track {{ height: 5px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden; margin-bottom: 4px; }}
  .trl-bar-fill {{ height: 100%; border-radius: 3px; width: 0; transition: width 1.4s cubic-bezier(0.4,0,0.2,1); }}
  .bar-yellow {{ background: linear-gradient(90deg, var(--yellow), #ffaa00); }}
  .bar-green  {{ background: linear-gradient(90deg, var(--green), #00cc66); }}
  .bar-orange {{ background: linear-gradient(90deg, var(--orange), #ff4400); }}
  .trl-bar-labels {{ display: flex; justify-content: space-between; font-family: 'Share Tech Mono', monospace; font-size: 9px; color: var(--muted); margin-bottom: 14px; }}

  .confidence-row {{ display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }}
  .conf-label {{ font-size: 10px; letter-spacing: 2px; color: var(--muted); text-transform: uppercase; }}
  .conf-pill {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; padding: 2px 8px; border-radius: 2px; }}
  .conf-medium  {{ background: rgba(255,215,0,0.15);  color: var(--yellow); }}
  .conf-high    {{ background: rgba(0,255,136,0.15);  color: var(--green); }}
  .conf-low     {{ background: rgba(255,107,53,0.15); color: var(--orange); }}
  .conf-unknown {{ background: rgba(74,122,155,0.15); color: var(--muted); }}

  .card-summary {{ font-size: 12px; color: var(--muted); line-height: 1.6; margin-bottom: 12px; border-left: 2px solid var(--border); padding-left: 10px; }}

  .detail-row {{ display: flex; gap: 8px; margin-bottom: 6px; font-size: 11px; }}
  .detail-key {{ font-family: 'Share Tech Mono', monospace; color: var(--accent); min-width: 75px; flex-shrink: 0; font-size: 10px; }}
  .detail-val {{ color: var(--text); line-height: 1.4; }}

  .evidence-count {{ margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--border); display: flex; gap: 20px; flex-wrap: wrap; }}
  .ev-item {{ font-family: 'Share Tech Mono', monospace; font-size: 10px; color: var(--muted); }}
  .ev-item span {{ color: var(--accent); font-size: 14px; display: block; }}

  .evidence-details {{
    margin-top: 14px;
    border-top: 1px solid var(--border);
    padding-top: 10px;
  }}
  .evidence-details summary {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 10px;
    letter-spacing: 1px;
    color: var(--accent);
    cursor: pointer;
    user-select: none;
  }}
  .evidence-details summary:hover {{ color: #fff; }}
  .evidence-list {{
    margin: 12px 0 0 0;
    padding-left: 18px;
    font-size: 11px;
    color: var(--text);
    line-height: 1.5;
  }}
  .evidence-list li {{ margin-bottom: 8px; }}
  .ev-title {{ color: var(--text); }}
  a.ev-link {{ color: var(--accent); text-decoration: underline; text-underline-offset: 3px; }}
  a.ev-link:hover {{ color: #fff; }}
  .ev-src {{ font-family: 'Share Tech Mono', monospace; font-size: 9px; color: var(--muted); margin-left: 4px; }}
  .ev-score {{ font-family: 'Share Tech Mono', monospace; font-size: 9px; color: var(--muted); }}
  .muted-small {{ font-size: 11px; color: var(--muted); margin-top: 8px; }}

  .footer {{
    margin-top: 48px;
    padding: 28px 0 36px;
    border-top: 1px solid var(--border);
    background: linear-gradient(180deg, transparent, rgba(0,212,255,0.04));
  }}
  .footer-inner {{
    max-width: 720px;
    margin: 0 auto;
    text-align: center;
  }}
  .footer-brand {{ margin-bottom: 16px; }}
  .footer-title {{
    display: block;
    font-family: 'Barlow Condensed', sans-serif;
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    color: #fff;
    margin-bottom: 6px;
  }}
  .footer-team {{
    display: block;
    font-size: 12px;
    color: var(--muted);
    line-height: 1.45;
  }}
  .footer-sources {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    align-items: center;
    gap: 8px 10px;
  }}
  .footer-pill {{
    font-family: 'Share Tech Mono', monospace;
    font-size: 9px;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: var(--accent);
    border: 1px solid var(--border);
    background: rgba(10, 21, 32, 0.85);
    padding: 6px 12px;
    border-radius: 2px;
  }}

  @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(16px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  .subsystem-card {{ animation: fadeIn 0.5s ease both; }}

  @media (max-width: 768px) {{
    .subsystems-grid {{ grid-template-columns: 1fr; }}
    .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
    .dsm-table {{ font-size: 10px; }}
    .dsm-table th, .dsm-table td {{ padding: 6px 4px; }}
    .top-nav {{
      margin-left: -16px;
      margin-right: -16px;
      padding-left: 16px;
      padding-right: 16px;
    }}
  }}

  @media print {{
    body {{ background: #fff !important; color: #1a1a1a; }}
    body::before {{ display: none !important; }}
    .wrapper {{ max-width: none; padding: 16px; }}
    .top-nav {{
      position: static;
      background: #fff;
      backdrop-filter: none;
      border-bottom: 1px solid #999;
      margin: 0 0 16px 0;
      padding: 8px 0;
    }}
    .top-nav a {{ color: #0b5d8a; }}
    .header, .rollup-banner, .dsm-table, .arch-block,
    .stat-card, .subsystem-card, .gap-table-wrap, .gap-details, .footer {{
      background: #f9f9f9 !important;
      border-color: #bbb !important;
      box-shadow: none !important;
    }}
    .subsystem-card {{ break-inside: avoid; page-break-inside: avoid; animation: none !important; }}
    .subsystem-card:hover {{ transform: none !important; }}
    .trl-bar-fill {{ transition: none !important; }}
    * {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  }}
</style>
</head>
<body>
<div class="wrapper">

  <nav class="top-nav" aria-label="Sections">
    <a href="#rollup">Roll-up</a>
    <a href="#dsm">DSM</a>
    <a href="#architecture">Architecture</a>
    <a href="#stats">Stats</a>
    <a href="#subsystems">Subsystems</a>
    <a href="#gaps">Gaps</a>
  </nav>

  {health_html}

  <div class="header">
    <div class="header-label">DOE Microreactor Program · Idaho National Laboratory</div>
    <h1>MARVEL <span>Microreactor</span></h1>
    <h1>TRL Assessment Dashboard</h1>
    <div class="header-sub" style="margin-top:10px;">{total_docs} documents · {len(SUB_KEYS)} subsystems</div>
  </div>

  <div class="rollup-banner" id="rollup" role="region" aria-label="Roll-up summary">
    <div class="rollup-kicker">Roll-up</div>
    <p><strong>TRL {min_lo}</strong> bottleneck: {html.escape(bneck_name)} · mean midpoint <strong>{avg_mid:.1f}</strong></p>
    {floor_line}
    {critical_dsm_html}
  </div>

  <section class="dsm-section" id="dsm">
    <h2>Subsystem coupling (DSM)</h2>
    <p class="dsm-note"><strong>S</strong> / <strong>M</strong> / <strong>W</strong> = strength · second line = coupling types (hover)</p>
    <p class="dsm-legend">Heat pipes · Core/fuel · Power conv. · I&amp;C · Safety · Grid/load</p>
    {dsm_html}
  </section>

  {arch_html}

  <div class="stats-row" id="stats">
    <div class="stat-card">
      <div class="stat-value">{total_docs}</div>
      <div class="stat-label">Scored documents (sum)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{total_hq}</div>
      <div class="stat-label">High quality (sum)</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{len(SUB_KEYS)}</div>
      <div class="stat-label">Subsystems</div>
    </div>
    <div class="stat-card">
      <div class="stat-value">{avg_mid:.1f}</div>
      <div class="stat-label">Mean TRL midpoint</div>
    </div>
  </div>

  {gap_html}

  <div class="subsystems-grid" id="subsystems">
{cards_html}
  </div>

  <footer class="footer" role="contentinfo">
    <div class="footer-inner">
      <div class="footer-brand">
        <span class="footer-title">MARVEL technology readiness</span>
        <span class="footer-team">Arizona State University · Decision Theater Lab · public literature synthesis</span>
      </div>
      <div class="footer-sources" aria-label="Document sources">
        <span class="footer-pill">DOE OSTI</span>
        <span class="footer-pill">arXiv</span>
        <span class="footer-pill">INL technical reports</span>
      </div>
    </div>
  </footer>

</div>

<script>
  window.addEventListener('load', () => {{
    setTimeout(() => {{
      document.querySelectorAll('.trl-bar-fill').forEach(bar => {{
        const width = bar.style.width;
        bar.style.width = '0';
        setTimeout(() => {{ bar.style.width = width; }}, 100);
      }});
    }}, 300);
  }});
</script>
</body>
</html>
"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"Wrote {OUT_PATH}")
    print(f"  Documents (summed): {total_docs}, high quality: {total_hq}")
    print(f"  Bottleneck: TRL {min_lo} — {bneck_name}")


if __name__ == "__main__":
    main()
