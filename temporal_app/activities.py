from temporalio import activity
from temporalio.exceptions import ApplicationError

from mcp_server.services.yaml_service import (
    parse_yaml,
    validate_manifest_or_raise,
)
from mcp_server.services.k8s_service import fetch_cluster_context, apply_manifest
from mcp_server.services.ai_service import analyze_with_ai
from mcp_server.services.opa_service import evaluate_with_opa


@activity.defn
async def validate_yaml_activity(yaml_content: str) -> dict:
    try:
        manifest = parse_yaml(yaml_content)
        validate_manifest_or_raise(manifest)
        return manifest

    except Exception as exc:
        raise ApplicationError(
            f"YAML validation failed: {str(exc)}",
            non_retryable=True,
        )


@activity.defn
async def fetch_cluster_context_activity() -> dict:
    try:
        return fetch_cluster_context()
    except Exception as exc:
        raise ApplicationError(f"Cluster context fetch failed: {str(exc)}")


@activity.defn
async def ai_analysis_activity(manifest: dict, cluster_context: dict) -> dict:
    try:
        return analyze_with_ai(manifest, cluster_context)
    except Exception as exc:
        raise ApplicationError(f"AI analysis failed: {str(exc)}")


@activity.defn
async def opa_check_activity(manifest: dict) -> dict:
    try:
        return evaluate_with_opa(manifest)
    except Exception as exc:
        raise ApplicationError(f"OPA evaluation failed: {str(exc)}")


@activity.defn
async def apply_manifest_activity(manifest: dict) -> dict:
    try:
        return apply_manifest(manifest)
    except Exception as exc:
        raise ApplicationError(f"Apply manifest failed: {str(exc)}")