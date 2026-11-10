# backend/app/core/provider_factory.py
import os
import time
import requests
from typing import List, Sequence
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document, BaseDocumentCompressor
from langchain_nvidia_ai_endpoints import (
    ChatNVIDIA,
    NVIDIARerank,
    Model,
    register_model,
)
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import FAISS, AzureSearch
from app.core.config import settings
from langchain_core.callbacks import Callbacks

# Register latest Nemotron 3.5 Reranker
try:
    register_model(
        Model(
            id="nvidia/nemotron-3.5-rerank-8b",
            model_type="ranking",
            client="NVIDIARerank",
            endpoint="https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-rerank-8b/reranking",
        )
    )
except Exception:
    pass


class NVIDIANemotronEmbeddings(Embeddings):
    """
    Direct, resilient LangChain Embeddings client for NVIDIA Nemotron 3.5
    (nvidia/nemotron-3.5-embed-1b and nvidia/nemotron-3.5-embed-8b).
    Explicitly passes input_type ('passage' vs 'query') and modality='text'.
    """

    def __init__(
        self,
        model: str,
        api_key: str,
        batch_size: int = 8,
        endpoint: str = "https://integrate.api.nvidia.com/v1/embeddings",
    ):
        self.model = model
        self.api_key = api_key
        self.batch_size = batch_size
        self.endpoint = endpoint

    def _sanitize_text(self, text: str) -> str:
        # Remove null bytes and prevent multimodal NIM from misinterpreting '<img' or '<...' as broken base64 images
        cleaned = text.replace("\x00", " ").replace("<img", "[img").strip()
        return cleaned if cleaned else "empty"

    def _call_nim(self, texts: List[str], input_type: str) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "input": [self._sanitize_text(t) for t in texts],
            "model": self.model,
            "input_type": input_type,  # 'passage' at indexing, 'query' at search time
            "encoding_format": "float",
            "truncate": "END",
        }

        for attempt in range(3):
            resp = requests.post(self.endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code == 200:
                data = resp.json()["data"]
                # Ensure vectors are returned in exact input order
                data_sorted = sorted(data, key=lambda x: x["index"])
                return [item["embedding"] for item in data_sorted]

            # Wait briefly and retry on transient 500 / 429 from NVIDIA free tier
            time.sleep(1.5 * (attempt + 1))

        # If a batch still fails with 500, fall back to embedding one by one to isolate any problematic chunk
        if len(texts) > 1:
            results = []
            for single_t in texts:
                results.extend(self._call_nim([single_t], input_type=input_type))
            return results

        raise RuntimeError(
            f"NVIDIA Embeddings API error [{resp.status_code}] on model '{self.model}': {resp.text}"
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        all_vectors: List[List[float]] = []
        total = len(texts)
        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            print(f"  -> Embedding batch {i // self.batch_size + 1} ({min(i + self.batch_size, total)}/{total} chunks)...")
            vectors = self._call_nim(batch, input_type="passage")
            all_vectors.extend(vectors)
        return all_vectors

    def embed_query(self, text: str) -> List[float]:
        return self._call_nim([text], input_type="query")[0]


class AIProviderFactory:
    @staticmethod
    def get_llm(temperature: float = 0.1):
        if settings.AI_PROVIDER == "nvidia":
            return ChatNVIDIA(
                model=settings.NVIDIA_LLM_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                temperature=temperature,
            )
        return AzureChatOpenAI(
            azure_deployment=settings.AZURE_CHAT_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            temperature=temperature,
        )

    @staticmethod
    def get_embeddings() -> Embeddings:
        # Category 1: Uses matching embedding model with passage/query asymmetry
        if settings.AI_PROVIDER == "nvidia":
            return NVIDIANemotronEmbeddings(
                model=settings.NVIDIA_EMBED_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                batch_size=8,
            )
        return AzureOpenAIEmbeddings(
            azure_deployment=settings.AZURE_EMBED_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
        )

    @staticmethod
    def get_reranker():
        if settings.AI_PROVIDER == "nvidia":
            return NVIDIANemotronReranker(
                model=settings.NVIDIA_RERANK_MODEL,
                api_key=settings.NVIDIA_API_KEY,
                top_n=4,
            )
        return None

    @staticmethod
    def get_vectorstore(initial_docs: list[Document] | None = None):
        embeddings = AIProviderFactory.get_embeddings()

        if settings.AI_PROVIDER == "nvidia":
            index_path = settings.VECTOR_DB_PATH

            if os.path.exists(os.path.join(index_path, "index.faiss")):
                vectorstore = FAISS.load_local(
                    folder_path=index_path,
                    embeddings=embeddings,
                    allow_dangerous_deserialization=True,
                )
                if initial_docs:
                    vectorstore.add_documents(initial_docs)
                    vectorstore.save_local(index_path)
                return vectorstore

            if initial_docs:
                vectorstore = FAISS.from_documents(initial_docs, embeddings)
                vectorstore.save_local(index_path)
                return vectorstore

            return None

        return AzureSearch(
            azure_search_endpoint=settings.AZURE_SEARCH_ENDPOINT,
            azure_search_key=settings.AZURE_SEARCH_KEY,
            index_name=settings.AZURE_SEARCH_INDEX_NAME,
            embedding_function=embeddings.embed_query,
        )

class NVIDIANemotronReranker(BaseDocumentCompressor):
    """
    Resilient LangChain Document Compressor for NVIDIA Reranking NIMs.
    Supports nvidia/llama-3.2-nv-rerankqa-1b-v2 and nvidia/nemotron-3.5-rerank-8b.
    Automatically falls back to top_n base retrieval order if the NIM endpoint is unreachable.
    """
    model: str
    api_key: str
    top_n: int = 4

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Callbacks | None = None,
    ) -> Sequence[Document]:
        if not documents:
            return []

        # NVIDIA hosts reranking endpoints under model-specific paths on ai.api.nvidia.com
        model_slug = self.model
        url = f"https://ai.api.nvidia.com/v1/retrieval/{model_slug}/reranking"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "query": {"text": query[:2000]},
            "passages": [{"text": d.page_content[:2000]} for d in documents],
            "truncate": "END",
        }

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                rankings = resp.json().get("rankings", [])
                # Sort by logit score descending and select top_n
                rankings_sorted = sorted(rankings, key=lambda x: x.get("logit", 0.0), reverse=True)
                reranked_docs: list[Document] = []
                for item in rankings_sorted[: self.top_n]:
                    idx = item["index"]
                    if 0 <= idx < len(documents):
                        doc = documents[idx]
                        doc.metadata["rerank_score"] = round(float(item.get("logit", 0.0)), 4)
                        reranked_docs.append(doc)
                if reranked_docs:
                    return reranked_docs
        except Exception as e:
            print(f"[Reranker Warning] Falling back to Hybrid MMR order ({str(e)})")

        # Graceful fallback so retrieval never crashes if a preview reranker model is rate-limited
        return list(documents[: self.top_n])