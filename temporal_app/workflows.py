from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

# These imports are activity functions executed outside the workflow itself.
# We mark them as passed through so Temporal workflow sandbox handles them correctly.
with workflow.unsafe.imports_passed_through():
    from temporal_app.activities import (
        validate_yaml_activity,
        fetch_cluster_context_activity,
        ai_analysis_activity,
        opa_check_activity,
        apply_manifest_activity,
    )


@workflow.defn
class MCPWorkflow:
    def __init__(self) -> None:
        # This will store the human approval signal:
        # None = no decision yet
        # True = approved
        # False = denied
        self.approval_decision: bool | None = None

        # This is the live workflow state returned by get_status().
        # It is structured in the same order as the actual workflow:
        # manifest -> validation -> ai -> policy -> approval -> deployment -> decision
        self.current_state: dict = {
            "manifest": {
                "name": None,
                "kind": None,
            },
            "validation": {
                "status": "pending",
                "errors": None,
            },
            "ai": {
                "result": None,
            },
            "policy": {
                "result": None,
            },
            "approval": {
                "required": True,
                "status": "pending",  # pending / waiting / approved / denied / timeout / not_required
            },
            "deployment": {
                "result": None,
            },
            "decision": {
                "final_status": "started",
            },
            "summary": {
                "validation": "pending",
                "ai": "pending",
                "opa": "pending",
                "approval": "pending",
                "deployment": "pending",
            },
        }

    @workflow.signal
    def approve(self, approved: bool) -> None:
        """
        Signal method called from API to approve or deny the deployment.
        """
        self.approval_decision = approved

    @workflow.query
    def get_status(self) -> dict:
        """
        Query method used by API to read current workflow state
        before completion and after completion.
        """
        return self.current_state

    @workflow.run
    async def run(self, yaml_content: str) -> dict:
        """
        Main workflow execution order:

        1. Validate YAML
        2. Fetch cluster context
        3. Run AI analysis
        4. Run OPA policy check
        5. Wait for human approval
        6. Apply manifest
        """

        # --------------------------------------------------
        # STEP 1: VALIDATE YAML
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "validating_yaml"
        self.current_state["summary"]["validation"] = "running"

        try:
            manifest: dict = await workflow.execute_activity(
                validate_yaml_activity,
                yaml_content,
                start_to_close_timeout=timedelta(seconds=30),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )
        except Exception as exc:
            # Temporal often wraps activity errors.
            # We try to extract the deepest useful error message.
            error_msg = str(exc)

            if hasattr(exc, "cause") and exc.cause:
                error_msg = str(exc.cause)

            # Remove common wrapper prefix if present
            if "YAML validation failed:" in error_msg:
                error_msg = error_msg.split("YAML validation failed:", 1)[1].strip()

            # Remove generic Temporal wrapper text if it is the only thing present
            if "Activity task failed" in error_msg and "|" not in error_msg:
                error_msg = error_msg.replace("Activity task failed", "").strip()

            # Normalize new lines into separators so multiple validation errors split correctly
            normalized_error_msg = error_msg.replace("\r\n", "\n").replace("\n", "|")

            # Split multiple validation errors separated by "|"
            validation_errors = [
                part.strip()
                for part in normalized_error_msg.split("|")
                if part.strip()
            ]

            # Fallback if nothing useful was extracted
            if not validation_errors:
                validation_errors = [error_msg or "Unknown validation error"]

            self.current_state["validation"]["status"] = "failed"
            self.current_state["validation"]["errors"] = validation_errors
            self.current_state["decision"]["final_status"] = "validation_failed"

            self.current_state["summary"]["validation"] = "failed"
            self.current_state["summary"]["ai"] = "not_started"
            self.current_state["summary"]["opa"] = "not_started"
            self.current_state["summary"]["approval"] = "not_required"
            self.current_state["summary"]["deployment"] = "not_started"

            self.current_state["approval"]["required"] = False
            self.current_state["approval"]["status"] = "not_required"

            return self.current_state

        # Validation passed, so store manifest info
        self.current_state["manifest"]["name"] = manifest.get("metadata", {}).get("name")
        self.current_state["manifest"]["kind"] = manifest.get("kind")
        self.current_state["validation"]["status"] = "passed"
        self.current_state["summary"]["validation"] = "passed"

        # --------------------------------------------------
        # STEP 2: FETCH CLUSTER CONTEXT
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "fetching_cluster_context"

        cluster_context: dict = await workflow.execute_activity(
            fetch_cluster_context_activity,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        # --------------------------------------------------
        # STEP 3: RUN AI ANALYSIS
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "running_ai_analysis"
        self.current_state["summary"]["ai"] = "running"

        ai_result: dict = await workflow.execute_activity(
            ai_analysis_activity,
            args=[manifest, cluster_context],
            start_to_close_timeout=timedelta(seconds=90),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        self.current_state["ai"]["result"] = ai_result
        self.current_state["summary"]["ai"] = "completed"

        # --------------------------------------------------
        # STEP 4: RUN OPA POLICY CHECK
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "running_opa_check"
        self.current_state["summary"]["opa"] = "running"

        opa_result: dict = await workflow.execute_activity(
            opa_check_activity,
            manifest,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        self.current_state["policy"]["result"] = opa_result

        # If OPA blocks the manifest, stop here.
        if not opa_result.get("allow", False):
            self.current_state["decision"]["final_status"] = "blocked_by_policy"
            self.current_state["summary"]["opa"] = "blocked"
            self.current_state["summary"]["approval"] = "not_required"
            self.current_state["summary"]["deployment"] = "not_started"

            self.current_state["approval"]["required"] = False
            self.current_state["approval"]["status"] = "not_required"

            return self.current_state

        # OPA passed, so approval is now needed
        self.current_state["summary"]["opa"] = "passed"

        # --------------------------------------------------
        # STEP 5: WAIT FOR HUMAN APPROVAL
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "waiting_for_approval"
        self.current_state["summary"]["approval"] = "waiting"
        self.current_state["summary"]["deployment"] = "waiting_for_approval"
        self.current_state["approval"]["required"] = True
        self.current_state["approval"]["status"] = "waiting"

        try:
            await workflow.wait_condition(
                lambda: self.approval_decision is not None,
                timeout=timedelta(hours=24),
            )
        except TimeoutError:
            self.current_state["decision"]["final_status"] = "approval_timeout"
            self.current_state["summary"]["approval"] = "timeout"
            self.current_state["summary"]["deployment"] = "not_started"
            self.current_state["approval"]["status"] = "timeout"
            return self.current_state

        # User explicitly denied
        if not self.approval_decision:
            self.current_state["decision"]["final_status"] = "denied_by_user"
            self.current_state["summary"]["approval"] = "denied"
            self.current_state["summary"]["deployment"] = "not_started"
            self.current_state["approval"]["status"] = "denied"
            return self.current_state

        # User approved
        self.current_state["approval"]["status"] = "approved"
        self.current_state["summary"]["approval"] = "approved"

        # --------------------------------------------------
        # STEP 6: APPLY MANIFEST
        # --------------------------------------------------
        self.current_state["decision"]["final_status"] = "applying_manifest"
        self.current_state["summary"]["deployment"] = "running"

        apply_result: dict = await workflow.execute_activity(
            apply_manifest_activity,
            manifest,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        self.current_state["deployment"]["result"] = apply_result
        self.current_state["decision"]["final_status"] = "applied"
        self.current_state["summary"]["deployment"] = "completed"

        return self.current_state