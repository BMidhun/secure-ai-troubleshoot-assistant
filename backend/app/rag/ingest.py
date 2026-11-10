# backend/app/rag/ingest.py
import os
import re
import pymupdf4llm
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.core.provider_factory import AIProviderFactory

def extract_metadata_from_markdown(md_text: str, filename: str) -> dict:
    """Extracts Document ID and Issue Category directly from the converted PDF Markdown."""
    doc_id_match = re.search(r"(ADS-KB-[A-Z0-9]+-\d+)", md_text)
    doc_id = doc_id_match.group(1) if doc_id_match else filename.replace(".pdf", "")

    category_map = {
        "ASSET": "it_asset_allocation",
        "NET": "network_vpn",
        "IAM": "identity_access",
        "M365": "collaboration_m365",
        "SEC": "endpoint_security",
    }
    category = "general_it"
    for key, val in category_map.items():
        if f"-{key}-" in doc_id:
            category = val
            break

    return {"doc_id": doc_id, "source": f"{doc_id}.pdf", "category": category}

def ingest_pdf_directory(pdf_dir: str = "./data/kb_pdfs") -> dict:
    headers_to_split_on = [
        ("#", "Header_1"),
        ("##", "Header_2"),
        ("###", "Header_3"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n|", "\n", " "]
    )

    all_chunks: list[Document] = []
    files_processed = []

    for fname in sorted(os.listdir(pdf_dir)):
        if not fname.lower().endswith(".pdf"):
            continue
        pdf_path = os.path.join(pdf_dir, fname)

        # 1. Convert digital PDF to Markdown (disable image extraction to avoid OCR overhead)
        md_text = pymupdf4llm.to_markdown(pdf_path, write_images=False)
        base_meta = extract_metadata_from_markdown(md_text, fname)

        # 2. Boundary-aware split by Markdown headers & table boundaries
        header_splits = md_splitter.split_text(md_text)
        for i, split in enumerate(header_splits):
            sub_chunks = text_splitter.split_text(split.page_content)
            for j, chunk_str in enumerate(sub_chunks):
                cleaned_chunk = chunk_str.strip()
                # Skip empty or ultra-short artifacts that cause NVIDIA API 500 errors
                if len(cleaned_chunk) < 15:
                    continue

                # Clean metadata values (ensure no None values for FAISS/Azure compatibility)
                clean_split_meta = {k: str(v) for k, v in split.metadata.items() if v is not None}
                chunk_meta = {
                    **base_meta,
                    **clean_split_meta,
                    "chunk_id": f"{base_meta['doc_id']}_s{i}_c{j}"
                }
                all_chunks.append(Document(page_content=cleaned_chunk, metadata=chunk_meta))
        files_processed.append(fname)

    # 3. Store in FAISS
    if all_chunks:
        print(f"Embedding {len(all_chunks)} chunks....")
        AIProviderFactory.get_vectorstore(initial_docs=all_chunks)

    return {
        "files_processed": files_processed,
        "total_chunks_indexed": len(all_chunks)
    }

if __name__ == "__main__":
    stats = ingest_pdf_directory()
    print(f"Ingestion complete: {stats}")