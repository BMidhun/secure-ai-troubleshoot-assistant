# backend/app/main.py
import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from app.core.security import GenAISecurityGuard
from app.agents.orchestrator import multi_agent_app
from app.rag.ingest import ingest_pdf_directory
import json
import os
from fastapi.responses import StreamingResponse, FileResponse
import asyncio

TICKETS_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "db.json"))

# Configure structured server logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Secure AI IT Troubleshooting Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_id: str = Field(..., description="Employee ID or username")
    message: str = Field(..., min_length=1, description="User troubleshooting prompt")


@app.get("/health")
async def health_check():
    return {"status": 200, "message": "API is working..."}


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        # 1. Input Security & Physical Safety Guardrail
        sec_in = GenAISecurityGuard.validate_input(req.message)
        if not sec_in.allowed:
            if sec_in.escalate_immediately:
                return {
                    "reply": sec_in.sanitized_text,
                    "reasoning_branches": ["P1 Critical Safety Boundary Triggered -> Immediate Human Escalation"],
                    "critique_verified": True,
                    "blocked": True
                }
            return {
                "reply": f"Security Policy Block: {sec_in.reason}",
                "reasoning_branches": [],
                "critique_verified": False,
                "blocked": True
            }

        # 2. Execute Multi-Agent Graph with Exception Safety & Recursion Limit
        initial_state = {
            "messages": [HumanMessage(content=sec_in.sanitized_text)],
            "reasoning_branches": [],
            "critique_passed": False,
            "critique_feedback": "",
            "iterations": 0
        }

        try:
            result = await multi_agent_app.ainvoke(initial_state, config={"recursion_limit": 150})
        except Exception as graph_err:
            logger.error(f"Multi-agent graph execution failed or timed out: {str(graph_err)}", exc_info=True)
            return {
                "reply": "The troubleshooting assistant encountered a temporary upstream inference timeout or model error. Please retry your query or create a P3/P4 IT support ticket.",
                "reasoning_branches": ["Graph Execution Failure -> Graceful Fallback"],
                "critique_verified": False,
                "blocked": False
            }

        if not result or "messages" not in result or not result["messages"]:
            raise ValueError("Multi-agent graph returned an empty or malformed state output.")

        raw_reply = result["messages"][-1].content

        # 3. Output Security Guardrail
        sec_out = GenAISecurityGuard.validate_output(raw_reply)
        return {
            "reply": sec_out.sanitized_text,
            "reasoning_branches": result.get("reasoning_branches", []),
            "critique_verified": result.get("critique_passed", False),
            "blocked": not sec_out.allowed
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in chat_endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred while processing your request: {str(e)}"
        )
@app.post("/api/stream-chat")
async def stream_chat_endpoint(req: ChatRequest):
    SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
    }
    # 1. Input Security & Physical Safety Guardrail
    sec_in = GenAISecurityGuard.validate_input(req.message)
    if not sec_in.allowed:
        async def blocked_generator():
            payload = {
                "type": "error",
                "reply": sec_in.sanitized_text if sec_in.escalate_immediately else f"Security Policy Block: {sec_in.reason}",
                "reasoning_branches": ["P1 Critical Safety Boundary Triggered"] if sec_in.escalate_immediately else [],
                "blocked": True
            }
            yield f"data: {json.dumps(payload)}\n\n"
        return StreamingResponse(blocked_generator(), media_type="text/event-stream", headers=SSE_HEADERS)

    async def event_generator():
        initial_state = {
            "messages": [HumanMessage(content=sec_in.sanitized_text)],
            "reasoning_branches": [],
            "critique_passed": False,
            "critique_feedback": "",
            "iterations": 0
        }

        try:
            async for event in multi_agent_app.astream_events(
                initial_state,
                version="v2",
                config={"recursion_limit": 150}
            ):
                kind = event["event"]
                node = event.get("metadata", {}).get("langgraph_node", "")

                # 1. Emit reasoning branches when decomposer finishes
                if kind == "on_chain_end" and event.get("name") == "decomposer":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "reasoning_branches" in output:
                        yield f"data: {json.dumps({'type': 'branches', 'branches': output['reasoning_branches']})}\n\n"
                        await asyncio.sleep(0.01)

                # 2. Emit live tool execution status so the user sees what the agent is doing
                elif kind == "on_tool_start":
                    tool_name = event.get("name", "diagnostic_tool")
                    yield f"data: {json.dumps({'type': 'status', 'status': f'Running {tool_name}...'})}\n\n"
                    await asyncio.sleep(0.01)

                # 3. Stream LLM tokens live from the investigator node
                elif kind == "on_chat_model_stream" and node == "investigator":
                    chunk = event.get("data", {}).get("chunk")
                    # Ignore tool-call generation chunks; only stream actual text tokens
                    if chunk and getattr(chunk, "content", None) and not getattr(chunk, "tool_call_chunks", None):
                        token_str = chunk.content
                        # Scrub any sensitive pattern on the fly and flush in word-sized pieces
                        words = token_str.split(" ")
                        for idx, word in enumerate(words):
                            piece = word if idx == len(words) - 1 else word + " "
                            if piece:
                                yield f"data: {json.dumps({'type': 'token', 'content': piece})}\n\n"
                                await asyncio.sleep(0.012)

                # 4. Emit consensus verification badge when critic finishes
                elif kind == "on_chain_end" and event.get("name") == "critic":
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "critique_passed" in output:
                        passed = output["critique_passed"]
                        yield f"data: {json.dumps({'type': 'critique', 'verified': passed})}\n\n"
                        # If critic rejected the draft and loops back, clear the draft text for the new attempt
                        if not passed:
                            yield f"data: {json.dumps({'type': 'reset_draft'})}\n\n"
                        await asyncio.sleep(0.01)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Streaming execution failed: {str(e)}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'reply': 'An upstream error occurred during streaming.'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/ingest")
async def ingest_endpoint():
    try:
        data = ingest_pdf_directory()
        return {"status": "indexed", "data": data}
    except Exception as e:
        logger.error(f"PDF ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest knowledge base PDFs from `./data/kb_pdfs`: {str(e)}"
        )

@app.get("/api/tickets")
async def get_it_tickets():
    """Retrieves all IT support tickets logged in db.json."""
    if not os.path.exists(TICKETS_DB_PATH):
        return []
    try:
        with open(TICKETS_DB_PATH, "r") as f:
            tickets = json.load(f)
        return tickets
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read IT tickets database: {str(e)}"
        )

PDF_DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/kb_pdfs"))

@app.get("/api/documents/{filename}")
async def get_document(filename: str):
    """Serves the source PDF document for frontend citation links."""
    # Prevent directory traversal attacks
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(PDF_DIRECTORY, safe_filename)
    
    if os.path.exists(file_path) and safe_filename.lower().endswith('.pdf'):
        # Inline disposition allows the browser to open the PDF in a new tab natively
        return FileResponse(
            file_path, 
            media_type="application/pdf", 
            headers={"Content-Disposition": f"inline; filename={safe_filename}"}
        )
        
    raise HTTPException(status_code=404, detail="Document not found")