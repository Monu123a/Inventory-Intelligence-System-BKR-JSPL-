from abc import ABC, abstractmethod
from typing import Dict, List

class Executor(ABC):
    name: str
    allowed_request_roles: List[str] = ["Admin", "Manager", "Operator"]
    allowed_approve_roles: List[str] = ["Admin"]

    @abstractmethod
    def validate(self, payload: dict) -> None:
        """Raise ValueError on invalid payload"""
        pass

    @abstractmethod
    def lock_entities(self, db, payload: dict) -> None:
        """Perform SELECT ... FOR UPDATE on target entities in a deterministic order"""
        pass

    @abstractmethod
    def before_snapshot(self, db, payload: dict) -> dict:
        """Returns the minimal relevant state before execution"""
        pass

    @abstractmethod
    def compare_snapshot(self, before: dict, current: dict) -> None:
        """Raises SnapshotMismatchError if snapshots differ"""
        pass

    @abstractmethod
    def dry_run(self, db, payload: dict) -> dict:
        """Returns expected changes and side effects without committing"""
        pass

    @abstractmethod
    def execute(self, db, payload: dict, idempotency_key: str) -> dict:
        """Executes the actual logic and returns the result"""
        pass

    @abstractmethod
    def reverse_payload(self, payload: dict, before_snapshot: dict) -> dict:
        """Generates a payload capable of reverting this action"""
        pass

class ExecutorRegistry:
    _executors: Dict[str, Executor] = {}

    @classmethod
    def register(cls, executor: Executor):
        cls._executors[executor.name] = executor

    @classmethod
    def get(cls, name: str) -> Executor:
        if name not in cls._executors:
            raise ValueError(f"Executor '{name}' not found in registry.")
        return cls._executors[name]
