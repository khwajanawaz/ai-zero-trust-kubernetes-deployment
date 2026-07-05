from temporalio.client import Client
from mcp_server.config import TEMPORAL_HOST

# Global client instance (reuse connection)
_temporal_client: Client | None = None


async def get_temporal_client() -> Client:
    """
    Get or create a Temporal client connection.

    - Reuses existing connection (better performance)
    - Handles connection errors clearly
    """

    global _temporal_client

    if _temporal_client is not None:
        return _temporal_client

    try:
        _temporal_client = await Client.connect(TEMPORAL_HOST)
        return _temporal_client

    except Exception as e:
        raise RuntimeError(
            f"❌ Failed to connect to Temporal at {TEMPORAL_HOST}. "
            f"Make sure Temporal server is running.\nError: {str(e)}"
        )
    
    