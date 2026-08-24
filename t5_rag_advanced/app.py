from commons.constants import (
    OPENAI_API_KEY,
    OPENAI_CHAT_COMPLETIONS_ENDPOINT,
    OPENAI_EMBEDDINGS_ENDPOINT,
)
from commons.models.conversation import Conversation
from commons.models.message import Message
from commons.models.role import Role
from t5_rag_advanced.chat.chat_completion_client import ChatCompletionClient
from t5_rag_advanced.embeddings.embeddings_client import EmbeddingsClient
from t5_rag_advanced.embeddings.text_processor import SearchMode, TextProcessor

SYSTEM_PROMPT = """You are a RAG (Retrieval-Augmented Generation) powered assistant for a microwave oven manual.

Each user message contains two sections:
- RAG CONTEXT: information retrieved from the microwave manual that is relevant to the user's question.
- USER QUESTION: the actual question the user is asking.

Instructions:
- Answer using only the information provided in the RAG CONTEXT and the prior conversation history.
- Do not use any outside knowledge or make assumptions beyond what is stated in the RAG CONTEXT.
- If the RAG CONTEXT is empty or does not contain enough information to answer the question, say that you don't know based on the available information.
- Do not answer questions that are unrelated to microwave usage.
"""

USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""


def run_chat(
    text_processor: TextProcessor,
    chat_client: ChatCompletionClient,
) -> None:
    conversation = Conversation()
    conversation.add_message(Message(Role.SYSTEM, SYSTEM_PROMPT))

    print("Welcome to the Microwave Manual Assistant! Type 'exit' to quit.")

    while True:
        query = input("> ").strip()
        if query.lower() == "exit":
            break

        chunks = text_processor.search(
            mode=SearchMode.COSINE_DISTANCE,
            query=query,
            top_k=5,
            min_score=0.5,
            dimensions=384,
        )
        context = "\n\n".join(chunks)

        augmented_prompt = USER_PROMPT.format(context=context, query=query)
        conversation.add_message(Message(Role.USER, augmented_prompt))

        answer = chat_client.get_completion(conversation.get_messages())
        print(answer.content)

        conversation.add_message(answer)


# PAY ATTENTION THAT YOU NEED TO RUN Postgres DB ON THE 5433 WITH PGVECTOR EXTENSION!
# RUN docker-compose.yml

embeddings_client = EmbeddingsClient(
    endpoint=OPENAI_EMBEDDINGS_ENDPOINT,
    model_name="text-embedding-3-small",
    api_key=OPENAI_API_KEY,
)

chat_completion_client = ChatCompletionClient(
    endpoint=OPENAI_CHAT_COMPLETIONS_ENDPOINT,
    model_name="gpt-5.2",
    api_key=OPENAI_API_KEY,
)

text_processor = TextProcessor(
    embeddings_client=embeddings_client,
    db_config={
        "host": "localhost",
        "port": 5433,
        "database": "vectordb",
        "user": "postgres",
        "password": "postgres",
    },
)

if input("Load context into the database? (y/n): ").strip().lower() == "y":
    text_processor.process_text_file(
        file_name="t5_rag_advanced/embeddings/microwave_manual.txt",
        chunk_size=300,
        overlap=40,
        dimensions=384,
        truncate=True,
    )

run_chat(text_processor, chat_completion_client)
