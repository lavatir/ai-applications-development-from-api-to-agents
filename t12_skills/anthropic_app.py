import json
from pathlib import Path

import anthropic
from anthropic.lib import files_from_dir

from commons.constants import ANTHROPIC_API_KEY

SKILLS_VERSION = "skills-2025-10-02"


def get_or_create_skill(
    skill_title: str, skill_dir: Path, client: anthropic.Anthropic
) -> str:
    existing_skills = client.beta.skills.list(source="custom", betas=[SKILLS_VERSION])
    for skill in existing_skills:
        if skill.display_title == skill_title:
            print(f"Found existing skill '{skill_title}' with id: {skill.id}")
            return skill.id

    files = files_from_dir(skill_dir)
    new_skill = client.beta.skills.create(
        files=files,
        display_title=skill_title,
        betas=[SKILLS_VERSION],
    )
    print(f"Created new skill '{skill_title}' with id: {new_skill.id}")
    return new_skill.id


def delete_skills(client: anthropic.Anthropic):
    skills = client.beta.skills.list(source="custom", betas=[SKILLS_VERSION])
    for skill in skills:
        versions = client.beta.skills.versions.list(skill.id, betas=[SKILLS_VERSION])
        for version in versions:
            client.beta.skills.versions.delete(
                version.version, skill_id=skill.id, betas=[SKILLS_VERSION]
            )
            print(f"Deleted version {version.version} of skill {skill.id}")

        client.beta.skills.delete(skill.id, betas=[SKILLS_VERSION])
        print(f"Deleted skill {skill.id}")


def chat(
    client: anthropic.Anthropic,
    skill_id: str,
    log_request: bool = True,
    log_response: bool = True,
):
    """Multi-turn chat loop that reuses the container across turns."""
    messages = []
    container_id = None
    print("\nStyle Guide Agent is ready. Ask it to write, rewrite, or review any text.")
    print("Type 'exit' to quit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        container = {
            "skills": [{"type": "custom", "skill_id": skill_id, "version": "latest"}]
        }
        if container_id:
            container["id"] = container_id

        request_payload = {
            "model": "claude-sonnet-5",
            "max_tokens": 4096,
            "messages": messages,
            "container": container,
            "betas": ["code-execution-2025-08-25", SKILLS_VERSION],
            "tools": [{"type": "code_execution_20250825", "name": "code_execution"}],
        }

        if log_request:
            print(json.dumps(request_payload, indent=2))

        response = client.beta.messages.create(**request_payload)

        if log_response:
            print(response.model_dump_json(indent=2))
        else:
            text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            print(f"Claude: {text}")

        if response.container:
            container_id = response.container.id

        messages.append({"role": "assistant", "content": response.content})


STYLE_SKILL_TITLE = "style-guide"
STYLE_SKILL_DIR = Path(__file__).parent / "_skills" / STYLE_SKILL_TITLE

CALCULATOR_SKILL_TITLE = "calculator"
CALCULATOR_SKILL_DIR = Path(__file__).parent / "_skills" / CALCULATOR_SKILL_TITLE


def main():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    skill_id = get_or_create_skill(STYLE_SKILL_TITLE, STYLE_SKILL_DIR, client)
    try:
        chat(client, skill_id)
    finally:
        delete_skills(client)


if __name__ == "__main__":
    main()
