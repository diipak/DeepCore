"""
deepcore.runtime.stubs

Canonical stub implementations of BaseTool and BaseSkill used by the
Capability Discovery bootstrap registration and in tests.

These are NOT test-only fixtures. They are representative capability
implementations that demonstrate and exercise the runtime contracts.
They live here so that production code (e.g., capabilities.py) can
import them without pulling in the test package.
"""

from deepcore.runtime.stubs.tools import (
    EchoTool,
    RegistrySearchMockTool,
)
from deepcore.runtime.stubs.skills import (
    EchoSkill,
    RegistrySearchEchoSkill,
)

__all__ = [
    "EchoTool",
    "RegistrySearchMockTool",
    "EchoSkill",
    "RegistrySearchEchoSkill",
]
