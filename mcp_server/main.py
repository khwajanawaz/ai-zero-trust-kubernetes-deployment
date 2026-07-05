import uuid

from fastapi import FastAPI, HTTPException
from temporalio.client import WorkflowHandle

from mcp_server.models import (
    YamlSubmission,
    ApprovalRequest,
    WorkflowStartResponse,
    GithubYamlSubmission,  # NEW: request model for GitHub repo input
)
from mcp_server.temporal_client import get_temporal_client
from mcp_server.config import TEMPORAL_TASK_QUEUE
from mcp_server.services.github_service import (
    fetch_github_file_content,  # NEW: reads YAML file from GitHub
)
from temporal_app.workflows import MCPWorkflow

app = FastAPI(title="MCP Server for AI-Driven Kubernetes")


@app.get("/health")
async def health() -> dict:
    """
    Simple health check endpoint.
    Used by UI / monitoring to check if backend is alive.
    """
    return {"status": "ok"}


@app.post("/submit-yaml", response_model=WorkflowStartResponse)
async def submit_yaml(payload: YamlSubmission) -> WorkflowStartResponse:
    """
    Manual YAML submission endpoint.

    Flow:
    UI sends raw YAML text
    -> backend starts Temporal workflow
    -> workflow runs validation, AI, OPA, approval, deployment flow
    """
    try:
        client = await get_temporal_client()

        # Create unique workflow id for this submission
        workflow_id = f"mcp-workflow-{uuid.uuid4()}"

        # Start Temporal workflow with the YAML content directly
        await client.start_workflow(
            MCPWorkflow.run,
            payload.yaml_content,
            id=workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
        )

        return WorkflowStartResponse(
            workflow_id=workflow_id,
            message="Workflow started from manual YAML input. Review validation, AI, and policy results before approval.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/submit-github-yaml", response_model=WorkflowStartResponse)
async def submit_github_yaml(payload: GithubYamlSubmission) -> WorkflowStartResponse:
    """
    GitHub YAML submission endpoint.

    Flow:
    UI sends repo details
    -> backend reads YAML file from GitHub
    -> backend starts the same Temporal workflow using the fetched YAML text

    Works for:
    - public GitHub repos (token optional)
    - private GitHub repos (token required)
    """
    try:
        client = await get_temporal_client()

        # Create unique workflow id
        workflow_id = f"mcp-workflow-{uuid.uuid4()}"

        # Read file content from GitHub repository
        yaml_content = fetch_github_file_content(
            repo_owner=payload.repo_owner,
            repo_name=payload.repo_name,
            branch=payload.branch,
            file_path=payload.file_path,
            github_token=payload.github_token,
        )

        # Start the same MCP workflow with the fetched YAML
        await client.start_workflow(
            MCPWorkflow.run,
            yaml_content,
            id=workflow_id,
            task_queue=TEMPORAL_TASK_QUEUE,
        )

        return WorkflowStartResponse(
            workflow_id=workflow_id,
            message="GitHub YAML fetched successfully and workflow started.",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/approve")
async def approve(payload: ApprovalRequest) -> dict:
    """
    Approval endpoint.

    Flow:
    UI sends workflow_id + approved true/false
    -> backend sends approval signal to running Temporal workflow
    """
    try:
        client = await get_temporal_client()

        # Get handle to existing workflow
        handle: WorkflowHandle = client.get_workflow_handle(payload.workflow_id)

        # Send approval/denial signal
        await handle.signal(MCPWorkflow.approve, payload.approved)

        return {
            "workflow_id": payload.workflow_id,
            "approved": payload.approved,
            "message": "Approval signal sent",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/workflow/{workflow_id}")
async def get_workflow_result(workflow_id: str) -> dict:
    """
    Main workflow details endpoint.

    This is the most important endpoint for the UI.

    UI should call this endpoint to show:
    - workflow overall status
    - final status
    - stage-by-stage progress
    - validation / AI / OPA / approval / deployment results

    We convert internal workflow state into a cleaner 'stages' list
    so the frontend can show it in order.
    """
    try:
        client = await get_temporal_client()

        # Get workflow handle and workflow runtime description
        handle: WorkflowHandle = client.get_workflow_handle(workflow_id)
        description = await handle.describe()

        result = None
        error = None

        # Query live workflow state from Temporal workflow query method
        try:
            result = await handle.query(MCPWorkflow.get_status)
        except Exception as exc:
            error = f"Unable to query workflow state: {str(exc)}"

        # If workflow result cannot be queried, return basic response
        if result is None:
            return {
                "workflow_id": workflow_id,
                "status": description.status.name,
                "final_status": None,
                "manifest": None,
                "stages": [],
                "error": error,
            }

        # Build ordered stage list for frontend/UI readability
        # This lets UI show:
        # Validation -> AI -> OPA -> Approval -> Deployment
        stages = [
            {
                "step": 1,
                "name": "validation",
                "status": result.get("validation", {}).get("status"),
                "details": {
                    "errors": result.get("validation", {}).get("errors")
                },
            },
            {
                "step": 2,
                "name": "ai_analysis",
                "status": result.get("summary", {}).get("ai"),
                "details": result.get("ai", {}).get("result"),
            },
            {
                "step": 3,
                "name": "opa_policy_check",
                "status": result.get("summary", {}).get("opa"),
                "details": result.get("policy", {}).get("result"),
            },
            {
                "step": 4,
                "name": "approval",
                "status": result.get("summary", {}).get("approval"),
                "details": result.get("approval"),
            },
            {
                "step": 5,
                "name": "deployment",
                "status": result.get("summary", {}).get("deployment"),
                "details": result.get("deployment", {}).get("result"),
            },
        ]

        return {
            "workflow_id": workflow_id,
            "status": description.status.name,
            "final_status": result.get("decision", {}).get("final_status"),
            "manifest": result.get("manifest"),
            "stages": stages,
            # raw_result is useful while developing/debugging
            # You can remove it later in production UI if you want cleaner response
            "raw_result": result,
            "error": error,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))