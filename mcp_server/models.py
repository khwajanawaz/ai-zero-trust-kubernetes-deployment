from typing import Any, Optional, List
from pydantic import BaseModel, Field


# ================================
# 1. INPUT MODELS
# ================================

class YamlSubmission(BaseModel):
    """
    Used when user pastes YAML manually in UI
    """
    yaml_content: str = Field(
        ..., min_length=1, description="Raw Kubernetes YAML manifest"
    )


class GithubYamlSubmission(BaseModel):
    """
    Used when user selects GitHub repo instead of pasting YAML
    """
    repo_owner: str
    repo_name: str
    branch: str
    file_path: str
    github_token: Optional[str] = None  # required only for private repos


class ApprovalRequest(BaseModel):
    """
    Used when user clicks Approve / Deny in UI
    """
    workflow_id: str = Field(..., min_length=1)
    approved: bool


class WorkflowStartResponse(BaseModel):
    """
    Response when workflow starts
    """
    workflow_id: str
    message: str


# ================================
# 2. STAGE RESULT MODELS
# ================================

class ValidationResult(BaseModel):
    """
    Validation stage output
    """
    status: str  # passed / failed
    errors: Optional[List[str]] = None


class AIAnalysisResult(BaseModel):
    """
    AI stage output
    """
    risk_level: str
    recommendation: str
    reason: str
    suggested_fixes: List[str] = Field(default_factory=list)


class OPAEvaluationResult(BaseModel):
    """
    OPA policy check output
    """
    allow: bool
    violations: List[str] = Field(default_factory=list)


class ApprovalResult(BaseModel):
    """
    Approval stage state
    """
    required: bool
    status: str  # waiting / approved / denied / not_required


class DeploymentResult(BaseModel):
    """
    Deployment (or future GitOps commit) result
    """
    success: bool
    message: Optional[str] = None
    name: Optional[str] = None
    namespace: Optional[str] = None


# ================================
# 3. STAGE (UI FRIENDLY)
# ================================

class Stage(BaseModel):
    """
    This is what UI will use to render steps in order
    """
    step: int
    name: str
    status: str
    details: Optional[Any] = None


# ================================
# 4. FINAL RESPONSE MODEL (MAIN)
# ================================

class WorkflowStatusResponse(BaseModel):
    """
    Main response for UI

    This matches your /workflow/{workflow_id} API
    """

    workflow_id: str
    status: str  # Temporal status: RUNNING / COMPLETED

    final_status: Optional[str] = None

    manifest: Optional[dict[str, Any]] = None

    # Ordered stage-by-stage results (UI uses this)
    stages: List[Stage] = Field(default_factory=list)

    # Full raw data (debugging / advanced UI)
    raw_result: Optional[dict[str, Any]] = None

    error: Optional[str] = None