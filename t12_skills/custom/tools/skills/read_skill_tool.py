from pathlib import Path
from typing import Any

from t12_skills.custom.file_utils import get_file_content
from t12_skills.custom.tools.base import BaseTool


class ReadSkillTool(BaseTool):
    """Reads files from the local skills directory by path."""

    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir.resolve()

    @property
    def name(self) -> str:
        return "read_skill"

    @property
    def description(self) -> str:
        return (
            "Reads a file from the local skills directory (SKILL.md, scripts, or reference files). "
            "Use this to load skill instructions before acting. Pass the file path relative to the "
            "skills directory, e.g. 'unit-converter/SKILL.md' or 'unit-converter/scripts/convert.py' "
            "(a leading '/' is optional and will be stripped)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "Path to the skill file, relative to the skills directory "
                        "(e.g. 'unit-converter/SKILL.md')."
                    ),
                },
            },
            "required": ["path"],
        }

    async def _execute(self, arguments: dict[str, Any]) -> str:
        relative_path = arguments["path"].lstrip("/")
        full_path = self._skills_dir / relative_path
        return get_file_content(full_path)
