import logging
import time
from app.models.context import ExecutionContext, LogLevel
from app.plugins.plugin_registry import PluginRegistry

logger = logging.getLogger(__name__)


class TransformationEngine:
    """Orchestrates the universal transformation pipeline."""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry

    def execute_pipeline(self, context: ExecutionContext) -> None:
        """Run all enabled plugins on the context."""
        start = time.time()

        if context.current_data is None or context.current_data.empty:
            context.add_warning(LogLevel.ERROR, "No data loaded into context.")
            return

        context.statistics.rows_read = len(context.current_data)

        # Remove completely empty rows
        before = len(context.current_data)
        context.current_data = context.current_data.dropna(how="all")
        empty_removed = before - len(context.current_data)
        if empty_removed:
            context.statistics.rows_removed += empty_removed
            context.add_warning(LogLevel.INFO, f"Removed {empty_removed} empty rows.")

        # Discover and load enabled plugins
        self.registry.discover_plugins()
        plugins = self.registry.load_enabled_plugins(context)

        logger.info("Running pipeline with %d plugins: %s", len(plugins), [p.NAME for p in plugins])

        for plugin in plugins:
            try:
                logger.info("Executing plugin: %s v%s", plugin.NAME, plugin.VERSION)
                plugin.execute(context)
            except Exception as exc:
                context.add_warning(
                    LogLevel.CRITICAL,
                    f"Plugin '{plugin.NAME}' failed: {exc}",
                )
                logger.exception("Plugin %s failed.", plugin.NAME)

        context.statistics.rows_processed = len(context.current_data) if context.current_data is not None else 0
        elapsed = (time.time() - start) * 1000
        context.statistics.execution_time_ms = round(elapsed, 2)
        logger.info("Pipeline completed in %.2f ms.", elapsed)
