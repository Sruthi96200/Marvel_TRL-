# src/tools/trl_inferencer.py
# Uses Ollama (llama3.2) to estimate TRL for each MARVEL subsystem
# based on the top scored evidence documents

import json
import os
import requests


class TRLInferencer:
    """
    Sends top scored evidence documents to Ollama (llama3.2)
    and gets back a TRL estimate with reasoning.
    """

    OLLAMA_URL = "http://localhost:11434/api/generate"
    MODEL = "llama3.2"

    # How many top documents to send to the LLM per subsystem
    TOP_N_DOCS = 5

    def estimate_trl(self, subsystem_name: str, documents: list) -> dict:
        """
        Given a list of scored documents for a subsystem,
        pick the top N and ask the LLM to estimate TRL.
        """
        # Pick top N by quality score
        top_docs = sorted(
            documents,
            key=lambda x: x.get("quality_score", 0),
            reverse=True
        )[:self.TOP_N_DOCS]

        # Build the prompt
        prompt = self._build_prompt(subsystem_name, top_docs)

        # Call Ollama
        print(f"   🤖 Asking llama3.2 to estimate TRL...")
        response = self._call_ollama(prompt)

        # Parse the response
        result = self._parse_response(response)
        result["subsystem"] = subsystem_name
        result["evidence_used"] = [d["title"] for d in top_docs]
        result["top_doc_scores"] = [d.get("quality_score", 0) for d in top_docs]

        return result

    def _build_prompt(self, subsystem_name: str, documents: list) -> str:
        """Build a structured prompt for TRL estimation."""

        # Format evidence summaries
        evidence_text = ""
        for i, doc in enumerate(documents, 1):
            evidence_text += f"""
Document {i}:
  Title: {doc.get('title', 'Unknown')}
  Source: {doc.get('source', 'Unknown')} ({doc.get('source_type', 'Unknown')})
  Date: {doc.get('publication_date', 'Unknown')[:10]}
  Quality Score: {doc.get('quality_score', 0)}
  Summary: {doc.get('snippet', 'No summary available')[:300]}
"""

        prompt = f"""You are a nuclear technology expert assessing Technology Readiness Levels (TRLs).

TRL Scale:
- TRL 1-2: Basic concept / paper study only
- TRL 3-4: Lab experiments / component validation in lab
- TRL 5-6: Component tested in relevant environment / prototype demo
- TRL 7-8: System demonstrated in operational environment / qualified
- TRL 9: Proven in operational mission

Subsystem to assess: {subsystem_name}

Evidence documents:
{evidence_text}

Based on this evidence, provide your TRL assessment in this exact format:

TRL_RANGE: [e.g. 4-5]
CONFIDENCE: [LOW / MEDIUM / HIGH]
SUMMARY: [2-3 sentences explaining the TRL estimate]
KEY_EVIDENCE: [The single most important piece of evidence that drove your estimate]
LIMITING_FACTOR: [What is holding this subsystem back from a higher TRL]
NEXT_STEP: [What would need to happen to advance to the next TRL]

Be conservative and honest. If evidence is limited, say so."""

        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """Call Ollama API and return the response text."""
        try:
            response = requests.post(
                self.OLLAMA_URL,
                json={
                    "model": self.MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,  # Low temperature = more consistent
                        "num_predict": 400
                    }
                },
                timeout=120  # 2 minutes timeout
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.exceptions.ConnectionError:
            return "ERROR: Could not connect to Ollama. Make sure Ollama is running."
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _parse_response(self, response: str) -> dict:
        """Parse the structured response from the LLM."""
        result = {
            "trl_range": "Unknown",
            "confidence": "Unknown",
            "summary": "",
            "key_evidence": "",
            "limiting_factor": "",
            "next_step": "",
            "raw_response": response
        }

        if response.startswith("ERROR"):
            result["trl_range"] = "Error"
            result["summary"] = response
            return result

        lines = response.strip().split("\n")
        for line in lines:
            if line.startswith("TRL_RANGE:"):
                result["trl_range"] = line.replace("TRL_RANGE:", "").strip()
            elif line.startswith("CONFIDENCE:"):
                result["confidence"] = line.replace("CONFIDENCE:", "").strip()
            elif line.startswith("SUMMARY:"):
                result["summary"] = line.replace("SUMMARY:", "").strip()
            elif line.startswith("KEY_EVIDENCE:"):
                result["key_evidence"] = line.replace("KEY_EVIDENCE:", "").strip()
            elif line.startswith("LIMITING_FACTOR:"):
                result["limiting_factor"] = line.replace("LIMITING_FACTOR:", "").strip()
            elif line.startswith("NEXT_STEP:"):
                result["next_step"] = line.replace("NEXT_STEP:", "").strip()

        return result