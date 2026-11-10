# 1. Setup

### Prerequisites

- **Python 3.10 to 3.15** installed
- Azure credentials

### Environment Strategy

This project is built exclusively for the **Azure AI Ecosystem**. For data storage and retrieval:

- **Local Development:** The system utilizes a local **FAISS** vector index.
- **Higher Environments (Staging/Production):** The system transitions seamlessly to **Azure AI Search** for enterprise-scale retrieval.

### Installation Steps

1. **Navigate to the backend directory:**

   ```bash
   cd backend
   ```

2. **Create a Python virtual environment:**
   - **On Windows:**
     ```bash
     python -m venv .venv
     ```
   - **On macOS / Linux:**
     ```bash
     python3 -m venv .venv
     ```

3. **Activate the virtual environment:**
   - **On Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **On Windows (Command Prompt):**
     ```cmd
     .venv\Scripts\activate.bat
     ```
   - **On macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies from `requirements.txt`:**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Configure Environment Variables:**
   Create a `.env` file in the root of the `backend/` directory with the following contents:

   ```ini
   # Provider Toggle: "local" (FAISS for development) or "azure" (Azure AI Search for higher environments)
   AI_PROVIDER=azure
   VECTOR_DB_PATH=./faiss_index

   # Azure OpenAI Configuration
   AZURE_OPENAI_API_KEY=
   AZURE_OPENAI_ENDPOINT=
   AZURE_OPENAI_API_VERSION=
   AZURE_CHAT_DEPLOYMENT=
   AZURE_EMBED_DEPLOYMENT=

   # Azure AI Search Configuration (Required for Higher Environments)
   AZURE_SEARCH_ENDPOINT=
   AZURE_SEARCH_KEY=
   AZURE_SEARCH_INDEX_NAME=
   ```

---

## 2. Scripts to Run and Their Purpose

Run all commands from the `backend/` directory with your virtual environment activated.

| Script / Command                                                                                                                                                                                                                                                                                              | Purpose                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **2.1. Generate Corporate Knowledge Base PDFs**<br>`python -m scripts.generate_kb_pdfs`                                                                                                                                                                                                                       | Generates 5 standardized ABC Digital Services (ADS) IT policy and troubleshooting PDF documents inside `data/kb_pdfs/` using ReportLab:<br>• `ADS-KB-ASSET-001.pdf` — Secondary Laptop Allocation and Return<br>• `ADS-KB-NET-002.pdf` — Corporate VPN Connectivity and Split-Tunnel Troubleshooting<br>• `ADS-KB-IAM-003.pdf` — Active Directory Account Lockout, MFA Reset, and Conditional Access<br>• `ADS-KB-M365-004.pdf` — Microsoft 365 Outlook OST Corruption and Sync<br>• `ADS-KB-SEC-005.pdf` — Endpoint BitLocker Recovery and CrowdStrike Quarantine |
| **2.2. Ingest PDFs and Build the Vector Index**<br>`python -m app.rag.ingest`                                                                                                                                                                                                                                 | Reads all PDFs in `data/kb_pdfs/`, converts tables and formatting into Markdown via `pymupdf4llm`, performs boundary-aware chunking with header metadata preservation, generates text embeddings via **Azure OpenAI (text-embedding-3-large)**, and persists the vector index locally into `./faiss_index/` (`index.faiss` and `index.pkl`) for local development, or uploads to **Azure AI Search** for higher environments.                                                                                                                                      |
| **2.4. Test RAG Retrieval, Query Rewriting, and Reranking**<br>`python -c "from app.rag.retriever import AdvancedITRetriever; r = AdvancedITRetriever(); res = r.retrieve('Can I give my secondary project laptop directly to a teammate?'); print('Sources:', res['sources']); print(res['context'][:400])"` | Performs an end-to-end test of the retrieval pipeline without starting the web server. It executes:<br>• Query rewriting via **Azure OpenAI**.<br>• Hybrid search combining dense vector matching and sparse keyword matching (utilizing FAISS locally or Azure AI Search in higher environments).<br>• Structured context extraction with source document references.                                                                                                                                                                                             |
| **2.5. Run Adversarial Security & Safety Unit Tests**<br>`python -m pytest -o pythonpath=. tests/test_security.py -v`                                                                                                                                                                                         | Runs 9 comprehensive security tests against `GenAISecurityGuard` covering:<br>• Prompt injection and instruction jailbreak prevention (DAN mode, XML delimiter escapes, system prompt exfiltration).<br>• Denied topic blocking (disabling antivirus/EDR, password cracking).<br>• PII and credential redaction (emails, bearer tokens, API keys, passwords).<br>• Dangerous system command sanitization (`rm -rf`, disk formatting).<br>• Immediate physical hardware hazard escalation (swollen battery, smoke, electrical shock).                               |
| **2.6. Run Statistical Pipeline Evaluation**<br>`python -m evaluation.evaluate_pipeline`                                                                                                                                                                                                                      | Evaluates the RAG and agent pipeline across multiple quality dimensions (Context Recall, Answer Faithfulness, Safety & Policy Compliance). It computes 95% Bootstrap Confidence Intervals ($B=1000$), performs Paired $t$-tests and Wilcoxon Signed-Rank tests ($p < 10^{-9}$), and saves a publication-ready comparative bar chart to `evaluation/eval_comparison.png`.                                                                                                                                                                                           |

### 2.3. Validate Azure API Connectivity

To inspect and verify that your Azure OpenAI service is reachable and functioning, use these diagnostic scripts:

- **Verify vector generation & embedding dimension:**
  ```bash
  python -c "from app.core.provider_factory import AIProviderFactory; e = AIProviderFactory.get_embeddings(); v = e.embed_query('test vpn'); print('Vector generated successfully! Dimension:', len(v))"
  ```

---

## 3. Running the Backend Application

Launch the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --reload --port 8000
```

The server will initialize at `http://localhost:8000`.

### Key Endpoints

- **Health Check:** `GET /health` — Verifies the API is online.
- **Stream Troubleshooting:** `POST /api/stream-chat` — Server-Sent Events (SSE) endpoint providing live token streaming, reasoning steps, tool statuses, and consensus verification badges via Azure OpenAI.
- **Standard Chat:** `POST /api/chat` — Synchronous chat endpoint.
- **Document Viewer:** `GET /api/documents/{filename}` — Serves source PDFs with `Content-Disposition: inline` so frontend citation chips can open referenced runbooks directly.
- **Incident Tickets:** `GET /api/tickets` — Lists all ServiceNow tickets generated and saved to `db.json`.
- **Knowledge Re-indexing:** `POST /api/ingest` — Triggers automated re-chunking and indexing of all PDFs in `data/kb_pdfs/`.
- **Interactive API Documentation:** Visit `http://localhost:8000/docs` (Swagger UI).
