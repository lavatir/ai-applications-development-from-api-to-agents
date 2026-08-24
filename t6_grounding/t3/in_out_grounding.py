import asyncio
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field, SecretStr

from commons.constants import OPENAI_API_KEY
from t6_grounding.user_service_client import UserServiceClient

# Info about app:
# HOBBIES SEARCHING WIZARD
# Searches users by hobbies and provides their full info in JSON format:
#   Input: `I need people who love to go to mountains`
#   Output:
#     ```json
#       "rock climbing": [{full user info JSON},...],
#       "hiking": [{full user info JSON},...],
#       "camping": [{full user info JSON},...]
#     ```
# ---
# 1. Since we are searching hobbies that persist in `about_me` section - we need to embed only user `id` and `about_me`!
#    It will allow us to reduce context window significantly.
# 2. Pay attention that every 5 minutes in User Service will be added new users and some will be deleted. We will at the
#    'cold start' add all users for current moment to vectorstor and with each user request we will update vectorstor on
#    the retrieval step, we will remove deleted users and add new - it will also resolve the issue with consistency
#    within this 2 services and will reduce costs (we don't need on each user request load vectorstor from scratch and pay for it).
# 3. We ask LLM make NEE (Named Entity Extraction) https://cloud.google.com/discover/what-is-entity-extraction?hl=en
#    and provide response in format:
#    {
#       "{hobby}": [{user_id}, 2, 4, 100...]
#    }
#    It allows us to save significant money on generation, reduce time on generation and eliminate possible
#    hallucinations (corrupted personal info or removed some parts of PII (Personal Identifiable Information)). After
#    generation we also need to make output grounding (fetch full info about user and in the same time check that all
#    presented IDs are correct).
# 4. In response we expect JSON with grouped users by their hobbies.
# ---
# This sample is based on the real solution where one Service provides our Wizard with user request, we fetch all
# required data and then returned back to 1st Service response in JSON format.
# ---
# Useful links:
# Chroma DB: https://docs.langchain.com/oss/python/integrations/vectorstores/index#chroma
# Document#id: https://docs.langchain.com/oss/python/langchain/knowledge-base#1-documents-and-document-loaders
# ---
# TASK:
# Implement such application as described on the `flow.png` with adaptive vector based grounding and 'lite' version of
# output grounding (verification that such user exist and fetch full user info)

SYSTEM_PROMPT = """You are a Named Entity Extraction system for a hobbies search wizard.

The user message contains two sections:
- RAG CONTEXT: a list of users with their id and about_me text, retrieved because they are semantically
  relevant to the search request.
- USER QUESTION: the user's hobby search request.

The USER QUESTION may describe a broad theme (e.g. "mountains", "staying active") that maps to MULTIPLE
distinct hobbies, not just one. Consider every hobby mentioned in the RAG CONTEXT that is a reasonable match
for the theme of the USER QUESTION - do not narrow it down to a single hobby if several are relevant.

For each relevant hobby, examine every user's about_me text in the RAG CONTEXT and collect the ids of all
users who mention that hobby.

Group the matching user ids by hobby, keeping each hobby as its own separate group (do not merge different
hobbies together). Respond ONLY with the ids of users from the RAG CONTEXT - never invent ids or hobbies
that are not grounded in the provided context. If no user matches, return an empty mapping.
"""

USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


class HobbyGroup(BaseModel):
    hobby: str = Field(description="Hobby name")
    user_ids: list[int] = Field(description="List of matching user ids for this hobby")


class HobbyGroups(BaseModel):
    hobbies: list[HobbyGroup] = Field(
        description="List of hobby groups, each with the matching user ids",
        default_factory=list,
    )


def format_user_about_me(user: dict[str, Any]) -> str:
    return f"id: {user['id']}\nabout_me: {user.get('about_me', '')}\n\n"


class HobbiesWizard:
    COLLECTION_NAME = "users_about_me"

    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self._llm_client = OpenAI(api_key=OPENAI_API_KEY)
        self._user_client = UserServiceClient()
        self.vectorstore: Chroma | None = None

    async def __aenter__(self):
        print("🔎 Loading all users...")
        users = self._user_client.get_all_users()

        print(f"↗️ Creating embeddings and vectorstore for {len(users)} documents...")
        self.vectorstore = await self._create_vectorstore_with_batching(
            users, batch_size=100
        )

        print("✅ Vectorstore is ready.")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def _create_vectorstore_with_batching(
        self, users: list[dict[str, Any]], batch_size: int = 100
    ) -> Chroma:
        vectorstore = Chroma(
            collection_name=self.COLLECTION_NAME, embedding_function=self.embeddings
        )

        batches = [users[i : i + batch_size] for i in range(0, len(users), batch_size)]

        coroutines = [
            vectorstore.aadd_documents(
                [
                    Document(
                        id=str(user["id"]), page_content=format_user_about_me(user)
                    )
                    for user in batch
                ]
            )
            for batch in batches
        ]
        await asyncio.gather(*coroutines, return_exceptions=True)

        return vectorstore

    async def _sync_vectorstore(self) -> None:
        """Remove deleted users and add new users to keep the vectorstore consistent"""
        assert self.vectorstore is not None, "Vectorstore is not initialized"

        current_users = self._user_client.get_all_users()
        current_ids = {str(user["id"]) for user in current_users}

        stored_ids = set(self.vectorstore.get(include=[])["ids"])

        deleted_ids = list(stored_ids - current_ids)
        if deleted_ids:
            self.vectorstore.delete(ids=deleted_ids)

        new_users = [
            user for user in current_users if str(user["id"]) not in stored_ids
        ]
        if new_users:
            self.vectorstore.add_documents(
                [
                    Document(
                        id=str(user["id"]), page_content=format_user_about_me(user)
                    )
                    for user in new_users
                ]
            )

    async def retrieve_context(
        self, query: str, k: int = 20, score: float = 0.1
    ) -> str:
        print("Retrieving context...")

        await self._sync_vectorstore()

        assert self.vectorstore is not None, "Vectorstore is not initialized"
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=k, score_threshold=score
        )

        context_parts = []
        for doc, relevance_score in results:
            context_parts.append(doc.page_content)
            print(
                f"Retrieved (Score: {relevance_score:.3f}): {doc.page_content.strip()}"
            )

        return "\n\n".join(context_parts)

    def augment_prompt(self, query: str, context: str) -> str:
        return USER_PROMPT.format(context=context, query=query)

    def generate_hobby_groups(self, augmented_prompt: str) -> dict[str, list[int]]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": augmented_prompt},
        ]

        response = self._llm_client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            temperature=0.0,
            messages=messages,
            response_format=HobbyGroups,
        )

        parsed = response.choices[0].message.parsed
        if not parsed:
            return {}

        return {group.hobby: group.user_ids for group in parsed.hobbies}

    async def ground_output(
        self, hobby_groups: dict[str, list[int]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Output grounding: fetch full user info for each id and drop ids that don't exist"""
        grounded: dict[str, list[dict[str, Any]]] = {}

        for hobby, user_ids in hobby_groups.items():
            users = []
            for user_id in user_ids:
                try:
                    user = await self._user_client.get_user(user_id)
                    users.append(user)
                except Exception:
                    print(f"⚠️ User {user_id} not found, skipping (hallucinated id)")
            if users:
                grounded[hobby] = users

        return grounded


def format_grounded_results(grounded_results: dict[str, list[dict[str, Any]]]) -> str:
    if not grounded_results:
        return "No matching users found."

    lines = []
    for hobby, users in grounded_results.items():
        names = ", ".join(f"{user['name']} {user['surname']}" for user in users)
        lines.append(f"🏷️ {hobby} ({len(users)}): {names}")

    return "\n".join(lines)


async def main():
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=SecretStr(OPENAI_API_KEY),
        dimensions=384,
    )

    async with HobbiesWizard(embeddings) as wizard:
        print("Query samples:")
        print(" - I need people who love to go to mountains")
        while True:
            user_question = input("> ").strip()
            if user_question.lower() in ["quit", "exit"]:
                break

            context = await wizard.retrieve_context(user_question)
            augmented_prompt = wizard.augment_prompt(user_question, context)
            hobby_groups = wizard.generate_hobby_groups(augmented_prompt)
            grounded_results = await wizard.ground_output(hobby_groups)

            print(f"\n=== Results ===\n{format_grounded_results(grounded_results)}\n")


if __name__ == "__main__":
    asyncio.run(main())
