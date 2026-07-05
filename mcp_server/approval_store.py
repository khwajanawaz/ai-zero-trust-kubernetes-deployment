from typing import Dict, Optional
from threading import Lock


class ApprovalStore:
    def __init__(self) -> None:
        self._store: Dict[str, bool] = {}
        self._lock = Lock()

    def set_decision(self, workflow_id: str, approved: bool) -> None:
        with self._lock:
            self._store[workflow_id] = approved

    def get_decision(self, workflow_id: str) -> Optional[bool]:
        with self._lock:
            return self._store.get(workflow_id)

    def delete_decision(self, workflow_id: str) -> None:
        with self._lock:
            self._store.pop(workflow_id, None)


approval_store = ApprovalStore()