from typing import Any
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from mcp_server.config import KUBECONFIG_PATH, K8S_NAMESPACE, K8S_MOCK_MODE


def load_k8s_config() -> None:
    if K8S_MOCK_MODE:
        return

    if KUBECONFIG_PATH:
        config.load_kube_config(config_file=KUBECONFIG_PATH)
    else:
        config.load_kube_config()


def fetch_cluster_context() -> dict[str, Any]:
    if K8S_MOCK_MODE:
        return {
            "namespace": K8S_NAMESPACE,
            "namespaces": ["default", "kube-system", "dev"],
            "existing_pods": ["demo-pod-1", "demo-pod-2"],
            "mode": "mock",
        }

    load_k8s_config()
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    namespaces = [ns.metadata.name for ns in v1.list_namespace().items]
    pods = [pod.metadata.name for pod in v1.list_namespaced_pod(K8S_NAMESPACE).items]
    deployments = [
        dep.metadata.name
        for dep in apps_v1.list_namespaced_deployment(K8S_NAMESPACE).items
    ]

    return {
        "namespace": K8S_NAMESPACE,
        "namespaces": namespaces,
        "existing_pods": pods,
        "existing_deployments": deployments,
        "mode": "real",
    }


def apply_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if K8S_MOCK_MODE:
        return {
            "success": True,
            "kind": manifest.get("kind"),
            "name": manifest.get("metadata", {}).get("name", "unknown"),
            "namespace": manifest.get("metadata", {}).get("namespace", K8S_NAMESPACE),
            "message": "Mock apply completed successfully",
        }

    load_k8s_config()

    kind = manifest.get("kind")
    metadata = manifest.get("metadata", {})
    name = metadata.get("name", "unknown")
    namespace = metadata.get("namespace", K8S_NAMESPACE)

    try:
        if kind == "ConfigMap":
            v1 = client.CoreV1Api()
            body = client.V1ConfigMap(**manifest)

            try:
                v1.read_namespaced_config_map(name=name, namespace=namespace)
                v1.replace_namespaced_config_map(name=name, namespace=namespace, body=body)
                action = "updated"
            except ApiException as exc:
                if exc.status == 404:
                    v1.create_namespaced_config_map(namespace=namespace, body=body)
                    action = "created"
                else:
                    raise

            return {
                "success": True,
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "message": f"ConfigMap {action} successfully",
            }

        elif kind == "Deployment":
            apps_v1 = client.AppsV1Api()
            body = client.V1Deployment(**manifest)

            try:
                apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
                apps_v1.replace_namespaced_deployment(name=name, namespace=namespace, body=body)
                action = "updated"
            except ApiException as exc:
                if exc.status == 404:
                    apps_v1.create_namespaced_deployment(namespace=namespace, body=body)
                    action = "created"
                else:
                    raise

            return {
                "success": True,
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "message": f"Deployment {action} successfully",
            }

        elif kind == "Service":
            v1 = client.CoreV1Api()
            body = client.V1Service(**manifest)

            try:
                v1.read_namespaced_service(name=name, namespace=namespace)
                v1.replace_namespaced_service(name=name, namespace=namespace, body=body)
                action = "updated"
            except ApiException as exc:
                if exc.status == 404:
                    v1.create_namespaced_service(namespace=namespace, body=body)
                    action = "created"
                else:
                    raise

            return {
                "success": True,
                "kind": kind,
                "name": name,
                "namespace": namespace,
                "message": f"Service {action} successfully",
            }

        else:
            raise ValueError(
                f"Apply is not yet supported for kind='{kind}'. "
                "Supported kinds: ConfigMap, Deployment, Service."
            )

    except Exception as exc:
        return {
            "success": False,
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "message": f"Failed to apply manifest: {str(exc)}",
        }


def verify_deployment(name: str, namespace: str | None = None) -> dict[str, Any]:
    namespace = namespace or K8S_NAMESPACE

    if K8S_MOCK_MODE:
        return {
            "success": True,
            "deployment": name,
            "namespace": namespace,
            "ready": True,
            "message": "Mock deployment verification passed",
        }

    load_k8s_config()
    apps_v1 = client.AppsV1Api()

    try:
        deployment = apps_v1.read_namespaced_deployment(name=name, namespace=namespace)
        desired = deployment.spec.replicas or 0
        ready = deployment.status.ready_replicas or 0
        available = deployment.status.available_replicas or 0

        success = ready >= desired and available >= desired

        return {
            "success": success,
            "deployment": name,
            "namespace": namespace,
            "desired_replicas": desired,
            "ready_replicas": ready,
            "available_replicas": available,
            "message": "Deployment rollout successful" if success else "Deployment rollout not complete",
        }

    except Exception as exc:
        return {
            "success": False,
            "deployment": name,
            "namespace": namespace,
            "message": f"Failed to verify deployment: {str(exc)}",
        }