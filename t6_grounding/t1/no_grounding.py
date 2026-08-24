import asyncio
from typing import Any

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from commons.constants import OPENAI_API_KEY
from t6_grounding.user_service_client import UserServiceClient

BATCH_SYSTEM_PROMPT = """You are a user search assistant.

Analyze the search criteria described in the user's question. Examine each user in the provided list of users
and determine whether they match the search criteria.

Return the full details of every matching user, in their original format, exactly as provided.
If no users match the search criteria, respond with exactly: NO_MATCHES_FOUND
"""

FINAL_SYSTEM_PROMPT = """You are a user search assistant compiling final search results.

You will be given the combined results from multiple batch searches, each containing users that matched
the search criteria. Review all batch results, combine and deduplicate matching users found across batches,
and present the final list of matching users in a clear, organized manner.
"""

USER_PROMPT = """##USER DATA:
{context}


##SEARCH QUESTION:
{query}"""


class TokenTracker:
    def __init__(self):
        self.total_tokens = 0
        self.batch_tokens = []

    def add_tokens(self, tokens: int):
        self.total_tokens += tokens
        self.batch_tokens.append(tokens)

    def get_summary(self) -> dict:
        return {
            "total_tokens": self.total_tokens,
            "batch_count": len(self.batch_tokens),
            "batch_tokens": self.batch_tokens,
        }


llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

token_tracker = TokenTracker()


def join_context(context: list[dict[str, Any]]) -> str:
    result = ""
    for user in context:
        result += "User:\n"
        for key, value in user.items():
            result += f"  {key}: {value}\n"
        result += "\n"
    return result


async def generate_response(system_prompt: str, user_message: str) -> str:
    print("Processing...")

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    response = await llm_client.chat.completions.create(
        model="gpt-4.1-nano",
        temperature=0.0,
        messages=messages,
    )

    tokens = response.usage.total_tokens if response.usage else 0
    token_tracker.add_tokens(tokens)

    content = response.choices[0].message.content or ""
    print(f"{content}\n(tokens used: {tokens})")

    return content


async def main():
    print("Query samples:")
    print(" - Do we have someone with name John that loves traveling?")

    user_question = input("> ").strip()

    if not user_question:
        return

    print("\n--- Searching user database ---")
    users = UserServiceClient().get_all_users()
    batches = [users[i : i + 100] for i in range(0, len(users), 100)]

    coroutines = [
        generate_response(
            BATCH_SYSTEM_PROMPT,
            USER_PROMPT.format(context=join_context(batch), query=user_question),
        )
        for batch in batches
    ]
    batch_results = await asyncio.gather(*coroutines)

    print("\n--- Compiling results ---")
    relevant_results = [
        result for result in batch_results if result.strip() != "NO_MATCHES_FOUND"
    ]

    print("\n=== SEARCH RESULTS ===")
    if relevant_results:
        combined_results = "\n\n".join(relevant_results)
        await generate_response(
            FINAL_SYSTEM_PROMPT,
            f"Batch search results:\n\n{combined_results}\n\nOriginal search question: {user_question}",
        )
    else:
        print("No users found matching your search. Try refining your search criteria.")

    summary = token_tracker.get_summary()
    print(
        f"\n=== Performance ===\nTotal API calls: {summary['batch_count']}\nTotal tokens used: {summary['total_tokens']}"
    )


if __name__ == "__main__":
    asyncio.run(main())


# The problems with No Grounding approach are:
#   - If we load whole users as context in one request to LLM we will hit context window
#   - Huge token usage == Higher price per request
#   - Added + one chain in flow where original user data can be changed by LLM (before final generation)
# User Question -> Get all users -> ‼️parallel search of possible candidates‼️ -> probably changed original context -> final generation
