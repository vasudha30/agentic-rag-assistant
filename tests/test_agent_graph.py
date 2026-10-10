"""Tests for the agentic RAG LangGraph workflow."""

from pathlib import Path

import pytest

from app.agent.graph import build_agent_graph
from app.agent.llm.mock import MockLLMProvider
from app.agent.nodes import AgentNodes
from app.agent.state import AgentState
from app.ingestion.chunking.text_chunker import TextChunker
from app.ingestion.cleaning.text_cleaner import TextCleaner
from app.ingestion.embeddings.mock import MockEmbeddingProvider
from app.ingestion.loaders.factory import DocumentLoaderFactory
from app.ingestion.pipeline import IngestionPipeline
from app.retrieval.retriever import SemanticRetriever
from app.vectorstore.chroma import ChromaVectorStore


@pytest.fixture
def agent_graph(tmp_path: Path):
    """Create an isolated agent graph with test data."""
    vector_store = ChromaVectorStore(
        persist_directory=tmp_path / "chroma",
        collection_name="agent_graph_test",
    )

    embedding_provider = MockEmbeddingProvider(dimension=32)

    pipeline = IngestionPipeline(
        loader_factory=DocumentLoaderFactory.default(),
        text_cleaner=TextCleaner(),
        text_chunker=TextChunker(
            chunk_size=1000,
            chunk_overlap=100,
        ),
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    document = tmp_path / "document.txt"
    document.write_text(
        "Machine learning enables systems to learn from data.",
        encoding="utf-8",
    )

    pipeline.ingest(
        file_path=document,
        document_id="document-a",
        user_id="user-a",
        file_type="text/plain",
    )

    retriever = SemanticRetriever(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
    )

    llm_provider = MockLLMProvider()

    nodes = AgentNodes(
        retriever=retriever,
        llm_provider=llm_provider,
    )

    return build_agent_graph(nodes)


def test_agent_graph_retrieves_user_documents(agent_graph) -> None:
    """The graph should retrieve documents belonging to the current user."""
    state = AgentState(
        query="According to the document, what is machine learning?",
        user_id="user-a",
    )

    result = agent_graph.invoke(state)

    assert result["query"] == "According to the document, what is machine learning?"
    assert result["user_id"] == "user-a"
    assert result["retrieval_attempts"] == 1
    assert result["retrieved_chunks"]

    assert all(
        chunk["metadata"]["user_id"] == "user-a" for chunk in result["retrieved_chunks"]
    )


def test_agent_graph_does_not_cross_user_boundary(agent_graph) -> None:
    """The graph must not retrieve another user's documents."""
    state = AgentState(
        query="machine learning",
        user_id="user-b",
    )

    result = agent_graph.invoke(state)

    assert result["retrieved_chunks"] == []


def test_agent_graph_rejects_blank_query(agent_graph) -> None:
    """The planner should reject blank queries."""
    state = AgentState(
        query="   ",
        user_id="user-a",
    )

    with pytest.raises(ValueError, match="query cannot be empty"):
        agent_graph.invoke(state)


def test_agent_graph_rejects_blank_user_id(agent_graph) -> None:
    """The planner should reject blank user identifiers."""
    state = AgentState(
        query="machine learning",
        user_id="   ",
    )

    with pytest.raises(ValueError, match="user_id cannot be empty"):
        agent_graph.invoke(state)


def test_generate_uses_openai_and_gemini_then_synthesizes() -> None:
    class StubProvider:
        def __init__(self, responses: list[str]) -> None:
            self.responses = responses
            self.calls = 0

        def generate(
            self,
            *,
            system_prompt: str,
            user_prompt: str,
        ) -> str:
            response = self.responses[self.calls]
            self.calls += 1
            return response

    class StubRetriever:
        def retrieve(
            self,
            *,
            query: str,
            user_id: str,
            document_id: str | None,
            top_k: int,
        ) -> list:
            return [
                type(
                    "RetrievedChunk",
                    (),
                    {
                        "chunk_id": "chunk-1",
                        "text": (
                            "Machine learning is a method for learning "
                            "patterns from data."
                        ),
                        "metadata": {},
                    },
                )()
            ]

    openai_provider = StubProvider(
        [
            "Machine learning learns patterns from data.",
            "Machine learning allows systems to learn patterns from data.",
        ]
    )

    gemini_provider = StubProvider(
        [
            "Machine learning identifies patterns in data.",
        ]
    )

    nodes = AgentNodes(
        retriever=StubRetriever(),
        llm_provider=MockLLMProvider(),
        openai_provider=openai_provider,
        gemini_provider=gemini_provider,
    )

    state = AgentState(
        query="What is machine learning?",
        user_id="1",
    )

    state = nodes.retrieve(state)
    state = nodes.generate(state)
    state = nodes.verify(state)

    assert state.openai_answer == ("Machine learning learns patterns from data.")

    assert state.gemini_answer == ("Machine learning identifies patterns in data.")

    assert state.answer == (
        "Machine learning allows systems to learn patterns from data."
    )

    assert state.verification_passed is True

    assert openai_provider.calls == 2
    assert gemini_provider.calls == 1


def test_web_route_uses_search_service() -> None:
    """The web route should search and pass results to the LLM."""

    class StubRetriever:
        def retrieve(
            self,
            *,
            query: str,
            user_id: str,
            document_id: str | None,
            top_k: int,
        ) -> list:
            return []

    class StubWebSearchService:
        def search(
            self,
            query: str,
            *,
            max_results: int = 5,
        ) -> list[dict[str, str]]:
            assert query == "latest AI developments"
            assert max_results == 5

            return [
                {
                    "title": "Example AI News",
                    "url": "https://example.com/ai",
                    "snippet": "Latest AI development information.",
                }
            ]

    nodes = AgentNodes(
        retriever=StubRetriever(),
        llm_provider=MockLLMProvider(),
        web_search_service=StubWebSearchService(),
    )

    state = AgentState(
        query="latest AI developments",
        user_id="user-a",
    )

    state = nodes.planner(state)

    assert state.route == "web"

    state = nodes.generate(state)

    assert state.tool_result is not None
    assert "Example AI News" in state.tool_result
    assert "https://example.com/ai" in state.tool_result
    assert state.answer is not None


def test_web_route_handles_search_failure() -> None:
    """The web route should handle search service failures gracefully."""

    class StubRetriever:
        def retrieve(
            self,
            *,
            query: str,
            user_id: str,
            document_id: str | None,
            top_k: int,
        ) -> list:
            return []

    class FailingWebSearchService:
        def search(
            self,
            query: str,
            *,
            max_results: int = 5,
        ) -> list[dict[str, str]]:
            raise RuntimeError("Search service unavailable")

    nodes = AgentNodes(
        retriever=StubRetriever(),
        llm_provider=MockLLMProvider(),
        web_search_service=FailingWebSearchService(),
    )

    state = AgentState(
        query="latest AI developments",
        user_id="user-a",
    )

    state = nodes.planner(state)
    state = nodes.generate(state)

    assert state.route == "web"
    assert state.answer == (
        "I could not search the web right now. " "Please try again shortly."
    )
    assert state.error == "Search service unavailable"

def test_planner_does_not_search_when_user_opts_out(
    agent_graph,
) -> None:
    from app.agent.state import AgentState

    state = AgentState(
        query="Explain RAG in simple terms. Do not search the web.",
        user_id="test-user",
    )

    result = agent_graph.invoke(state)

    assert result["route"] == "general"
