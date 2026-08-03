from __future__ import annotations

from dataclasses import dataclass

from ...platform import SkillDocument, SkillRegistry

CORE_SKILL_NAMES: tuple[str, ...] = (
    "query-and-analyze",
    "using-connection-cli",
    "using-marcopolo-workspace",
)


@dataclass(frozen=True)
class AgentBootstrapContext:
    """Durable context preloaded into the chat agent at session start."""

    skill_names: tuple[str, ...]
    skill_documents: tuple[SkillDocument, ...]
    combined_text: str


def preload_core_skill_context(skills: SkillRegistry) -> AgentBootstrapContext:
    selected: list[SkillDocument] = []
    parts: list[str] = []

    for name in CORE_SKILL_NAMES:
        skill = skills.get(name)
        if skill is None:
            continue
        selected.append(skill)
        parts.append(
            "\n".join(
                [
                    f"# Skill: {skill.name}",
                    f"Path: {skill.path}",
                    f"Description: {skill.description}".rstrip(),
                    "",
                    skill.body.strip(),
                ]
            ).strip()
        )

    return AgentBootstrapContext(
        skill_names=tuple(skill.name for skill in selected),
        skill_documents=tuple(selected),
        combined_text="\n\n".join(parts).strip(),
    )
