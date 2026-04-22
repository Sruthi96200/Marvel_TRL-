# src/tools/gap_analyzer.py
# Evidence gap analysis: corpus coverage, simulation vs test balance, gap language,
# source diversity — complements TRL LIMIT/NEXT (prof framing: thin / contradictory / uncertain).

from __future__ import annotations

import json
import statistics
from datetime import datetime, timezone
from typing import Any, Optional

from src.tools.evidence_scorer import EvidenceQualityScorer

GAP_PHRASES = [
    "knowledge gap",
    "future work",
    "not yet demonstrated",
    "not been demonstrated",
    "lacks ",
    "lack of",
    "limited data",
    "limited evidence",
    "further research",
    "remaining challenge",
    "open question",
    " additional study",
    "needs to be validated",
    "has not been",
    "no clear evidence",
    "sparse",
    "uncertainty remains",
    "more work is needed",
    # Nuclear / program language (MARVEL, SMR, licensing)
    "licensing basis",
    "regulatory acceptance",
    "not yet qualified",
    "qualification path",
    "beyond design basis",
    "pre-application",
    "conceptual design",
    "preliminary design",
    "unresolved issue",
    "vendor claims",
    "independent validation",
    "irradiation data",
    "operational experience",
    "first-of-a-kind",
]


def _count_keyword_hits(text: str, keywords: list) -> int:
    t = text.lower()
    return sum(1 for k in keywords if k.lower() in t)


def _simulation_vs_test_balance(snippet: str, title: str) -> tuple[int, int]:
    blob = f"{title} {snippet}".lower()
    sim = _count_keyword_hits(blob, EvidenceQualityScorer.SIMULATION_KEYWORDS)
    test = _count_keyword_hits(blob, EvidenceQualityScorer.TEST_EVIDENCE_KEYWORDS)
    return sim, test


def _gap_phrase_hits(blob: str) -> int:
    b = blob.lower()
    return sum(1 for p in GAP_PHRASES if p in b)


def analyze_subsystem(
    key: str,
    subsystem_name: str,
    scored: dict,
    trl_entry: Optional[dict],
    peer_median_docs: float,
) -> dict[str, Any]:
    docs = scored.get("scored_documents") or []
    summary = scored.get("scoring_summary") or {}
    n = len(docs)
    if n == 0:
        return {
            "subsystem_key": key,
            "name": subsystem_name,
            "coverage_label": "NO_DATA",
            "gap_index": 100,
            "signals": ["No scored documents in corpus."],
            "metrics": {},
            "from_trl_report": _trl_slice(trl_entry),
        }

    high_q = sum(1 for d in docs if d.get("evidence_tier") == "HIGH")
    hq_ratio = high_q / n
    scores = [float(d.get("quality_score") or 0) for d in docs]
    avg_q = sum(scores) / n

    osti = sum(1 for d in docs if str(d.get("source", "")).upper() == "OSTI")
    arxiv = sum(1 for d in docs if "arxiv" in str(d.get("source", "")).lower())
    stypes = {str(d.get("source_type") or "unknown").lower() for d in docs}

    gap_doc_hits = 0
    sim_heavy = 0
    weak_trl_signals = []
    for d in docs:
        blob = f"{d.get('title', '')} {d.get('snippet', '')}"
        if _gap_phrase_hits(blob) > 0:
            gap_doc_hits += 1
        sim, test = _simulation_vs_test_balance(
            d.get("snippet") or "", d.get("title") or ""
        )
        if sim >= test + 2 and sim >= 3:
            sim_heavy += 1
        tb = (d.get("score_breakdown") or {}).get("trl_signal")
        if tb is not None and float(tb) < 0.35:
            weak_trl_signals.append(float(tb))

    gap_phrase_rate = gap_doc_hits / n
    sim_heavy_ratio = sim_heavy / n
    avg_trl_sig = (
        sum(weak_trl_signals) / len(weak_trl_signals) if weak_trl_signals else None
    )

    top5 = scores[:5] if len(scores) >= 5 else scores
    score_spread = statistics.pstdev(top5) if len(top5) >= 2 else 0.0

    top5_docs = docs[:5]
    contrast: Optional[dict[str, Any]] = None
    # Max–min in top-ranked five (more reliable than pstdev on small sets)
    if len(top5_docs) >= 2:
        sorted5 = sorted(
            top5_docs,
            key=lambda d: float(d.get("quality_score") or 0),
            reverse=True,
        )
        hi_d, lo_d = sorted5[0], sorted5[-1]
        hi_s = float(hi_d.get("quality_score") or 0)
        lo_s = float(lo_d.get("quality_score") or 0)
        if hi_s - lo_s >= 0.06:
            contrast = {
                "higher_quality_title": (hi_d.get("title") or "")[:240],
                "higher_quality_score": round(hi_s, 3),
                "lower_quality_title": (lo_d.get("title") or "")[:240],
                "lower_quality_score": round(lo_s, 3),
            }

    metrics = {
        "total_documents": n,
        "high_quality_count": high_q,
        "high_quality_ratio": round(hq_ratio, 3),
        "avg_quality_score": round(avg_q, 3),
        "osti_count": osti,
        "arxiv_count": arxiv,
        "source_type_variety": len(stypes),
        "gap_language_doc_fraction": round(gap_phrase_rate, 3),
        "simulation_heavy_doc_fraction": round(sim_heavy_ratio, 3),
        "top5_quality_spread": round(score_spread, 4),
        "top5_contrast": contrast,
    }

    signals: list[str] = []

    if n < max(10, peer_median_docs * 0.65):
        signals.append(
            f"Thin corpus ({n} docs) vs. peer median (~{peer_median_docs:.0f}) — higher uncertainty for TRL claims."
        )
    if hq_ratio < 0.55:
        signals.append(
            f"Less than 55% of documents are HIGH tier ({high_q}/{n}); evidence strength is uneven."
        )
    if gap_phrase_rate >= 0.25:
        signals.append(
            "Many sources use gap / limitation language — corpus itself flags open technical questions."
        )
    if sim_heavy_ratio >= 0.35:
        signals.append(
            "Substantial share of documents lean simulation/concept-heavy vs. test-forward wording — watch integration blindness."
        )
    if len(stypes) <= 2 and n >= 8:
        signals.append(
            "Low variety of source types — promotional or procedural bias possible; seek independent verification."
        )
    if score_spread >= 0.12:
        signals.append(
            "High spread in top-ranked document quality — mixed evidence types; analyst review recommended."
        )
    if contrast:
        ht = contrast["higher_quality_title"]
        lt = contrast["lower_quality_title"]
        signals.append(
            "Top-ranked evidence contrast (triangulation): higher-scored source vs. lower-scored source "
            f"both in top five — compare «{ht[:90]}» "
            f"vs «{lt[:90]}»."
        )
    if osti > 0 and arxiv == 0 and n < 20:
        signals.append(
            "No arXiv hits; corpus may miss preprint / academic angles for this subsystem."
        )

    tslice = _trl_slice(trl_entry)
    if tslice.get("limiting_factor"):
        signals.append(f"TRL assessment limit: {tslice['limiting_factor'][:200]}{'…' if len(tslice.get('limiting_factor', '')) > 200 else ''}")

    # Composite gap index: higher = more concern (0–100)
    idx = 0
    if n < peer_median_docs * 0.7:
        idx += 22
    elif n < peer_median_docs * 0.9:
        idx += 12
    if hq_ratio < 0.5:
        idx += 18
    elif hq_ratio < 0.65:
        idx += 8
    if gap_phrase_rate >= 0.35:
        idx += 15
    elif gap_phrase_rate >= 0.2:
        idx += 8
    if sim_heavy_ratio >= 0.45:
        idx += 15
    elif sim_heavy_ratio >= 0.3:
        idx += 8
    if score_spread >= 0.12:
        idx += 10
    if len(stypes) <= 2 and n >= 10:
        idx += 8
    idx = min(100, idx)

    if idx >= 55:
        coverage = "WEAK"
    elif idx >= 30:
        coverage = "MODERATE"
    else:
        coverage = "STRONG"

    if not signals:
        signals.append(
            "No major automated gap flags — still review LIMIT/NEXT and licensing vs. technical maturity."
        )

    return {
        "subsystem_key": key,
        "name": subsystem_name,
        "coverage_label": coverage,
        "gap_index": idx,
        "signals": signals,
        "metrics": metrics,
        "from_trl_report": tslice,
    }


def _trl_slice(trl: Optional[dict]) -> dict:
    if not trl:
        return {}
    return {
        "trl_range": trl.get("trl_range"),
        "confidence": trl.get("confidence"),
        "limiting_factor": (trl.get("limiting_factor") or "").strip(),
        "next_step": (trl.get("next_step") or "").strip(),
    }


def build_gap_report(
    subsystem_keys: list[str],
    subsystem_names: dict[str, str],
    scored_dir: str,
    trl_report_path: str,
) -> dict[str, Any]:
    with open(trl_report_path, encoding="utf-8") as f:
        trl_report = json.load(f)

    counts = []
    scored_map: dict[str, dict] = {}
    for key in subsystem_keys:
        path = f"{scored_dir}/{key}_scored.json"
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {"scored_documents": [], "scoring_summary": {}}
        scored_map[key] = data
        counts.append(len(data.get("scored_documents") or []))

    peer_median = statistics.median(counts) if counts else 0.0

    subsystems: dict[str, Any] = {}
    for key in subsystem_keys:
        name = subsystem_names.get(key, key)
        subsystems[key] = analyze_subsystem(
            key,
            name,
            scored_map[key],
            trl_report.get(key),
            peer_median,
        )

    ranked = sorted(
        subsystems.items(),
        key=lambda x: x[1].get("gap_index", 0),
        reverse=True,
    )
    highest_gap = [k for k, v in ranked if v.get("gap_index", 0) >= 25][:3]
    if not highest_gap and ranked:
        highest_gap = [ranked[0][0]]
        if len(ranked) > 1:
            highest_gap.append(ranked[1][0])

    return {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "peer_median_document_count": round(peer_median, 1),
        "summary": {
            "highest_gap_pressure_subsystems": highest_gap,
            "framing": (
                "Gap index is a heuristic (0–100): higher suggests thinner or more uneven evidence "
                "relative to peers. It does not replace SME review or licensing assessment."
            ),
        },
        "subsystems": subsystems,
    }
