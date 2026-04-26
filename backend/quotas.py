import datetime
import json
import os
from pathlib import Path

from pydantic import BaseModel

QUOTAS_FILE = Path(
    os.path.expanduser("~/.config/runner-dashboard/principal-spend.json")
)


class SpendRecord(BaseModel):
    principal_id: str
    date: str  # YYYY-MM-DD
    spend_usd: float


class QuotaManager:
    def __init__(self, path: Path = QUOTAS_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[SpendRecord]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text())
            return [SpendRecord(**record) for record in data]
        except Exception:
            return []

    def _save(self, records: list[SpendRecord]):
        self.path.write_text(json.dumps([r.model_dump() for r in records]))

    def get_today_spend(self, principal_id: str) -> float:
        today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        records = self._load()
        spend = sum(
            r.spend_usd
            for r in records
            if r.principal_id == principal_id and r.date == today
        )
        return spend

    def record_spend(self, principal_id: str, amount_usd: float):
        today = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
        records = self._load()
        # Keep only last 7 days to avoid unbounded growth
        cutoff = (
            datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7)
        ).strftime("%Y-%m-%d")
        records = [r for r in records if r.date >= cutoff]

        found = False
        for r in records:
            if r.principal_id == principal_id and r.date == today:
                r.spend_usd += amount_usd
                found = True
                break

        if not found:
            records.append(
                SpendRecord(principal_id=principal_id, date=today, spend_usd=amount_usd)
            )

        self._save(records)


quota_manager = QuotaManager()
