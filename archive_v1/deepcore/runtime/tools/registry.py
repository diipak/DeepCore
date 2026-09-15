from typing import Dict, List, Optional
from deepcore.runtime.tools.base import BaseTool, ToolDescriptor
from deepcore.runtime.tools.exceptions import ToolNotFoundError

class ToolRegistry:
    def __init__(self):
        self._registry: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._registry:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._registry[tool.name] = tool

    def unregister(self, name: str) -> None:
        if name not in self._registry:
            raise ToolNotFoundError(f"Tool '{name}' is not registered.")
        del self._registry[name]

    def get(self, name: str) -> Optional[BaseTool]:
        return self._registry.get(name)

    def list_tools(self) -> List[ToolDescriptor]:
        return [tool.get_descriptor() for tool in self._registry.values()]


class ExecutionRegistry:
    """
    Lightweight resolution layer for executable handlers.
    Prepares the platform for Composite Tools, Macros, Workflows,
    and future runtime extensions without modifying Tool Runtime.
    """
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry

    def resolve(self, name: str) -> BaseTool:
        """
        Resolve an executable handler (e.g. a Tool) by name.
        Raises ToolNotFoundError if no handler exists.
        """
        tool = self.tool_registry.get(name)
        if not tool:
            raise ToolNotFoundError(f"Executable handler '{name}' not found in registry.")
        return tool
