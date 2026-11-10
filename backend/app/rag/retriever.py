# backend/app/rag/retriever.py
from langchain_classic.retrievers import EnsembleRetriever, ContextualCompressionRetriever
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.core.provider_factory import AIProviderFactory

class AdvancedITRetriever:
    def __init__(self):
        self.llm = AIProviderFactory.get_llm(temperature=0.0)
        self.reranker = AIProviderFactory.get_reranker()

    def rewrite_query(self, user_query: str) -> str:
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Rewrite the user's IT issue into a precise technical search query for corporate runbooks. Return ONLY the rewritten query."),
            ("human", "{query}")
        ])
        chain = prompt | self.llm | StrOutputParser()
        return chain.invoke({"query": user_query}).strip()

    def retrieve(self, query: str, category_filter: str | None = None) -> dict:
        vectorstore = AIProviderFactory.get_vectorstore()
        if vectorstore is None:
            return {
                "found": False,
                "context": "FALLBACK_NO_DOCS: Vector index is empty. Please ingest runbooks first.",
                "sources": []
            }

        rewritten_query = self.rewrite_query(query)

        # 1. Dense FAISS Retriever with MMR + Metadata Filtering
        search_kwargs = {"k": 8, "fetch_k": 20, "lambda_mult": 0.7}
        if category_filter:
            search_kwargs["filter"] = {"category": category_filter}

        dense_retriever = vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs=search_kwargs
        )

        # 2. Hybrid Search: Combine Sparse BM25 + Dense FAISS MMR
        if hasattr(vectorstore, "docstore") and hasattr(vectorstore.docstore, "_dict"):
            all_docs = list(vectorstore.docstore._dict.values())
            if category_filter:
                all_docs = [d for d in all_docs if d.metadata.get("category") == category_filter]
        else:
            all_docs = []

        if all_docs:
            bm25_retriever = BM25Retriever.from_documents(all_docs, k=8)
            base_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, dense_retriever],
                weights=[0.35, 0.65]
            )
        else:
            base_retriever = dense_retriever

        # 3. Cross-Encoder Reranking (NVIDIA Nemotron Reranker)
        if self.reranker:
            compression_retriever = ContextualCompressionRetriever(
                base_compressor=self.reranker,
                base_retriever=base_retriever
            )
            docs = compression_retriever.invoke(rewritten_query)
        else:
            docs = base_retriever.invoke(rewritten_query)

        if not docs:
            return {
                "found": False,
                "context": "FALLBACK_NO_DOCS: No matching corporate IT runbooks found.",
                "sources": []
            }

        formatted_context = "\n\n".join([
            f"[Source: {d.metadata.get('source', 'Unknown')} | Section: {d.metadata.get('Header_2', 'General')}]\n{d.page_content}"
            for d in docs
        ])
        sources = list({d.metadata.get("source", "Unknown") for d in docs})
        return {
            "found": True,
            "context": formatted_context,
            "sources": sources,
            "rewritten_query": rewritten_query
        }