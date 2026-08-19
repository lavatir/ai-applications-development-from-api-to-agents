import os
from pathlib import Path

from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.vectorstores import VectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import SecretStr

from commons.constants import OPENAI_API_KEY

# TODO:
# Create system prompt with:
# - role: explains the role for LLM and what it should do
# - Structure of User message, consists of 2 blocks:
#   - `RAG CONTEXT`: information retrieved on the Retrieval step based on user request
#   - `USER QUESTION`: The user's actual question
# - Instructions:
#   - Model must use only information from conversation
#   - Strictly forbid to answer questions that are not in the conversation or not present in `RAG CONTEXT`
_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about a microwave oven based strictly on the manual.

The user message you receive will contain two sections:
- RAG CONTEXT: information retrieved from the microwave manual that is relevant to the user's question.
- USER QUESTION: the actual question the user is asking.

Instructions:
- Answer using only the information provided in the RAG CONTEXT.
- Do not use any outside knowledge or make assumptions beyond what is stated in the RAG CONTEXT.
- If the RAG CONTEXT does not contain enough information to answer the question, say that you don't know based on the available information. Do not answer questions that are unrelated to the RAG CONTEXT.
"""

_USER_PROMPT = """##RAG CONTEXT:
{context}


##USER QUESTION:
{query}"""

_INDEX_PATH = str(Path(__file__).parent / "microwave_faiss_index")
_MANUAL_PATH = str(Path(__file__).parent / "microwave_manual.txt")


class MicrowaveRAG:
    def __init__(self, embeddings: OpenAIEmbeddings, llm_client: ChatOpenAI):
        self.llm_client = llm_client
        self.embeddings = embeddings
        self.vectorstore = self._setup_vectorstore()

    def _setup_vectorstore(self) -> VectorStore:
        """
        Load existing FAISS index from disk or create a new one.
        Returns:
              VectorStore: Initialized FAISS vectorstore.
        """
        print("Setting up vectorstore...")

        if os.path.exists(_INDEX_PATH):
            print("Loading existing FAISS index from disk...")
            return FAISS.load_local(
                _INDEX_PATH,
                self.embeddings,
                allow_dangerous_deserialization=True,
            )

        return self._create_new_index()

    def _create_new_index(self) -> VectorStore:
        """
        Load the manual, split into chunks, embed, and save a new FAISS index.
        Returns:
              VectorStore: Newly created and saved FAISS vectorstore.
        """
        print("Creating new FAISS index from microwave manual...")

        documents = TextLoader(_MANUAL_PATH).load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300, chunk_overlap=50, separators=["\n\n", "\n", "."]
        )
        chunks = splitter.split_documents(documents)

        vectorstore = FAISS.from_documents(chunks, self.embeddings)
        vectorstore.save_local(_INDEX_PATH)

        return vectorstore

    def retrieve_context(self, query: str, k: int = 4, score=0.3):
        """
        Retrieve the context for a given query.
        Args:
              query (str): The query to retrieve the context for.
              k (int): The number of relevant documents(chunks) to retrieve.
              score (float): The similarity score between documents and query. Range 0.0 to 1.0.
        """
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query, k=k, score_threshold=score
        )

        chunks = []
        for doc, relevance_score in results:
            print(f"Relevance score: {relevance_score:.4f}")
            chunks.append(doc.page_content)

        return "\n\n".join(chunks)

    def augment_prompt(self, query: str, context: str):
        """
        Inject retrieved context and user query into the prompt template.
        Args:
              query (str): The user's question.
              context (str): Retrieved context from the vectorstore.
        Returns:
              str: Formatted prompt ready for the LLM.
        """
        augmented_prompt = _USER_PROMPT.format(context=context, query=query)
        print(augmented_prompt)
        return augmented_prompt

    def generate_answer(self, augmented_prompt: str):
        """
        Send the augmented prompt to the LLM and return its response.
        Args:
              augmented_prompt (str): The prompt with injected context and query.
        Returns:
              str: The LLM-generated answer.
        """
        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=augmented_prompt),
        ]

        response = self.llm_client.invoke(messages)
        print(response.content)

        return response.content


def main(rag: MicrowaveRAG):
    print("Welcome to the Microwave Manual Assistant! Type 'exit' to quit.")

    while True:
        query = input("> ").strip()
        if query.lower() == "exit":
            break

        context = rag.retrieve_context(query)
        augmented_prompt = rag.augment_prompt(query, context)
        rag.generate_answer(augmented_prompt)


main(
    MicrowaveRAG(
        embeddings=OpenAIEmbeddings(
            model="text-embedding-3-small", api_key=SecretStr(OPENAI_API_KEY)
        ),
        llm_client=ChatOpenAI(
            temperature=0.0, model="gpt-5.2", api_key=SecretStr(OPENAI_API_KEY)
        ),
    )
)
