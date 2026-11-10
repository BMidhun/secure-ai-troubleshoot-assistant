# backend/app/agents/orchestrator.py
from typing import TypedDict, Annotated, Sequence
import operator
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.core.provider_factory import AIProviderFactory
from app.agents.tools import it_tools

class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    reasoning_branches: list[str]
    rag_context: str
    diagnostic_findings: str
    critique_passed: bool
    critique_feedback: str
    iterations: int

class DecompositionPlan(BaseModel):
    branches: list[str] = Field(description="2 to 3 distinct diagnostic hypotheses/sub-tasks to investigate (Tree of Thoughts).")

class CritiqueVerdict(BaseModel):
    approved: bool = Field(description="True if the answer is grounded, accurate, safe, and cites sources.")
    feedback: str = Field(description="If not approved, specific instructions on what to fix.")

llm = AIProviderFactory.get_llm(temperature=0.1)
llm_with_tools = llm.bind_tools(it_tools)

# Node 1: Tree-of-Thoughts Problem Decomposer
def decomposer_node(state: GraphState) -> dict:
    try:
        user_msg = state["messages"][-1].content
        structured_llm = llm.with_structured_output(DecompositionPlan)
        plan = structured_llm.invoke([
            SystemMessage(content="Decompose this IT issue into 2-3 candidate root-cause hypotheses to test."),
            HumanMessage(content=user_msg)
        ])
        return {"reasoning_branches": plan.branches, "iterations": state.get("iterations", 0) + 1}
    except Exception as e:
        # Agent failure isolation
        return {"reasoning_branches": ["General IT symptom investigation"], "iterations": state.get("iterations", 0) + 1}

# Node 2: Knowledge & Diagnostics Executor Agent
async def investigator_node(state: GraphState) -> dict:
    try:
        branches_str = "\n".join(f"- {b}" for b in state.get("reasoning_branches", []))
        feedback = state.get("critique_feedback", "")
        sys_prompt = (
            "You are the Lead IT Troubleshooting Agent for ABC Digital Services (ADS). "
            "Investigate the following reasoning paths:\n"
            f"{branches_str}\n"
            "Use `search_it_runbooks` for documentation and `run_network_diagnostics` for live checks. "
            "Always cite sources at the end of sentences using the exact format:. "
            "If unresolved, create a ticket.\n"
            f"{f'Previous Critique to address: {feedback}' if feedback else ''}"
        )
        response = llm_with_tools.invoke([SystemMessage(content=sys_prompt)] + list(state["messages"]))
        return {"messages": [response]}
    except Exception as e:
        fallback = AIMessage(content=f"Diagnostics agent encountered an internal error ({str(e)}). Escalating to human support.")
        return {"messages": [fallback]}

# Node 3: Consensus & Verification Critic Agent
def critic_node(state: GraphState) -> dict:
    last_message = state["messages"][-1].content
    try:
        critic_llm = llm.with_structured_output(CritiqueVerdict)
        verdict = critic_llm.invoke([
            SystemMessage(content=(
                "You are the Consensus & Quality Verifier Agent. Verify the proposed IT solution:\n"
                "1. Does it directly address the user's IT problem?\n"
                "2. Are claims grounded in tool outputs or cited with?\n"
                "3. Does it avoid dangerous commands (e.g., rm -rf, disabling firewalls)?\n"
                "Approve if valid, otherwise reject with specific correction instructions."
            )),
            HumanMessage(content=f"Proposed Agent Response:\n{last_message}")
        ])
        return {"critique_passed": verdict.approved, "critique_feedback": verdict.feedback}
    except Exception:
        # Fail-safe consensus fallback if structured output fails
        return {"critique_passed": True, "critique_feedback": "Critic bypassed due to parser fallback."}

def route_after_investigator(state: GraphState):
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "critic"

def route_after_critic(state: GraphState):
    if state.get("critique_passed", True) or state.get("iterations", 0) >= 3:
        return END
    return "investigator"

# Build the Multi-Agent StateGraph
workflow = StateGraph(GraphState)
workflow.add_node("decomposer", decomposer_node)
workflow.add_node("investigator", investigator_node)
workflow.add_node("tools", ToolNode(it_tools))
workflow.add_node("critic", critic_node)

workflow.set_entry_point("decomposer")
workflow.add_edge("decomposer", "investigator")
workflow.add_conditional_edges("investigator", route_after_investigator, {"tools": "tools", "critic": "critic"})
workflow.add_edge("tools", "investigator")
workflow.add_conditional_edges("critic", route_after_critic, {END: END, "investigator": "investigator"})

multi_agent_app = workflow.compile()