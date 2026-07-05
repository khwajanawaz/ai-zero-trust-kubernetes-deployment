User sends YAML to FastAPI MCP server
↓
MCP server validates YAML
↓
MCP server starts a Temporal workflow
↓
Temporal workflow runs these steps:
   1. validate manifest
   2. fetch cluster context
   3. call AI analysis
   4. call OPA policy check
   5. combine result
   6. wait for human approval
   7. if approved → apply manifest to cluster
↓
MCP API returns workflow id
↓
User later approves or denies using API
↓
Workflow continues and finishes

