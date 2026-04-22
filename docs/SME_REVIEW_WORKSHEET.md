# SME Review Worksheet (Fast Pass)

Use this to move from "running scripts" to "defending judgments."
Target time: 45-60 minutes.

## 1) Choose one subsystem

- Suggested start: `control_systems` (lowest TRL lower bound) or `safety_systems` (gap pressure).

## 2) Evidence grounding (3-5 docs)

For each chosen document:

- **Claim observed:** What did they actually test/show?
- **Context:** Lab, relevant environment, integrated system, or conceptual?
- **Confidence impact:** Does this push TRL up, down, or stay neutral?
- **Transfer risk:** Is this directly MARVEL-relevant or adjacent-domain analogy?

## 3) What is still uncertain?

- **Missing evidence:** What specific test/result is absent?
- **Contradiction check:** Do high-score and low-score top-5 sources tell different stories?
- **Regulatory angle:** What is technical maturity vs licensing maturity?

## 4) Architecture/DSM check

Review:

- `config/marvel_architecture_tree.json`
- `config/marvel_dsm_edges.json`

Answer:

- Which component bullets are incomplete or too vague?
- Which edges should be `critical: true` (or not)?
- Any missing dependency type (`thermal`, `regulatory`, etc.)?

## 5) Decision note (short)

Write 5-7 sentences:

- Most defensible TRL band for this subsystem
- Why
- Main limitation
- One concrete next test that would change your confidence

## 6) Update files

- If structure changes: edit `config/marvel_architecture_tree.json` and `config/marvel_dsm_edges.json`
- Re-run: `make dashboard`
- Optional: commit as "SME review pass"

