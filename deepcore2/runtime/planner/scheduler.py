import re
from typing import List, Dict, Any
from deepcore2.runtime.planner.base import ExecutionStep, ExecutionPlan
from deepcore2.runtime.planner.exceptions import PlannerDependencyError

# Matches step.<step_id> or steps.<step_id>
REF_PATTERN = r"(?:steps|step)\.([a-zA-Z0-9_-]+)"

def get_step_dependencies(step: ExecutionStep) -> List[str]:
    """
    Inspects a step's inputs and conditions to determine which step IDs
    it depends on.
    """
    dependencies = set()

    def find_deps_in_value(val: Any):
        if isinstance(val, str):
            matches = re.findall(REF_PATTERN, val)
            for m in matches:
                dependencies.add(m)
        elif isinstance(val, dict):
            for v in val.values():
                find_deps_in_value(v)
        elif isinstance(val, list):
            for item in val:
                find_deps_in_value(item)

    # 1. Inspect inputs
    find_deps_in_value(step.inputs)
    
    # 2. Inspect condition expressions
    for cond in step.conditions:
        matches = re.findall(REF_PATTERN, cond.expression)
        for m in matches:
            dependencies.add(m)

    return list(dependencies)


class PlannerScheduler:
    """
    Scheduler providing deterministic topological sorting and cycle detection.
    """
    @staticmethod
    def get_execution_order(plan: ExecutionPlan) -> List[ExecutionStep]:
        """
        Sort plan steps topologically.
        Raises PlannerDependencyError if circular dependencies or missing steps are found.
        """
        steps = plan.steps
        step_map = {s.step_id: s for s in steps}
        
        adj: Dict[str, List[str]] = {s.step_id: [] for s in steps}
        in_degree: Dict[str, int] = {s.step_id: 0 for s in steps}
        
        for step in steps:
            deps = get_step_dependencies(step)
            for dep in deps:
                if dep in step_map:
                    # dep must execute before step: dep -> step
                    adj[dep].append(step.step_id)
                    in_degree[step.step_id] += 1
                else:
                    raise PlannerDependencyError(
                        f"Step '{step.step_id}' depends on non-existent step '{dep}'."
                    )
        
        # Kahn's algorithm
        queue = [step_id for step_id, deg in in_degree.items() if deg == 0]
        queue.sort()  # Maintain deterministic tie-breaker sorting
        
        order = []
        while queue:
            u = queue.pop(0)
            order.append(u)
            for v in adj[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
                    
        if len(order) != len(steps):
            raise PlannerDependencyError("Circular dependency detected in execution plan.")
            
        return [step_map[step_id] for step_id in order]
