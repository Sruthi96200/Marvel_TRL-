# AI-Powered TRL Identification of Microreactors

> A multi-agent AI framework for automated Technology Readiness Level (TRL) assessment of the MARVEL nuclear microreactor using public technical literature.

**Team:** Jahnavi Lasyapriya Vavilala · Sruthi Keerthana Nuttakki · Anjali Balaram Mohanthy · Prajeet Darda  
**Built for:** ASU Decision Theater · DOE Microreactor Program · Idaho National Laboratory

---

## Objective

Assessing TRL of a developing complex technology such as microreactors requires domain expertise, involving frequent manual effort to understand information spread across various sources. This project demonstrates how AI tools can assist — but not replace — expert-driven TRL discussions by:

- Synthesizing public technical literature more efficiently
- Highlighting subsystem-level maturity differences
- Generating preliminary TRL estimates with confidence scores
- Identifying where evidence is strong and where gaps exist

---

## Multi-Agent Framework Architecture

```
PUBLIC DOCUMENTS (Input Source)
        │
        ▼
LITERATURE COLLECTOR — Identifies & Retrieves Documents
        │
        ▼
EVIDENCE EXTRACTOR — Extracts Milestones, Tests, Demos
        │
   ┌────┴────┐
   ▼         ▼
TRL MAPPER   GAP ANALYZER
(TRL Logic)  (Evidence Gaps & Weaknesses)
   │         │
   └────┬────┘
        ▼
REPORT GENERATOR — Synthesizes into Narrative Reports
        │
        ▼
   FINAL REPORT
```

---

## Pipeline

| Phase | Agent | Deliverable |
|-------|-------|-------------|
| Phase 1 | Indicator Dictionaries | TRL signal indicators for all 6 subsystems |
| Phase 2 | Search Agent | Source prioritization (Tier 1 / Tier 2 / Tier 3) |
| Phase 3 | Analysis Agent | Evidence extraction pipeline |
| Phase 4 | Classification Agent | TRL classification with confidence scoring |
| Phase 5 | MARVEL Testing | Validate system on historical data (2022–2024) |
| Phase 6 | SME Validation | Compare results against expert assessments |

---

## Implementation

| Step | Script | Output |
|------|--------|--------|
| Scrape evidence | `test_scraper.py` | `data/raw/*.json` |
| Score documents | `run_scorer.py` | `data/scored/*.json` |
| Infer TRL | `run_trl_inference.py` | `data/trl/*.json` (fail-safe: bad Ollama runs do not overwrite valid TRL; see `data/trl/failed_runs/`) |
| Gap analysis | `run_gap_analysis.py` | `data/gaps/MARVEL_GAP_REPORT.json` |
| Build dashboard | `generate_dashboard.py` | `MARVEL_TRL_Dashboard.html` (open in browser) |

Shortcut: `make dashboard` runs gap analysis then regenerates the HTML (see `Makefile`).

---

## Understanding Aid (SME Pass)

If you want to validate results rather than only run scripts, use:

- `docs/SME_REVIEW_WORKSHEET.md`

This guides a 45-60 minute subsystem review (evidence grounding, uncertainty, DSM/architecture checks, and decision note).

---

## Target Subsystems

Based on MARVEL's documented architecture:

1. Reactor Core & Fuel Assembly
2. Heat Transport System (Heat Pipes)
3. Power Conversion System (Stirling Engines)
4. Instrumentation & Control Systems
5. Safety & Shutdown Systems
6. Grid Integration and Load Coupling

---

## Results

| Subsystem | TRL Range | Confidence | Docs |
|-----------|-----------|------------|------|
| Heat Transport (Heat Pipes) | 5–6 | MEDIUM | 31 |
| Reactor Core and Fuel System | 5–6 | MEDIUM | 33 |
| Power Conversion (Stirling Engines) | 5–6 | MEDIUM | 31 |
| Control and Instrumentation Systems | 5–6 | MEDIUM | 23 |
| Safety and Shutdown Systems | 5–6 | MEDIUM | 12 |
| Grid Integration and Load Coupling | 5–6 | MEDIUM | 16 |

**Total:** 146 relevant documents · 90 high quality · 6 subsystems assessed

---

## Project Structure

```
marvel_trl/
├── config/
│   └── subsystems.py          # Subsystem definitions and search terms
├── src/tools/
│   ├── search_tools.py        # OSTI + arXiv scraper (Literature Collector)
│   ├── evidence_scorer.py     # Document quality scorer (Evidence Extractor)
│   └── trl_inferencer.py      # Ollama LLM TRL inference (TRL Mapper)
├── data/
│   ├── raw/                   # Scraped documents (JSON)
│   ├── scored/                # Quality-scored documents (JSON)
│   └── trl/                   # TRL estimates + final report (JSON)
├── test_scraper.py            # Run scraper for all subsystems
├── run_scorer.py              # Run evidence quality scorer
├── run_trl_inference.py       # Run TRL inference
└── MARVEL_TRL_Dashboard.html  # Visual dashboard (open in browser)
```

---

## How to Run

### 1. Install dependencies
```bash
pip install requests
```

### 2. Install Ollama + download model
Download from https://ollama.com/download then:
```bash
ollama pull llama3.2
```

### 3. Run the full pipeline
```bash
python test_scraper.py       # Scrape evidence
python run_scorer.py         # Score documents
python run_trl_inference.py  # Infer TRL
# Open MARVEL_TRL_Dashboard.html in browser
```

---

## Data Sources

- **OSTI** — DOE technical reports, journal articles, conference papers
- **arXiv** — Preprints and research papers
- Future: ANS conference proceedings, USPTO patents, INL technical reports

---

## TRL Scale Reference

| TRL | Description |
|-----|-------------|
| 1–2 | Basic concept / paper study only |
| 3–4 | Lab experiments / component validation |
| 5–6 | Component tested in relevant environment |
| 7–8 | System demonstrated in operational environment |
| 9 | Proven in operational mission |

---

## About MARVEL

MARVEL (Microreactor Applications Research Validation and EvaLuation) is an 85 kWth sodium-potassium cooled microreactor being built at Idaho National Laboratory by the U.S. Department of Energy. ASU's Decision Theater is one of five teams selected by DOE to run experiments on MARVEL, focusing on nuclear-to-data-center power integration.

---

*Proof-of-concept AI-assisted TRL workflow · Evidence scored via automated quality scorer · TRL inference via Ollama llama3.2*
