# src/tools/trl_inferencer.py
# Uses Ollama (llama3.2) to estimate TRL for each MARVEL subsystem
# based on the top scored evidence documents

import json
import os
import requests


def _ollama_generate_url() -> str:
    """Base URL without trailing slash + /api/generate (trailing slash on host causes 404)."""
    base = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    return f"{base}/api/generate"


def _ollama_model() -> str:
    """Model tag must match `ollama list` (e.g. llama3.2, llama3.2:latest)."""
    return os.environ.get("OLLAMA_MODEL", "llama3.2")


class TRLInferencer:
    """
    Sends top scored evidence documents to Ollama
    and gets back a TRL estimate with reasoning.
    """

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

        model = _ollama_model()
        print(f"   🤖 Asking {model} to estimate TRL...")
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
        url = _ollama_generate_url()
        model = _ollama_model()
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
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
        except requests.exceptions.HTTPError as e:
            return self._format_ollama_http_error(e, url, model)
        except Exception as e:
            return f"ERROR: {str(e)}"

    def _format_ollama_http_error(
        self, e: requests.exceptions.HTTPError, url: str, model: str
    ) -> str:
        """Ollama often returns 404 when the model is missing; body has an 'error' string."""
        resp = e.response
        detail = ""
        if resp is not None:
            try:
                body = resp.json()
                if isinstance(body, dict) and body.get("error"):
                    detail = f" {body['error']}"
            except Exception:
                detail = f" {resp.text[:200]}" if resp.text else ""

        code = resp.status_code if resp is not None else "?"
        if code == 404:
            return (
                f"ERROR: HTTP 404 from Ollama at {url}.{detail} "
                f"If the model is missing, run: ollama pull {model.split(':')[0]} "
                f"Then check the exact name with: ollama list "
                f"(you can set OLLAMA_MODEL to match, e.g. export OLLAMA_MODEL=llama3.2:latest)."
            )
        return f"ERROR: HTTP {code} from Ollama.{detail}"

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