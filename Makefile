# MARVEL TRL pipeline — run from repo root (requires Python 3)
.PHONY: help score gaps trl dashboard all clean-gaps

help:
	@echo "Targets:"
	@echo "  make score      - data/raw → data/scored (run_scorer.py)"
	@echo "  make trl        - scored + Ollama → data/trl (run_trl_inference.py)"
	@echo "  make gaps       - scored + TRL report → data/gaps (run_gap_analysis.py)"
	@echo "  make dashboard  - gaps + JSON → MARVEL_TRL_Dashboard.html"
	@echo "  make all        - gaps + dashboard (no scrape, no new TRL inference)"

score:
	python3 run_scorer.py

trl:
	python3 run_trl_inference.py

gaps:
	python3 run_gap_analysis.py

dashboard: gaps
	python3 generate_dashboard.py

all: dashboard
