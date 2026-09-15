from typing import Dict, List, Optional
from deepcore2.runtime.skills.base import BaseSkill, SkillDescriptor
from deepcore2.runtime.skills.exceptions import SkillNotFoundError

class SkillRegistry:
    def __init__(self):
        self._registry: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill) -> None:
        if skill.name in self._registry:
            raise ValueError(f"Skill '{skill.name}' is already registered.")
        self._registry[skill.name] = skill

    def unregister(self, name: str) -> None:
        if name not in self._registry:
            raise SkillNotFoundError(f"Skill '{name}' is not registered.")
        del self._registry[name]

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._registry.get(name)

    def get_descriptor(self, name: str) -> Optional[SkillDescriptor]:
        skill = self.get(name)
        return skill.get_descriptor() if skill else None

    def list_skills(self) -> List[SkillDescriptor]:
        return [skill.get_descriptor() for skill in self._registry.values()]
