import yaml
import requests
from mcp_server.config import OPA_URL


def evaluate_with_opa(manifest) -> dict:
    try:
        # If manifest is YAML string, convert it to dict
        if isinstance(manifest, str):
            manifest = yaml.safe_load(manifest)

        if not isinstance(manifest, dict):
            return {
                "allow": False,
                "violations": ["Invalid manifest format for OPA"],
            }

        payload = {"input": manifest}

        response = requests.post(OPA_URL, json=payload, timeout=20)
        response.raise_for_status()

        raw = response.json()
        result = raw.get("result", {})

        if isinstance(result, dict) and "result" in result:
            result = result["result"]

        return {
            "allow": bool(result.get("allow", False)),
            "violations": result.get("violations", []),
        }

    except Exception as exc:
        return {
            "allow": False,
            "violations": [f"OPA check failed: {str(exc)}"],
        }