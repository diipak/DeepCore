import time
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from deepcore.runtime.conversation.base import (
    ConversationRequest,
    ConversationResponse,
    ConversationMessage,
    ConversationStatus,
    ConversationDiagnostics,
    ConversationDescriptor,
    ConversationMode
)
from deepcore.runtime.planner.base import PlannerRequest, PlannerStatus, PlanStatus
from deepcore.runtime.planner.runtime import PlannerRuntime
from deepcore.intelligence import ContextEngine, ContextRequest


from deepcore.runtime.descriptors import DescriptorCategory

class ConversationRuntime:
    """
    Deterministic Conversation Runtime serving as the coordination gateway
    between API requests and the DeepCore Intelligence Stack.
    """
    def __init__(self, planner_runtime: PlannerRuntime):
        self.planner_runtime = planner_runtime

    def get_descriptor(self) -> ConversationDescriptor:
        """Returns the capability descriptor for Conversation Runtime."""
        return ConversationDescriptor(
            id="conversation_runtime",
            name="Conversation Runtime",
            description="Entry point to the DeepCore intelligence kernel",
            category=DescriptorCategory.CONVERSATION,
            supported_modes=[ConversationMode.DIRECT, ConversationMode.PLANNING],
            supports_context=True,
            supports_planning=True,
            supports_streaming=False,
            supports_models=[]
        )

    def execute(self, request: ConversationRequest, db: Session) -> ConversationResponse:
        """
        Executes a conversation message: validates request, builds context via ContextEngine,
        routes execution (direct or planning), and returns a ConversationResponse.
        """
        from deepcore.storage.sqlite.db import db_session_ctx
        token = db_session_ctx.set(db)
        try:
            start_time = time.perf_counter()
            context_retrieved = False
            planner_invoked = False
            planner_result = None
            artifacts = []
            error_message = None
            status = ConversationStatus.SUCCESS

            # 1. Decide and Orchestrate Context Engine
            # Context is compiled if trigger object is specified or mode is PLANNING
            if request.context_object_uuid or request.mode == ConversationMode.PLANNING:
                ctx_engine = ContextEngine(db)
                ctx_req = ContextRequest(
                    trigger_object_uuid=request.context_object_uuid,
                    query=request.message.content
                )
                # Invoke Context Engine
                context_package = ctx_engine.build_context(ctx_req)
                context_retrieved = True
                
                # Map context package details to artifacts if appropriate (reserved space)
                # E.g., we can append the context package as an execution artifact mapping if desired.

            # 2. Route Execution based on Mode
            if request.mode == ConversationMode.DIRECT:
                # DIRECT Mode: Bypass Planner entirely
                response_content = f"Echo: {request.message.content}"
                response_message = ConversationMessage(
                    role="assistant",
                    content=response_content,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                # PLANNING Mode: Delegate plan construction and execute via Planner
                planner_invoked = True
                plan = self.planner_runtime.build_plan_for_goal(request.message.content)
                
                planner_req = PlannerRequest(
                    request_id=f"conv-{request.conversation_id}",
                    plan=plan
                )
                planner_result = self.planner_runtime.execute(planner_req)
                
                if planner_result.status == PlannerStatus.SUCCESS:
                    # Find output from the final step of the plan
                    last_step = planner_result.plan.steps[-1] if planner_result.plan.steps else None
                    if last_step and last_step.outputs:
                        res_val = last_step.outputs.get("result") or last_step.outputs.get("processed_results")
                        response_content = str(res_val) if res_val is not None else "Plan executed successfully."
                    else:
                        response_content = "Plan executed successfully with no output."
                    
                    # Gather step artifacts
                    for step in planner_result.plan.steps:
                        artifacts.extend(step.artifacts)
                else:
                    status = ConversationStatus.FAILURE
                    error_message = planner_result.error_message or "Planner execution failed."
                    response_content = f"Execution failed: {error_message}"

                response_message = ConversationMessage(
                    role="assistant",
                    content=response_content,
                    timestamp=datetime.now(timezone.utc)
                )

            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            
            return ConversationResponse(
                conversation_id=request.conversation_id,
                status=status,
                response_message=response_message,
                planner_result=planner_result,
                artifacts=artifacts,
                diagnostics=ConversationDiagnostics(
                    execution_time_ms=execution_time_ms,
                    context_retrieved=context_retrieved,
                    planner_invoked=planner_invoked
                ),
                error_message=error_message
            )
        finally:
            try:
                db_session_ctx.reset(token)
            except ValueError:
                pass
