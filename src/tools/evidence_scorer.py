# src/tools/evidence_scorer.py
# Scores each scraped document on how useful it is for TRL assessment
# Each document gets a score 0.0 - 1.0 with detailed reasoning

import json
import os
from datetime import datetime


class EvidenceQualityScorer:
    """
    Scores documents on 5 dimensions:
    1. Source type      - Technical reports > journal articles > conference > other
    2. Recency          - Newer documents score higher
    3. MARVEL specific  - Mentions MARVEL/INL directly scores higher
    4. Evidence type    - Test results > simulations > concepts
    5. TRL signal       - Mentions readiness, qualification, demonstration
    
    Final score = weighted average of all 5 dimensions (0.0 to 1.0)
    """

    # --- Source type scores ---
    SOURCE_TYPE_SCORES = {
        "technical report":         0.95,  # INL/DOE reports = gold standard
        "program document":         0.90,  # Official program docs
        "journal article":          0.80,  # Peer reviewed
        "conference":               0.65,  # Conference papers
        "s&t accomplishment report":0.70,  # DOE accomplishment reports
        "other":                    0.40,  # Unknown
    }

    # --- Keywords that signal actual test/demonstration evidence ---
    TEST_EVIDENCE_KEYWORDS = [
        "test", "tested", "testing", "experiment", "experimental",
        "demonstrated", "demonstration", "measured", "measurement",
        "validated", "validation", "facility", "prototype",
        "operated", "operation", "hours", "duration",
        "SPHERE", "PCAT", "benchmark", "irradiation"
    ]

    # --- Keywords that signal only simulation/concept ---
    SIMULATION_KEYWORDS = [
        "model", "simulation", "simulated", "concept", "design",
        "proposed", "theoretical", "analytical", "calculated",
        "estimated", "preliminary", "feasibility"
    ]

    # --- Keywords that signal TRL relevance ---
    TRL_SIGNAL_KEYWORDS = [
        "readiness", "TRL", "maturity", "qualification", "qualified",
        "certified", "licensed", "approved", "NRC", "regulatory",
        "technology readiness", "deployment", "commercial",
        "ready", "demonstrated capability"
    ]

    # --- MARVEL/INL specific keywords ---
    MARVEL_KEYWORDS = [
        "MARVEL", "INL", "Idaho National Laboratory",
        "SPHERE", "NEAMS", "microreactor program",
        "DOE microreactor", "NRIC"
    ]

    def score_document(self, doc: dict) -> dict:
        """
        Score a single document and return it with scores attached.
        
        Returns the original doc plus:
        - quality_score: overall 0.0-1.0
        - score_breakdown: individual dimension scores
        - score_reasons: human readable explanation
        - evidence_tier: HIGH / MEDIUM / LOW
        """
        title = doc.get("title", "")
        snippet = doc.get("snippet", "")
        text = (title + " " + snippet).lower()

        source_type = doc.get("source_type", "other").lower()
        pub_date = doc.get("publication_date", "")
        source = doc.get("source", "")  # OSTI or arXiv

        # --- Score each dimension ---
        s1, r1 = self._score_source_type(source_type, source)
        s2, r2 = self._score_recency(pub_date)
        s3, r3 = self._score_marvel_specific(text)
        s4, r4 = self._score_evidence_type(text)
        s5, r5 = self._score_trl_signal(text)

        # --- Weighted average ---
        # Source type and evidence type matter most for TRL assessment
        weights = {
            "source_type":    0.25,
            "recency":        0.15,
            "marvel_specific":0.25,
            "evidence_type":  0.25,
            "trl_signal":     0.10,
        }

        overall = (
            s1 * weights["source_type"] +
            s2 * weights["recency"] +
            s3 * weights["marvel_specific"] +
            s4 * weights["evidence_type"] +
            s5 * weights["trl_signal"]
        )
        overall = round(overall, 3)

        # --- Assign tier ---
        if overall >= 0.55:
            tier = "HIGH"
        elif overall >= 0.35:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        # --- Attach scores to document ---
        scored_doc = doc.copy()
        scored_doc["quality_score"] = overall
        scored_doc["evidence_tier"] = tier
        scored_doc["score_breakdown"] = {
            "source_type":     round(s1, 2),
            "recency":         round(s2, 2),
            "marvel_specific": round(s3, 2),
            "evidence_type":   round(s4, 2),
            "trl_signal":      round(s5, 2),
        }
        scored_doc["score_reasons"] = {
            "source_type":     r1,
            "recency":         r2,
            "marvel_specific": r3,
            "evidence_type":   r4,
            "trl_signal":      r5,
        }

        return scored_doc

    # ------------------------------------------------------------------ #
    #  Dimension scorers                                                   #
    # ------------------------------------------------------------------ #

    def _score_source_type(self, source_type: str, source: str) -> tuple:
        """Score based on document type."""
        # arXiv preprints are lower quality than OSTI technical reports
        if source == "arXiv":
            return 0.50, "arXiv preprint — not peer reviewed or officially published"

        for key, score in self.SOURCE_TYPE_SCORES.items():
            if key in source_type:
                return score, f"Source type: {source_type}"

        return 0.40, f"Unknown source type: '{source_type}'"

    def _score_recency(self, pub_date: str) -> tuple:
        """Score based on publication date. Newer = better for TRL evidence."""
        if not pub_date:
            return 0.30, "No publication date available"

        try:
            # Handle both "2026-02-06T00:00:00Z" and "2026-02-06" formats
            date_str = pub_date[:10]
            year = int(date_str[:4])
            current_year = datetime.now().year

            age = current_year - year

            if age <= 1:
                return 1.0, f"Very recent ({year}) — highly relevant"
            elif age <= 3:
                return 0.80, f"Recent ({year}) — likely relevant"
            elif age <= 6:
                return 0.60, f"Moderately recent ({year})"
            elif age <= 10:
                return 0.40, f"Older ({year}) — may be outdated"
            else:
                return 0.20, f"Old ({year}) — likely outdated for TRL assessment"

        except Exception:
            return 0.30, "Could not parse publication date"

    def _score_marvel_specific(self, text: str) -> tuple:
        """Score based on how specific to MARVEL/INL the document is."""
        hits = [kw for kw in self.MARVEL_KEYWORDS if kw.lower() in text]

        if len(hits) >= 3:
            return 1.0, f"Highly MARVEL-specific — mentions: {', '.join(hits[:3])}"
        elif len(hits) == 2:
            return 0.80, f"MARVEL-related — mentions: {', '.join(hits)}"
        elif len(hits) == 1:
            return 0.60, f"Partially relevant — mentions: {hits[0]}"
        else:
            return 0.20, "No direct MARVEL/INL mention — general nuclear content"

    def _score_evidence_type(self, text: str) -> tuple:
        """Score based on whether document describes real tests vs just models."""
        test_hits = [kw for kw in self.TEST_EVIDENCE_KEYWORDS if kw.lower() in text]
        sim_hits = [kw for kw in self.SIMULATION_KEYWORDS if kw.lower() in text]

        has_test = len(test_hits) >= 2
        has_sim = len(sim_hits) >= 2

        if has_test and not has_sim:
            return 1.0, f"Strong test/experimental evidence — keywords: {', '.join(test_hits[:3])}"
        elif has_test and has_sim:
            return 0.75, f"Mixed test + simulation evidence"
        elif has_sim and not has_test:
            return 0.40, f"Primarily simulation/modeling — keywords: {', '.join(sim_hits[:3])}"
        else:
            return 0.50, "Unclear evidence type"

    def _score_trl_signal(self, text: str) -> tuple:
        """Score based on whether document explicitly discusses readiness/maturity."""
        hits = [kw for kw in self.TRL_SIGNAL_KEYWORDS if kw.lower() in text]

        if len(hits) >= 2:
            return 1.0, f"Explicit TRL/readiness signals — keywords: {', '.join(hits[:3])}"
        elif len(hits) == 1:
            return 0.60, f"Weak TRL signal — mentions: {hits[0]}"
        else:
            return 0.20, "No explicit TRL/readiness signal"

    # ------------------------------------------------------------------ #
    #  Batch processing                                                    #
    # ------------------------------------------------------------------ #

    def score_subsystem_file(self, input_path: str, output_path: str) -> dict:
        """
        Load a scraped JSON file, score all documents, save scored version.
        Returns summary statistics.
        """
        with open(input_path) as f:
            data = json.load(f)

        # Score OSTI results
        scored_osti = [self.score_document(doc) for doc in data.get("osti_results", [])]

        # Score arXiv results
        scored_arxiv = [self.score_document(doc) for doc in data.get("arxiv_results", [])]

        # Sort each by quality score descending
        scored_osti.sort(key=lambda x: x["quality_score"], reverse=True)
        scored_arxiv.sort(key=lambda x: x["quality_score"], reverse=True)

        # Build output
        all_docs = scored_osti + scored_arxiv
        all_docs.sort(key=lambda x: x["quality_score"], reverse=True)

        # Compute stats
        scores = [d["quality_score"] for d in all_docs]
        high = sum(1 for d in all_docs if d["evidence_tier"] == "HIGH")
        medium = sum(1 for d in all_docs if d["evidence_tier"] == "MEDIUM")
        low = sum(1 for d in all_docs if d["evidence_tier"] == "LOW")

        output_data = {
            "subsystem": data["subsystem"],
            "name": data["name"],
            "scoring_summary": {
                "total_documents": len(all_docs),
                "avg_quality_score": round(sum(scores) / len(scores), 3) if scores else 0,
                "high_quality": high,
                "medium_quality": medium,
                "low_quality": low,
                "top_document": all_docs[0]["title"] if all_docs else "None"
            },
            "scored_documents": all_docs
        }

        # Save
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        return output_data["scoring_summary"]