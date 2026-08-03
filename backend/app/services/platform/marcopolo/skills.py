from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class SkillDocument:
    name: str
    description: str
    path: str
    body: str


class SkillRegistry:
    def __init__(self, skills: list[SkillDocument]):
        self._skills = {skill.name: skill for skill in skills}

    @property
    def count(self) -> int:
        return len(self._skills)

    def summaries(self) -> list[SkillDocument]:
        return list(self._skills.values())

    def get(self, name: str) -> SkillDocument | None:
        return self._skills.get(name)


@lru_cache
def load_skill_registry(skill_repo_path: str) -> SkillRegistry:
    if not skill_repo_path.strip():
        return SkillRegistry([])

    root = Path(skill_repo_path)
    if not root.exists():
        return SkillRegistry([])

    skills: list[SkillDocument] = []
    for skill_path in sorted(root.glob("*/SKILL.md")):
        text = skill_path.read_text(encoding="utf-8")
        name, description, body = _parse_skill_document(text)
        skills.append(
            SkillDocument(
                name=name or skill_path.parent.name,
                description=description or "",
                path=str(skill_path),
                body=body,
            )
        )
    return SkillRegistry(skills)


def _parse_skill_document(text: str) -> tuple[str | None, str | None, str]:
    if not text.startswith("---\n"):
        return None, None, text

    _, frontmatter, body = text.split("---", 2)
    name: str | None = None
    description: str | None = None
    for raw_line in frontmatter.splitlines():
        line = raw_line.strip()
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("description:"):
            description = line.split(":", 1)[1].strip().strip('"')

    return name, description, body.lstrip()
