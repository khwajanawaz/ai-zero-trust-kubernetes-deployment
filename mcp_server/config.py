import os
from dotenv import load_dotenv

load_dotenv()

# Temporal
TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
TEMPORAL_TASK_QUEUE = os.getenv("TEMPORAL_TASK_QUEUE", "mcp-task-queue")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# OPA
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181/v1/data/kubernetes/admission")

# Kubernetes
KUBECONFIG_PATH = os.getenv("KUBECONFIG_PATH", "")
K8S_NAMESPACE = os.getenv("K8S_NAMESPACE", "default")


K8S_MOCK_MODE = os.getenv("K8S_MOCK_MODE", "true").lower() == "true"