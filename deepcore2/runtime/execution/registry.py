from typing import Dict, List, Optional, Any
from deepcore2.runtime.execution.base import ExecutionDescriptor
from deepcore2.runtime.execution.exceptions import ExecutableNotFoundError

class ExecutionRegistry:
    """
    Registry for all Executables (Skills, Workflows, Macros, Composite Tools, etc.)
    within the DeepCore execution runtime.
    """
    def __init__(self):
        self._executables: Dict[str, Any] = {}

    def register(self, name: str, executable: Any) -> None:
        """Register a generic executable target."""
        if name in self._executables:
            raise ValueError(f"Executable '{name}' is already registered.")
        self._executables[name] = executable

    def unregister(self, name: str) -> None:
        """Unregister an executable target."""
        if name not in self._executables:
            raise ExecutableNotFoundError(f"Executable '{name}' is not registered.")
        del self._executables[name]

    def get(self, name: str) -> Optional[Any]:
        """Resolve and return the executable target by name."""
        return self._executables.get(name)

    def list_descriptors(self) -> List[ExecutionDescriptor]:
        """List descriptors for all registered executables, normalized to ExecutionDescriptor."""
        descriptors = []
        for name, exe in self._executables.items():
            if hasattr(exe, "get_descriptor"):
                desc = exe.get_descriptor()
                
                # Extract capabilities cleanly if they exist
                capabilities_mapped = []
                capabilities = getattr(desc, "capabilities", [])
                for cap in capabilities:
                    if hasattr(cap, "value"):
                        capabilities_mapped.append(str(cap.value))
                    else:
                        capabilities_mapped.append(str(cap))
                
                input_schema = getattr(desc, "input_schema", {})
                if hasattr(input_schema, "model_json_schema"):
                    input_schema = input_schema.model_json_schema()
                elif hasattr(input_schema, "schema"):
                    input_schema = input_schema.schema()
                elif isinstance(input_schema, type):
                    input_schema = {}

                output_schema = getattr(desc, "output_schema", {})
                if hasattr(output_schema, "model_json_schema"):
                    output_schema = output_schema.model_json_schema()
                elif hasattr(output_schema, "schema"):
                    output_schema = output_schema.schema()
                elif isinstance(output_schema, type):
                    output_schema = {}

                descriptors.append(ExecutionDescriptor(
                    name=getattr(desc, "name", name),
                    description=getattr(desc, "description", ""),
                    input_schema=input_schema,
                    output_schema=output_schema,
                    capabilities=capabilities_mapped,
                    examples=getattr(desc, "examples", [])
                ))
        return descriptors
