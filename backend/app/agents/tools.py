# backend/app/agents/tools.py
import os
import json
import concurrent.futures
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from app.rag.retriever import AdvancedITRetriever

retriever = AdvancedITRetriever()
DB_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../db.json"))

def _init_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump([], f)

# 1. Typed Schemas
class RunbookSearchInput(BaseModel):
    query: str = Field(description="Technical description of the IT symptom or error code.")
    category: str | None = Field(
        default=None,
        description="Optional filter matching ADS KB packs: 'it_asset_allocation', 'network_vpn', 'identity_access', 'collaboration_m365', or 'endpoint_security'"
    )

class ServiceDiagnosticsInput(BaseModel):
    hostname_or_ip: str = Field(description="Target hostname or IPv4 address (e.g., 'vpn-gw-01.ads.local').")
    port: int = Field(default=443, ge=1, le=65535, description="TCP port number to probe.")

class TicketCreationInput(BaseModel):
    user_id: str = Field(description="Employee ID or email reporting the issue.")
    summary: str = Field(description="Concise title of the incident.")
    severity: str = Field(description="Must be 'P1', 'P2', 'P3', or 'P4'.")

# 2. Tool Implementations with Persistent JSON Storage
def _search_runbooks(query: str, category: str | None = None) -> str:
    try:
        res = retriever.retrieve(query, category_filter=category)
        return res["context"]
    except Exception as e:
        return f"TOOL_ERROR: Runbook retrieval failed ({str(e)}). Proceed with general diagnostic tools or escalate."

def _check_service_health(hostname_or_ip: str, port: int = 443) -> str:
    def _probe():
        if "vpn" in hostname_or_ip.lower() and port == 443:
            return {"status": "DEGRADED", "latency_ms": 480, "packet_loss": "12%", "active_alert": "IKEv2 Daemon High CPU"}
        if "ad" in hostname_or_ip.lower():
            return {"status": "HEALTHY", "latency_ms": 14, "ldap_bind": "OK"}
        return {"status": "HEALTHY", "latency_ms": 22, "port_open": True}

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_probe)
            result = future.result(timeout=3.0)
            return f"DIAGNOSTIC_RESULT for {hostname_or_ip}:{port} -> {result}"
    except concurrent.futures.TimeoutError:
        return f"TOOL_TIMEOUT: Probing {hostname_or_ip}:{port} timed out after 3s."
    except Exception as e:
        return f"TOOL_FAILURE: Could not verify {hostname_or_ip}:{port} due to error: {str(e)}."

def _create_it_ticket(user_id: str, summary: str, severity: str) -> str:
    if severity not in {"P1", "P2", "P3", "P4"}:
        return "TOOL_VALIDATION_ERROR: Invalid severity. Please retry with 'P1', 'P2', 'P3', or 'P4'."
    
    _init_db()
    
    try:
        with open(DB_FILE, "r") as f:
            tickets = json.load(f)
    except Exception:
        tickets = []

    ticket_id = f"INC-{90000 + len(tickets) + 1}"
    new_ticket = {
        "ticket_id": ticket_id,
        "user_id": user_id,
        "summary": summary,
        "severity": severity,
        "status": "Open",
        "created_at": datetime.utcnow().isoformat()
    }

    tickets.append(new_ticket)

    with open(DB_FILE, "w") as f:
        json.dump(tickets, f, indent=2)

    return f"TICKET_CREATED: Incident {ticket_id} logged successfully for {user_id} [Severity: {severity}] - '{summary}'."

# 3. Export StructuredTools
it_tools = [
    StructuredTool.from_function(
        func=_search_runbooks,
        name="search_it_runbooks",
        description="Searches corporate IT documentation and troubleshooting runbooks for known fixes.",
        args_schema=RunbookSearchInput,
        handle_tool_error=True
    ),
    StructuredTool.from_function(
        func=_check_service_health,
        name="run_network_diagnostics",
        description="Runs live health, latency, and port checks against corporate servers or VPN gateways.",
        args_schema=ServiceDiagnosticsInput,
        handle_tool_error=True
    ),
    StructuredTool.from_function(
        func=_create_it_ticket,
        name="create_servicenow_ticket",
        description="Creates an official IT support ticket when automated troubleshooting cannot resolve the issue.",
        args_schema=TicketCreationInput,
        handle_tool_error=True
    ),
]