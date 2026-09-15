from typing import Dict, Any, List
from deepcore.runtime.tools.registry import ToolRegistry
from deepcore.runtime.skills.registry import SkillRegistry
from deepcore.runtime.execution.registry import ExecutionRegistry

class KernelHealthReport:
    """
    Developer diagnostics tool that provides a health summary of the
    currently initialized DeepCore execution kernel.
    """
    def __init__(
        self,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry,
        execution_registry: ExecutionRegistry
    ):
        self.tool_registry = tool_registry
        self.skill_registry = skill_registry
        self.execution_registry = execution_registry
        self.version = "0.1.0"

    def get_summary(self) -> Dict[str, Any]:
        """Gathers diagnostic statistics and configuration details of the kernel."""
        # 1. Registered Tools
        tools_list = []
        for desc in self.tool_registry.list_tools():
            tools_list.append({
                "name": desc.name,
                "description": desc.description,
                "capabilities": [c.name for c in desc.capabilities]
            })

        # 2. Registered Skills
        skills_list = []
        for desc in self.skill_registry.list_skills():
            skills_list.append({
                "name": desc.name,
                "description": desc.description
            })

        # 3. Registered Executables
        executables_list = []
        for desc in self.execution_registry.list_descriptors():
            executables_list.append({
                "name": desc.name,
                "description": desc.description
            })

        return {
            "kernel_version": self.version,
            "runtimes": {
                "tool_runtime": "Initialized",
                "skill_runtime": "Initialized",
                "execution_runtime": "Initialized",
                "planner_runtime": "Initialized"
            },
            "registered_tools": tools_list,
            "registered_skills": skills_list,
            "registered_executables": executables_list
        }

    def generate_report_markdown(self) -> str:
        """Formats the diagnostics report as a markdown string for developers."""
        summary = self.get_summary()
        
        md = []
        md.append(f"# DeepCore Kernel Health Report (v{summary['kernel_version']})")
        md.append("")
        
        md.append("## Registered Runtimes")
        for r_name, status in summary["runtimes"].items():
            md.append(f"- **{r_name}**: `{status}`")
        md.append("")

        md.append("## Registered Tools")
        if not summary["registered_tools"]:
            md.append("No tools registered.")
        for tool in summary["registered_tools"]:
            caps = ", ".join(tool["capabilities"])
            md.append(f"- **{tool['name']}**: {tool['description']} (Capabilities: `[{caps}]`)")
        md.append("")

        md.append("## Registered Skills")
        if not summary["registered_skills"]:
            md.append("No skills registered.")
        for skill in summary["registered_skills"]:
            md.append(f"- **{skill['name']}**: {skill['description']}")
        md.append("")

        md.append("## Registered Executables")
        if not summary["registered_executables"]:
            md.append("No generic executables registered.")
        for exe in summary["registered_executables"]:
            md.append(f"- **{exe['name']}**: {exe['description']}")
            
        return "\n".join(md)
