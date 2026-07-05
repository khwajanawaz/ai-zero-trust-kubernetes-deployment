import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker, UnsandboxedWorkflowRunner

from mcp_server.config import TEMPORAL_HOST, TEMPORAL_TASK_QUEUE
from temporal_app.workflows import MCPWorkflow
from temporal_app.activities import (
    validate_yaml_activity,
    fetch_cluster_context_activity,
    ai_analysis_activity,
    opa_check_activity,
    apply_manifest_activity,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    client = await Client.connect(TEMPORAL_HOST)

    worker = Worker(
        client,
        task_queue=TEMPORAL_TASK_QUEUE,
        workflows=[MCPWorkflow],
        activities=[
            validate_yaml_activity,
            fetch_cluster_context_activity,
            ai_analysis_activity,
            opa_check_activity,
            apply_manifest_activity,
        ],
        workflow_runner=UnsandboxedWorkflowRunner(),
    )

    logger.info(f"Temporal worker started on task queue: {TEMPORAL_TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())