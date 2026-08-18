from abc import ABC, abstractmethod
from app.models.context import ExecutionContext


class BasePlugin(ABC):
    """Base class for all transformation plugins."""

    NAME: str = "BasePlugin"
    VERSION: str = "1.0"
    DESCRIPTION: str = ""

    @abstractmethod
    def execute(self, context: ExecutionContext) -> None:
        """Execute the plugin logic on the shared ExecutionContext."""
