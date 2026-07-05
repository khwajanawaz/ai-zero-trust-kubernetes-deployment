from typing import Any
import yaml


class ManifestValidationError(Exception):
    """Raised when one or more blocking manifest validation issues are found."""

    def __init__(self, issues: list[str]) -> None:
        self.issues = issues
        super().__init__("\n".join(issues))


def parse_yaml_documents(yaml_content: str) -> list[dict[str, Any]]:
    """
    Parse one or more YAML documents from a string.

    Returns:
        A list of Kubernetes manifest dictionaries.

    Raises:
        ManifestValidationError:
            - if YAML is empty
            - if YAML syntax is invalid
            - if any document is empty or not a YAML object
    """
    issues: list[str] = []

    if not yaml_content or not yaml_content.strip():
        raise ManifestValidationError(["YAML is empty"])

    try:
        documents = list(yaml.safe_load_all(yaml_content))
    except yaml.YAMLError as exc:
        raise ManifestValidationError([f"Invalid YAML syntax: {str(exc)}"]) from exc

    if not documents:
        raise ManifestValidationError(["YAML is empty"])

    parsed_documents: list[dict[str, Any]] = []

    for index, doc in enumerate(documents, start=1):
        if doc is None:
            issues.append(f"Document {index}: YAML document is empty")
            continue

        if not isinstance(doc, dict):
            issues.append(
                f"Document {index}: YAML must represent a Kubernetes object"
            )
            continue

        parsed_documents.append(doc)

    if issues:
        raise ManifestValidationError(issues)

    return parsed_documents


def parse_yaml(yaml_content: str) -> dict[str, Any]:
    """
    Backward-compatible helper for single-document YAML only.

    Raises:
        ManifestValidationError if there is not exactly one YAML document.
    """
    documents = parse_yaml_documents(yaml_content)

    if len(documents) != 1:
        raise ManifestValidationError(
            [f"Expected exactly 1 YAML document, but found {len(documents)}"]
        )

    return documents[0]


def normalize_manifest_formatting(manifest: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize YAML formatting only.

    Important:
        This does NOT change Kubernetes meaning and does NOT auto-fix
        spec or security logic. It only normalizes formatting.
    """
    return yaml.safe_load(
        yaml.safe_dump(
            manifest,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
        )
    )


def normalize_yaml_documents(
    documents: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Apply formatting-only normalization to all manifest documents."""
    return [normalize_manifest_formatting(doc) for doc in documents]


def format_yaml_documents(documents: list[dict[str, Any]]) -> str:
    """
    Convert normalized manifest documents back into clean YAML text.
    Useful for showing corrected YAML in the UI.
    """
    return yaml.safe_dump_all(
        documents,
        sort_keys=False,
        default_flow_style=False,
        allow_unicode=True,
    )


def basic_validate_manifest(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Level 1 validation:
    Basic YAML / Kubernetes object structure.

    These are BLOCKING issues.
    """
    issues: list[str] = []
    prefix = f"Document {document_index}: " if document_index is not None else ""

    required_fields = ["apiVersion", "kind", "metadata"]
    for field in required_fields:
        if field not in manifest:
            issues.append(f"{prefix}Manifest missing required field: {field}")

    metadata = manifest.get("metadata")
    if metadata is None:
        issues.append(f"{prefix}metadata is required")
        return issues

    if not isinstance(metadata, dict):
        issues.append(f"{prefix}metadata must be an object")
        return issues

    if not metadata.get("name"):
        issues.append(f"{prefix}metadata.name is required")

    return issues


def kubernetes_validate_manifest(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Level 2 validation:
    Kubernetes object correctness.

    These are BLOCKING issues because the object is incomplete or malformed.
    """
    issues: list[str] = []
    prefix = f"Document {document_index}: " if document_index is not None else ""

    kind = manifest.get("kind")
    raw_spec = manifest.get("spec", {})

    if raw_spec is not None and not isinstance(raw_spec, dict):
        issues.append(f"{prefix}spec must be an object")
        raw_spec = {}

    spec: dict[str, Any] = raw_spec if isinstance(raw_spec, dict) else {}

    # -------------------------
    # Pod validation
    # -------------------------
    if kind == "Pod":
        if not spec:
            issues.append(f"{prefix}Pod must include spec")

        containers = spec.get("containers")
        if not containers or not isinstance(containers, list):
            issues.append(
                f"{prefix}Pod must include at least one container in spec.containers"
            )
            containers = []

        for i, container in enumerate(containers):
            if not isinstance(container, dict):
                issues.append(f"{prefix}Pod container at index {i} must be an object")
                continue

            if not container.get("name"):
                issues.append(f"{prefix}Pod container at index {i} must have name")
            if not container.get("image"):
                issues.append(
                    f"{prefix}Pod container '{container.get('name', i)}' must have image"
                )

    # -------------------------
    # Deployment validation
    # -------------------------
    elif kind == "Deployment":
        if not spec:
            issues.append(f"{prefix}Deployment must include spec")

        selector = spec.get("selector", {})
        template = spec.get("template", {})

        if selector and not isinstance(selector, dict):
            issues.append(f"{prefix}Deployment spec.selector must be an object")
            selector = {}
        elif not isinstance(selector, dict):
            selector = {}

        if template and not isinstance(template, dict):
            issues.append(f"{prefix}Deployment spec.template must be an object")
            template = {}
        elif not isinstance(template, dict):
            template = {}

        template_metadata = template.get("metadata", {})
        template_spec = template.get("spec", {})

        if template_metadata and not isinstance(template_metadata, dict):
            issues.append(
                f"{prefix}Deployment spec.template.metadata must be an object"
            )
            template_metadata = {}
        elif not isinstance(template_metadata, dict):
            template_metadata = {}

        if template_spec and not isinstance(template_spec, dict):
            issues.append(f"{prefix}Deployment spec.template.spec must be an object")
            template_spec = {}
        elif not isinstance(template_spec, dict):
            template_spec = {}

        containers = template_spec.get("containers")
        if not containers or not isinstance(containers, list):
            issues.append(
                f"{prefix}Deployment must include at least one container in "
                f"spec.template.spec.containers"
            )
            containers = []

        if "selector" not in spec:
            issues.append(f"{prefix}Deployment must include spec.selector")
        elif "matchLabels" not in selector:
            issues.append(f"{prefix}Deployment spec.selector must include matchLabels")

        if "template" not in spec:
            issues.append(f"{prefix}Deployment must include spec.template")

        if "metadata" not in template:
            issues.append(f"{prefix}Deployment spec.template.metadata is required")

        if "labels" not in template_metadata:
            issues.append(f"{prefix}Deployment spec.template.metadata.labels is required")

        if "spec" not in template:
            issues.append(f"{prefix}Deployment spec.template.spec is required")

        for i, container in enumerate(containers):
            if not isinstance(container, dict):
                issues.append(
                    f"{prefix}Deployment container at index {i} must be an object"
                )
                continue

            if not container.get("name"):
                issues.append(
                    f"{prefix}Deployment container at index {i} must have name"
                )
            if not container.get("image"):
                issues.append(
                    f"{prefix}Deployment container '{container.get('name', i)}' must have image"
                )

    # -------------------------
    # Service validation
    # -------------------------
    elif kind == "Service":
        if not spec:
            issues.append(f"{prefix}Service must include spec")

        ports = spec.get("ports")
        if not ports or not isinstance(ports, list):
            issues.append(f"{prefix}Service must include spec.ports")
            ports = []
        else:
            for i, port in enumerate(ports):
                if not isinstance(port, dict):
                    issues.append(f"{prefix}Service port at index {i} must be an object")
                    continue
                if "port" not in port:
                    issues.append(
                        f"{prefix}Service port at index {i} must include 'port'"
                    )

        selector = spec.get("selector")
        if not selector:
            issues.append(f"{prefix}Service must include spec.selector")
        elif not isinstance(selector, dict):
            issues.append(f"{prefix}Service spec.selector must be an object")

    # -------------------------
    # ConfigMap validation
    # -------------------------
    elif kind == "ConfigMap":
        pass

    return issues


def security_validate_manifest(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Level 3 validation:
    Blocking security/shape checks only.

    Important:
    - ':latest' is NOT checked here; OPA handles that.
    - Missing runAsNonRoot / requests / limits are NOT blocking anymore.
      They are now warnings, not hard validation failures.
    """
    issues: list[str] = []
    prefix = f"Document {document_index}: " if document_index is not None else ""

    kind = manifest.get("kind")
    containers: list[dict[str, Any]] = []

    if kind == "Pod":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            raw_containers = raw_spec.get("containers", [])
            if isinstance(raw_containers, list):
                containers = raw_containers

    elif kind == "Deployment":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            raw_template = raw_spec.get("template", {})
            if isinstance(raw_template, dict):
                raw_template_spec = raw_template.get("spec", {})
                if isinstance(raw_template_spec, dict):
                    raw_containers = raw_template_spec.get("containers", [])
                    if isinstance(raw_containers, list):
                        containers = raw_containers

    for i, container in enumerate(containers):
        if not isinstance(container, dict):
            issues.append(f"{prefix}Container at index {i} must be an object")
            continue

        name = container.get("name", f"index-{i}")

        # securityContext must be an object if present
        security_context = container.get("securityContext", {})
        if security_context and not isinstance(security_context, dict):
            issues.append(
                f"{prefix}Container '{name}' securityContext must be an object"
            )
            security_context = {}
        elif not isinstance(security_context, dict):
            security_context = {}

        # privileged=true is still a hard stop
        if security_context.get("privileged") is True:
            issues.append(
                f"{prefix}Container '{name}' is privileged, which is not allowed"
            )

        # resources must be an object if present
        resources = container.get("resources", {})
        if resources and not isinstance(resources, dict):
            issues.append(f"{prefix}Container '{name}' resources must be an object")
            resources = {}
        elif not isinstance(resources, dict):
            resources = {}

        limits = resources.get("limits", {})
        requests = resources.get("requests", {})

        # If limits/requests exist, they must be objects
        if limits and not isinstance(limits, dict):
            issues.append(
                f"{prefix}Container '{name}' resource limits must be an object"
            )

        if requests and not isinstance(requests, dict):
            issues.append(
                f"{prefix}Container '{name}' resource requests must be an object"
            )

    return issues


def security_warn_manifest(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Security and best-practice warnings.

    These DO NOT block the workflow.
    They are useful for:
    - UI warnings
    - AI context
    - later reporting
    """
    warnings: list[str] = []
    prefix = f"Document {document_index}: " if document_index is not None else ""

    kind = manifest.get("kind")
    containers: list[dict[str, Any]] = []

    if kind == "Pod":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            raw_containers = raw_spec.get("containers", [])
            if isinstance(raw_containers, list):
                containers = raw_containers

    elif kind == "Deployment":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            raw_template = raw_spec.get("template", {})
            if isinstance(raw_template, dict):
                raw_template_spec = raw_template.get("spec", {})
                if isinstance(raw_template_spec, dict):
                    raw_containers = raw_template_spec.get("containers", [])
                    if isinstance(raw_containers, list):
                        containers = raw_containers

    for i, container in enumerate(containers):
        if not isinstance(container, dict):
            continue

        name = container.get("name", f"index-{i}")

        security_context = container.get("securityContext", {})
        if not isinstance(security_context, dict):
            security_context = {}

        resources = container.get("resources", {})
        if not isinstance(resources, dict):
            resources = {}

        limits = resources.get("limits", {})
        requests = resources.get("requests", {})

        # Best-practice warning only
        if security_context.get("runAsNonRoot") is not True:
            warnings.append(
                f"{prefix}Container '{name}' should set securityContext.runAsNonRoot=true"
            )

        # Best-practice warning only
        if not limits:
            warnings.append(f"{prefix}Container '{name}' should define resource limits")
        elif isinstance(limits, dict):
            if "cpu" not in limits or "memory" not in limits:
                warnings.append(
                    f"{prefix}Container '{name}' should define cpu and memory in resource limits"
                )

        # Best-practice warning only
        if not requests:
            warnings.append(
                f"{prefix}Container '{name}' should define resource requests"
            )
        elif isinstance(requests, dict):
            if "cpu" not in requests or "memory" not in requests:
                warnings.append(
                    f"{prefix}Container '{name}' should define cpu and memory in resource requests"
                )

    # Pod-level best-practice warnings
    pod_spec: dict[str, Any] = {}

    if kind == "Pod":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            pod_spec = raw_spec

    elif kind == "Deployment":
        raw_spec = manifest.get("spec", {})
        if isinstance(raw_spec, dict):
            raw_template = raw_spec.get("template", {})
            if isinstance(raw_template, dict):
                raw_template_spec = raw_template.get("spec", {})
                if isinstance(raw_template_spec, dict):
                    pod_spec = raw_template_spec

    if pod_spec.get("hostNetwork") is True:
        warnings.append(f"{prefix}hostNetwork=true is discouraged")

    if pod_spec.get("hostPID") is True:
        warnings.append(f"{prefix}hostPID=true is discouraged")

    return warnings


def validate_manifest(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Run all BLOCKING validation levels for one manifest and return issues.
    """
    issues: list[str] = []
    issues.extend(basic_validate_manifest(manifest, document_index))
    issues.extend(kubernetes_validate_manifest(manifest, document_index))
    issues.extend(security_validate_manifest(manifest, document_index))
    return issues


def collect_manifest_warnings(
    manifest: dict[str, Any], document_index: int | None = None
) -> list[str]:
    """
    Collect non-blocking warnings for one manifest.
    """
    warnings: list[str] = []
    warnings.extend(security_warn_manifest(manifest, document_index))
    return warnings


def validate_manifest_or_raise(
    manifest: dict[str, Any], document_index: int | None = None
) -> None:
    """
    Raise ManifestValidationError if any BLOCKING validation issue exists.
    """
    issues = validate_manifest(manifest, document_index)
    if issues:
        raise ManifestValidationError(issues)


def validate_yaml_documents(yaml_content: str) -> list[dict[str, Any]]:
    """
    Parse and validate one or more YAML documents.

    Returns:
        Parsed manifest documents if valid.

    Raises:
        ManifestValidationError: if any blocking validation issue exists.
    """
    documents = parse_yaml_documents(yaml_content)

    all_issues: list[str] = []
    for index, manifest in enumerate(documents, start=1):
        all_issues.extend(validate_manifest(manifest, index))

    if all_issues:
        raise ManifestValidationError(all_issues)

    return documents


def collect_yaml_warnings(yaml_content: str) -> list[str]:
    """
    Parse YAML and collect non-blocking warnings.

    This is optional helper logic you can use later in:
    - workflow state
    - UI
    - AI context
    """
    documents = parse_yaml_documents(yaml_content)

    all_warnings: list[str] = []
    for index, manifest in enumerate(documents, start=1):
        all_warnings.extend(collect_manifest_warnings(manifest, index))

    return all_warnings


def validate_and_normalize_yaml_documents(
    yaml_content: str,
) -> tuple[list[dict[str, Any]], str | None, bool, str]:
    """
    Parse, normalize formatting only, validate, and return:

    Returns:
        1. normalized documents
        2. corrected YAML only if formatting changed, otherwise None
        3. format_changed (True/False)
        4. user-friendly message

    Raises:
        ManifestValidationError: if any blocking validation issue exists.
    """
    documents = parse_yaml_documents(yaml_content)
    normalized_documents = normalize_yaml_documents(documents)

    all_issues: list[str] = []
    for index, manifest in enumerate(normalized_documents, start=1):
        all_issues.extend(validate_manifest(manifest, index))

    if all_issues:
        raise ManifestValidationError(all_issues)

    corrected_yaml = format_yaml_documents(normalized_documents)

    original_clean = yaml_content.strip()
    corrected_clean = corrected_yaml.strip()
    format_changed = original_clean != corrected_clean

    if format_changed:
        message = "YAML formatting was corrected"
    else:
        corrected_yaml = None
        message = "YAML is already well formatted"

    return normalized_documents, corrected_yaml, format_changed, message