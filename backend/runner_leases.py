import json
import os
import time
import uuid
from pathlib import Path

from pydantic import BaseModel

LEASES_FILE = Path(os.path.expanduser("~/.config/runner-dashboard/runner-leases.json"))


class RunnerLease(BaseModel):
    id: str
    principal_id: str
    runner_count: int
    acquired_at: float
    expires_at: float


class LeaseManager:
    def __init__(self, path: Path = LEASES_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[RunnerLease]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
            return [RunnerLease(**lease) for lease in data]
        except Exception:
            return []

    def _save(self, leases: list[RunnerLease]):
        self.path.write_text(json.dumps([lease.model_dump() for lease in leases]))

    def get_active_leases(self) -> list[RunnerLease]:
        now = time.time()
        leases = self._load()
        active = [lease for lease in leases if lease.expires_at > now]
        if len(active) != len(leases):
            self._save(active)
        return active

    def get_principal_leases(self, principal_id: str) -> list[RunnerLease]:
        active = self.get_active_leases()
        return [lease for lease in active if lease.principal_id == principal_id]

    def acquire_lease(
        self, principal_id: str, count: int, duration_seconds: int
    ) -> RunnerLease:
        now = time.time()
        lease = RunnerLease(
            id=uuid.uuid4().hex,
            principal_id=principal_id,
            runner_count=count,
            acquired_at=now,
            expires_at=now + duration_seconds,
        )
        active = self.get_active_leases()
        active.append(lease)
        self._save(active)
        return lease

    def release_lease(self, lease_id: str):
        active = self.get_active_leases()
        active = [lease for lease in active if lease.id != lease_id]
        self._save(active)


lease_manager = LeaseManager()
