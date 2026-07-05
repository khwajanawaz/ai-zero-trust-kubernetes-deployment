import json
from typing import Any

import requests

from mcp_server.config import OPENAI_API_KEY, OPENAI_MODEL


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"


def _fallback_ai_result(reason: str) -> dict[str, Any]:
    return {
        "risk_level": "unknown",
        "recommendation": "manual_review",
        "reason": reason,
        "suggested_fixes": [],
    }


def analyze_with_ai(manifest: dict[str, Any], cluster_context: dict[str, Any]) -> dict[str, Any]:
    """
    Send Kubernetes manifest + cluster context to OpenAI and return a structured risk analysis.

    Expected output format:
    {
        "risk_level": "low" | "medium" | "high" | "unknown",
        "recommendation": "approve" | "deny" | "manual_review",
        "reason": "short explanation",
        "suggested_fixes": ["fix1", "fix2"]
    }
    """
    if not OPENAI_API_KEY:
        return _fallback_ai_result("OPENAI_API_KEY is not set")

    prompt = f"""
You are a strict Kubernetes DevSecOps reviewer.

Analyze the Kubernetes manifest and cluster context below.

STRICT RULES:
- Return ONLY valid JSON
- Do NOT include markdown
- Do NOT include explanation outside JSON
- Output must be parseable by json.loads()

Return exactly this JSON structure:
{{
  "risk_level": "low | medium | high",
  "recommendation": "approve | deny | manual_review",
  "reason": "short explanation",
  "suggested_fixes": ["fix1", "fix2"]
}}

Decision guidance:
- Return "deny" if there are serious deployment or security risks
- Return "manual_review" if the result is uncertain or needs human review
- Return "approve" only if risk is low and the manifest looks safe

Manifest:
{json.dumps(manifest, indent=2)}

Cluster Context:
{json.dumps(cluster_context, indent=2)}
""".strip()

    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a strict Kubernetes DevSecOps reviewer that returns JSON only.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return _fallback_ai_result(f"OpenAI API request failed: {str(exc)}")

    try:
        response_data = response.json()
        content = response_data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        return _fallback_ai_result(f"Invalid OpenAI API response format: {str(exc)}")

    try:
        ai_result = json.loads(content)
    except json.JSONDecodeError:
        return _fallback_ai_result(f"Model returned non-JSON output: {content}")

    risk_level = str(ai_result.get("risk_level", "unknown")).lower()
    recommendation = str(ai_result.get("recommendation", "manual_review")).lower()
    reason = str(ai_result.get("reason", "No reason provided")).strip()

    suggested_fixes = ai_result.get("suggested_fixes", [])
    if not isinstance(suggested_fixes, list):
        suggested_fixes = [str(suggested_fixes)]

    allowed_risk_levels = {"low", "medium", "high", "unknown"}
    allowed_recommendations = {"approve", "deny", "manual_review"}

    if risk_level not in allowed_risk_levels:
        risk_level = "unknown"

    if recommendation not in allowed_recommendations:
        recommendation = "manual_review"

    return {
        "risk_level": risk_level,
        "recommendation": recommendation,
        "reason": reason,
        "suggested_fixes": [str(item) for item in suggested_fixes],
    }