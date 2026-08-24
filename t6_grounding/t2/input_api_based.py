from enum import StrEnum
from typing import Any

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from commons.constants import OPENAI_API_KEY
from t6_grounding.user_service_client import UserServiceClient

QUERY_ANALYSIS_PROMPT = """You are a query analysis system.

Available search fields: name, surname, email.

Analyze the user's question and extract explicit search values, mapping each one to the appropriate search field.
Only extract values that are clearly and explicitly stated in the question - do not infer or assume values that
are not present.

Examples:
- "Who is John?" → name: "John"
- "Find John Smith" → name: "John", surname: "Smith"
"""

SYSTEM_PROMPT = """You are a RAG (Retrieval-Augmented Generation) powered assistant.

The user message contains two sections:
- RAG CONTEXT: user data retrieved from the user service that is relevant to the question.
- USER QUESTION: the actual question being asked.

Answer ONLY based on the information provided in the RAG CONTEXT and the prior conversation history.
If the RAG CONTEXT does not contain relevant information to answer the question, state clearly that
the question cannot be answered based on the available information.

When presenting user information, format it clearly.
"""

USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


class SearchField(StrEnum):
    NAME = "name"
    SURNAME = "surname"
    EMAIL = "email"


class SearchRequest(BaseModel):
    search_field: SearchField = Field(description="Search field")
    search_value: str = Field(description="Search value. Sample: Adam.")


class SearchRequests(BaseModel):
    search_request_parameters: list[SearchRequest] = Field(
        description="List of search parameters to execute", default_factory=list
    )


llm_client = OpenAI(api_key=OPENAI_API_KEY)

user_client = UserServiceClient()

total_tokens = 0


def retrieve_context(user_question: str) -> list[dict[str, Any]]:
    global total_tokens

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": QUERY_ANALYSIS_PROMPT},
        {"role": "user", "content": user_question},
    ]

    response = llm_client.beta.chat.completions.parse(
        model="gpt-4.1-nano",
        temperature=0.0,
        messages=messages,
        response_format=SearchRequests,
    )

    total_tokens += response.usage.total_tokens if response.usage else 0

    parsed = response.choices[0].message.parsed
    parameters = parsed.search_request_parameters if parsed else []

    if parameters:
        search_params = {
            param.search_field.value: param.search_value for param in parameters
        }
        print(f"Searching with parameters: {search_params}")
        return user_client.search_users(**search_params)

    print("No specific search parameters found!")
    return []


def augment_prompt(user_question: str, context: list[dict[str, Any]]) -> str:
    formatted_context = ""
    for user in context:
        formatted_context += "User:\n"
        for key, value in user.items():
            formatted_context += f"  {key}: {value}\n"
        formatted_context += "\n"

    augmented_prompt = USER_PROMPT.format(
        context=formatted_context, query=user_question
    )
    print(augmented_prompt)

    return augmented_prompt


def generate_answer(augmented_prompt: str) -> str:
    global total_tokens

    messages: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": augmented_prompt},
    ]

    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.0,
        messages=messages,
    )

    total_tokens += response.usage.total_tokens if response.usage else 0

    return response.choices[0].message.content or ""


def main():
    print("Query samples:")
    print(" - I need user emails that filled with hiking and psychology")
    print(" - Who is John?")
    print(" - Find users with surname Adams")
    print(" - Do we have smbd with name John that love painting?")

    while True:
        user_question = input("> ").strip()
        if user_question:
            if user_question.lower() in ["quit", "exit"]:
                print(f"\n=== Performance ===\nTotal tokens used: {total_tokens}")
                break

            print("\n--- Retrieving context ---")
            context = retrieve_context(user_question)

            if context:
                print("\n--- Augmenting prompt ---")
                augmented_prompt = augment_prompt(user_question, context)

                print("\n--- Generating answer ---")
                answer = generate_answer(augmented_prompt)
                print(f"\nAnswer: {answer}\n")
            else:
                print("\n--- No relevant information found ---")


if __name__ == "__main__":
    main()


# The problems with API based Grounding approach are:
#   - We need a Pre-Step to figure out what field should be used for search (Takes time)
#   - Values for search should be correct (✅ John -> ❌ Jonh)
#   - Is not so flexible
# Benefits are:
#   - We fetch actual data (new users added and deleted every 5 minutes)
#   - Costs reduce
