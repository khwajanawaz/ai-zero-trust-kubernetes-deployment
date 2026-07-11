from typing import Any

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.config.config_exception import ConfigException

from mcp_server.config import (
    KUBECONFIG_PATH,
    K8S_NAMESPACE,
    K8S_MOCK_MODE,
)


def load_k8s_config() -> None:
    """
    Load Kubernetes authentication.

    Inside EKS:
        Uses the Pod ServiceAccount through in-cluster configuration.

    Outside EKS:
        Falls back to the kubeconfig file.
    """
    if K8S_MOCK_MODE:
        return

    try:
        config.load_incluster_config()
    except ConfigException:
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
            "existing_deployments": [],
            "mode": "mock",
        }

    load_k8s_config()

    core_api = client.CoreV1Api()
    apps_api = client.AppsV1Api()

    namespaces = [
        namespace.metadata.name
        for namespace in core_api.list_namespace().items
    ]

    pods = [
        pod.metadata.name
        for pod in core_api.list_namespaced_pod(
            namespace=K8S_NAMESPACE
        ).items
    ]

    deployments = [
        deployment.metadata.name
        for deployment in apps_api.list_namespaced_deployment(
            namespace=K8S_NAMESPACE
        ).items
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
            "name": manifest.get("metadata", {}).get(
                "name",
                "unknown",
            ),
            "namespace": manifest.get("metadata", {}).get(
                "namespace",
                K8S_NAMESPACE,
            ),
            "message": "Mock apply completed successfully",
        }

    load_k8s_config()

    kind = manifest.get("kind")
    metadata = manifest.get("metadata", {})
    name = metadata.get("name", "unknown")
    namespace = metadata.get("namespace", K8S_NAMESPACE)

    try:
        if kind == "ConfigMap":
            core_api = client.CoreV1Api()
            body = client.ApiClient()._ApiClient__deserialize(
                manifest,
                "V1ConfigMap",
            )

            try:
                core_api.read_namespaced_config_map(
                    name=name,
                    namespace=namespace,
                )

                core_api.replace_namespaced_config_map(
                    name=name,
                    namespace=namespace,
                    body=body,
                )

                action = "updated"

            except ApiException as exc:
                if exc.status == 404:
                    core_api.create_namespaced_config_map(
                        namespace=namespace,
                        body=body,
                    )
                    action = "created"
                else:
                    raise

        elif kind == "Deployment":
            apps_api = client.AppsV1Api()
            body = client.ApiClient()._ApiClient__deserialize(
                manifest,
                "V1Deployment",
            )

            try:
                apps_api.read_namespaced_deployment(
                    name=name,
                    namespace=namespace,
                )

                apps_api.replace_namespaced_deployment(
                    name=name,
                    namespace=namespace,
                    body=body,
                )

                action = "updated"

            except ApiException as exc:
                if exc.status == 404:
                    apps_api.create_namespaced_deployment(
                        namespace=namespace,
                        body=body,
                    )
                    action = "created"
                else:
                    raise

        elif kind == "Service":
            core_api = client.CoreV1Api()
            body = client.ApiClient()._ApiClient__deserialize(
                manifest,
                "V1Service",
            )

            try:
                existing_service = core_api.read_namespaced_service(
                    name=name,
                    namespace=namespace,
                )

                if (
                    existing_service.spec
                    and existing_service.spec.cluster_ip
                ):
                    body.spec.cluster_ip = (
                        existing_service.spec.cluster_ip
                    )

                core_api.replace_namespaced_service(
                    name=name,
                    namespace=namespace,
                    body=body,
                )

                action = "updated"

            except ApiException as exc:
                if exc.status == 404:
                    core_api.create_namespaced_service(
                        namespace=namespace,
                        body=body,
                    )
                    action = "created"
                else:
                    raise

        else:
            raise ValueError(
                f"Apply is not supported for kind='{kind}'. "
                "Supported kinds: ConfigMap, Deployment, Service."
            )

        return {
            "success": True,
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "message": f"{kind} {action} successfully",
        }

    except Exception as exc:
        return {
            "success": False,
            "kind": kind,
            "name": name,
            "namespace": namespace,
            "message": f"Failed to apply manifest: {str(exc)}",
        }


def verify_deployment(
    name: str,
    namespace: str | None = None,
) -> dict[str, Any]:
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
    apps_api = client.AppsV1Api()

    try:
        deployment = apps_api.read_namespaced_deployment(
            name=name,
            namespace=namespace,
        )

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
            "message": (
                "Deployment rollout successful"
                if success
                else "Deployment rollout not complete"
            ),
        }

    except Exception as exc:
        return {
            "success": False,
            "deployment": name,
            "namespace": namespace,
            "message": f"Failed to verify deployment: {str(exc)}",
        }
