import asyncio
import logging
import time
from typing import Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.profile_collector import ProfileCollectorAgent
from agents.profile_analyzer import ProfileAnalyzerAgent
from agents.content_generator import ContentGeneratorAgent
from utils.dynamodb_storage import storage
from config import config

logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State object for the LinkedIn Profile Optimizer workflow."""
    pdf_path: Optional[str]
    pdf_bytes: Optional[bytes]
    target_role: Optional[str]
    profile_data: Optional[Dict[str, Any]]
    analysis_results: Optional[Dict[str, Any]]
    content_results: Optional[Dict[str, Any]]
    final_results: Optional[Dict[str, Any]]
    error: Optional[str]
    status: str
    request_id: Optional[str]
    api_key: Optional[str]
    step_timings: Optional[Dict[str, float]]


class LinkedInOptimizerWorkflow:
    """LangGraph workflow orchestrating the LinkedIn Profile Optimizer agents."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the workflow with optional API key.

        Args:
            api_key: Optional OpenAI API key to use (overrides config)
        """
        self.api_key = api_key
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""

        # Create the workflow graph
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("collect_profile", self._collect_profile_node)
        workflow.add_node("analyze_profile", self._analyze_profile_node)
        workflow.add_node("generate_content", self._generate_content_node)
        workflow.add_node("compile_results", self._compile_results_node)

        # Define the workflow edges with conditional error handling
        workflow.set_entry_point("collect_profile")

        # After profile collection, check for critical errors
        workflow.add_conditional_edges(
            "collect_profile",
            self._should_continue,
            {
                "continue": "analyze_profile",
                "stop": "compile_results"
            }
        )

        # After profile analysis, check for critical errors
        workflow.add_conditional_edges(
            "analyze_profile",
            self._should_continue,
            {
                "continue": "generate_content",
                "stop": "compile_results"
            }
        )

        # After content generation, always compile results
        workflow.add_edge("generate_content", "compile_results")
        workflow.add_edge("compile_results", END)

        return workflow.compile(checkpointer=MemorySaver())

    def _should_continue(self, state: WorkflowState) -> str:
        """
        Determine if workflow should continue or stop due to critical error.

        Critical errors include:
        - Authentication/API key errors
        - Invalid credentials
        - Rate limiting issues
        - Other unrecoverable errors
        """
        error = state.get("error", "")

        if not error:
            return "continue"

        # Check for critical error indicators
        critical_keywords = [
            "api key",
            "authentication",
            "unauthorized",
            "invalid_api_key",
            "invalid_request_error",
            "rate_limit",
            "quota_exceeded",
            "insufficient_quota",
            "billing",
            "permission denied",
            "forbidden"
        ]

        error_lower = error.lower()
        is_critical = any(keyword in error_lower for keyword in critical_keywords)

        if is_critical:
            request_id = state.get("request_id", "unknown")
            logger.error(f"[CRITICAL] [REQ:{request_id}] Critical error detected, stopping workflow: {error}")
            state["status"] = "Stopped due to critical error"
            return "stop"

        # Non-critical errors: continue to next step (skip current step but try others)
        return "continue"

    async def _collect_profile_node(self, state: WorkflowState) -> WorkflowState:
        """Node for collecting profile data from PDF."""
        request_id = state.get("request_id", "unknown")
        api_key = state.get("api_key") or self.api_key
        step_start = time.time()

        logger.info(f"[INFO] [REQ:{request_id}] Starting Profile Collector Agent...")

        try:
            state["status"] = "Extracting profile data from PDF..."

            # Initialize agent with API key
            profile_collector = ProfileCollectorAgent(api_key=api_key)

            if state.get("pdf_bytes"):
                logger.info(f"[INFO] [REQ:{request_id}] Processing PDF from bytes ({len(state['pdf_bytes'])} bytes)")
                profile_data = await profile_collector.extract_profile_data_from_bytes(
                    state["pdf_bytes"], request_id
                )
            elif state.get("pdf_path"):
                logger.info(f"[INFO] [REQ:{request_id}] Processing PDF from path: {state['pdf_path']}")
                profile_data = await profile_collector.extract_profile_data(
                    state["pdf_path"], request_id
                )
            else:
                raise ValueError("No PDF data provided (neither path nor bytes)")

            state["profile_data"] = profile_data
            state["status"] = "Profile data extracted successfully"

            step_time = time.time() - step_start
            if not state.get("step_timings"):
                state["step_timings"] = {}
            state["step_timings"]["profile_collection"] = step_time

            logger.info(f"[OK] [REQ:{request_id}] Profile collection completed in {step_time:.2f}s")
            logger.info(f"[INFO] [REQ:{request_id}] Extracted sections: {list(profile_data.keys())}")

            # Save step progress immediately
            progress_saved = await storage.save_step_progress(
                optimization_id=request_id,
                step_name="profile_extraction",
                step_data={
                    'duration': step_time,
                    'sections_extracted': list(profile_data.keys()),
                    'data_quality': 'good' if len(profile_data) > 3 else 'limited'
                },
                status="processing"
            )

            if not progress_saved:
                logger.warning(f"[WARN] [REQ:{request_id}] Failed to save profile_extraction progress to DynamoDB")

        except Exception as e:
            step_time = time.time() - step_start
            state["error"] = f"Error in profile collection: {str(e)}"
            state["status"] = "Failed to extract profile data"
            logger.error(f"[ERROR] [REQ:{request_id}] Profile collection failed after {step_time:.2f}s: {str(e)}")

            # Save failed status to DynamoDB
            await storage.save_step_progress(
                optimization_id=request_id,
                step_name="profile_extraction",
                step_data={
                    'duration': step_time,
                    'error': str(e)
                },
                status="failed"
            )

        return state

    async def _analyze_profile_node(self, state: WorkflowState) -> WorkflowState:
        """Node for analyzing profile data."""
        request_id = state.get("request_id", "unknown")
        api_key = state.get("api_key") or self.api_key
        step_start = time.time()

        logger.info(f"[INFO] [REQ:{request_id}] Starting Profile Analyzer Agent...")

        try:
            if state.get("error"):
                logger.warning(f"[WARN] [REQ:{request_id}] Skipping analysis due to previous error: {state['error']}")
                return state

            state["status"] = "Analyzing profile for optimization opportunities..."

            if not state.get("profile_data"):
                raise ValueError("No profile data available for analysis")

            logger.info(f"[INFO] [REQ:{request_id}] Analyzing profile for target role: {state.get('target_role', 'General')}")

            # Initialize agent with API key
            profile_analyzer = ProfileAnalyzerAgent(api_key=api_key)

            analysis_results = await profile_analyzer.analyze_profile(
                state["profile_data"],
                state.get("target_role"),
                request_id
            )

            state["analysis_results"] = analysis_results
            state["status"] = "Profile analysis completed"

            step_time = time.time() - step_start
            if not state.get("step_timings"):
                state["step_timings"] = {}
            state["step_timings"]["profile_analysis"] = step_time

            logger.info(f"[OK] [REQ:{request_id}] Profile analysis completed in {step_time:.2f}s")
            logger.info(f"[INFO] [REQ:{request_id}] Analysis score: {analysis_results.get('overall_score', 'N/A')}/100")

            # Save step progress immediately
            progress_saved = await storage.save_step_progress(
                optimization_id=request_id,
                step_name="profile_analysis",
                step_data={
                    'duration': step_time,
                    'overall_score': analysis_results.get('overall_score', 0),
                    'strengths_count': len(analysis_results.get('strengths', [])),
                    'improvements_count': len(analysis_results.get('areas_for_improvement', [])),
                    'recommendations_generated': bool(analysis_results.get('recommendations'))
                },
                status="processing"
            )

            if not progress_saved:
                logger.warning(f"[WARN] [REQ:{request_id}] Failed to save profile_analysis progress to DynamoDB")

        except Exception as e:
            step_time = time.time() - step_start
            state["error"] = f"Error in profile analysis: {str(e)}"
            state["status"] = "Failed to analyze profile"
            logger.error(f"[ERROR] [REQ:{request_id}] Profile analysis failed after {step_time:.2f}s: {str(e)}")

            # Save failed status to DynamoDB
            await storage.save_step_progress(
                optimization_id=request_id,
                step_name="profile_analysis",
                step_data={
                    'duration': step_time,
                    'error': str(e)
                },
                status="failed"
            )

        return state

    async def _generate_content_node(self, state: WorkflowState) -> WorkflowState:
        """Node for generating content ideas and posts."""
        request_id = state.get("request_id", "unknown")
        api_key = state.get("api_key") or self.api_key
        step_start = time.time()

        logger.info(f"[INFO] [REQ:{request_id}] Starting Content Generator Agent...")

        try:
            if state.get("error"):
                logger.warning(f"[WARN] [REQ:{request_id}] Skipping content generation due to previous error: {state['error']}")
                return state

            state["status"] = "Generating content ideas and posts..."

            if not state.get("profile_data") or not state.get("analysis_results"):
                raise ValueError("Missing required data for content generation")

            logger.info(f"[INFO] [REQ:{request_id}] Generating content based on profile analysis...")

            # Initialize agent with API key
            content_generator = ContentGeneratorAgent(api_key=api_key)

            content_results = await content_generator.generate_content(
                state["profile_data"],
                state["analysis_results"],
                request_id
            )

            state["content_results"] = content_results
            state["status"] = "Content generation completed"

            step_time = time.time() - step_start
            if not state.get("step_timings"):
                state["step_timings"] = {}
            state["step_timings"]["content_generation"] = step_time

            logger.info(f"[OK] [REQ:{request_id}] Content generation completed in {step_time:.2f}s")
            logger.info(f"[INFO] [REQ:{request_id}] Generated {len(content_results.get('content_ideas', []))} content ideas")

            # Save step progress immediately
            progress_saved = await storage.save_step_progress(
                optimization_id=request_id,
                step_name="content_generation",
                step_data={
                    'duration': step_time,
                    'content_ideas_count': len(content_results.get('content_ideas', [])),
                    'sample_posts_count': len(content_results.get('sample_posts', [])),
                    'strategy_created': bool(content_results.get('content_strategy')),
                    'calendar_created': bool(content_results.get('weekly_content_calendar'))
                },
                status="processing"
            )

            if not progress_saved:
                logger.warning(f"[WARN] [REQ:{request_id}] Failed to save content_generation progress to DynamoDB")

        except Exception as e:
            step_time = time.time() - step_start
            state["error"] = f"Error in content generation: {str(e)}"
            state["status"] = "Failed to generate content"
            logger.error(f"[ERROR] [REQ:{request_id}] Content generation failed after {step_time:.2f}s: {str(e)}")

            # Save failed status to DynamoDB
            await storage.save_step_progress(
                optimization_id=request_id,
                step_name="content_generation",
                step_data={
                    'duration': step_time,
                    'error': str(e)
                },
                status="failed"
            )

        return state

    async def _compile_results_node(self, state: WorkflowState) -> WorkflowState:
        """Node for compiling final results."""
        request_id = state.get("request_id", "unknown")
        step_start = time.time()

        logger.info(f"[INFO] [REQ:{request_id}] Starting results compilation...")

        try:
            if state.get("error"):
                # Even if there's an error, try to compile partial results
                error_msg = state["error"]
                logger.warning(f"[WARN] [REQ:{request_id}] Compiling partial results due to error: {error_msg}")

                # Check if this is a critical error
                critical_keywords = [
                    "api key", "authentication", "unauthorized", "invalid_api_key",
                    "invalid_request_error", "rate_limit", "quota_exceeded",
                    "insufficient_quota", "billing", "permission denied", "forbidden"
                ]

                is_critical = any(keyword in error_msg.lower() for keyword in critical_keywords)

                # Provide user-friendly error message for critical errors
                if is_critical:
                    if "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                        user_message = "Invalid or missing OpenAI API key. Please check your API key and try again."
                    elif "rate_limit" in error_msg.lower() or "quota" in error_msg.lower():
                        user_message = "API rate limit or quota exceeded. Please try again later or check your OpenAI account."
                    elif "billing" in error_msg.lower():
                        user_message = "OpenAI billing issue. Please check your OpenAI account billing status."
                    else:
                        user_message = "Authentication or permission error. Please check your OpenAI API key."
                else:
                    user_message = error_msg

                state["final_results"] = {
                    "success": False,
                    "error": user_message,
                    "status": state["status"],
                    "profile_data": state.get("profile_data"),
                    "analysis_results": state.get("analysis_results"),
                    "content_results": state.get("content_results"),
                    "step_timings": state.get("step_timings")
                }

                # Save failed status to DynamoDB with progress at 0%
                await storage.save_step_progress(
                    optimization_id=request_id,
                    step_name="optimization_completed",
                    step_data={
                        'error': user_message,
                        'is_critical': is_critical,
                        'original_error': error_msg
                    },
                    status="failed"
                )

                return state

            state["status"] = "Compiling final optimization report..."

            # Aggregate token usage from all steps
            total_token_usage = {
                'model': config.OPENAI_MODEL,
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }

            for key in ['profile_data', 'analysis_results', 'content_results']:
                if state.get(key) and state[key].get('token_usage'):
                    usage = state[key]['token_usage']
                    total_token_usage['prompt_tokens'] += usage.get('prompt_tokens', 0)
                    total_token_usage['completion_tokens'] += usage.get('completion_tokens', 0)
                    total_token_usage['total_tokens'] += usage.get('total_tokens', 0)

            # Compile comprehensive results
            final_results = {
                "success": True,
                "status": "LinkedIn Profile optimization completed successfully",
                "profile_data": state["profile_data"],
                "analysis_results": state["analysis_results"],
                "content_results": state["content_results"],
                "summary": self._generate_summary(state),
                "recommendations_count": len(state["analysis_results"].get("next_steps", [])),
                "content_ideas_count": len(state["content_results"].get("content_ideas", [])),
                "sample_posts_count": len(state["content_results"].get("sample_posts", [])),
                "step_timings": state.get("step_timings"),
                "token_usage": total_token_usage
            }

            state["final_results"] = final_results
            state["status"] = "Optimization completed successfully"

            step_time = time.time() - step_start
            if not state.get("step_timings"):
                state["step_timings"] = {}
            state["step_timings"]["results_compilation"] = step_time

            # Log performance summary
            timings = state.get("step_timings", {})
            total_time = sum(timings.values())
            logger.info(f"[OK] [REQ:{request_id}] Results compilation completed in {step_time:.2f}s")
            logger.info(f"[COMPLETE] [REQ:{request_id}] WORKFLOW COMPLETE - Total time: {total_time:.2f}s")
            logger.info(f"[INFO] [REQ:{request_id}] Performance breakdown:")
            for step, duration in timings.items():
                logger.info(f"    - {step}: {duration:.2f}s ({(duration/total_time*100):.1f}%)")

            # Save results to DynamoDB
            if storage.is_enabled():
                try:
                    logger.info(f"[SAVE] [REQ:{request_id}] Saving results to DynamoDB...")

                    # Prepare metadata
                    request_metadata = {
                        'target_role': state.get('target_role'),
                        'processing_time': total_time,
                        'step_timings': timings,
                        'file_size': len(state.get('pdf_bytes', b'')) if state.get('pdf_bytes') else None
                    }

                    # Save results (this will run synchronously in the async context)
                    save_success = await storage.save_optimization_result(
                        optimization_id=request_id,
                        results=final_results,
                        request_metadata=request_metadata
                    )

                    if save_success:
                        logger.info(f"[OK] [REQ:{request_id}] Results successfully saved to DynamoDB")
                        # Add storage info to final results
                        final_results['optimization_id'] = request_id
                        final_results['storage_saved'] = True
                    else:
                        logger.warning(f"[WARN] [REQ:{request_id}] Failed to save results to DynamoDB")
                        final_results['storage_saved'] = False

                except Exception as e:
                    logger.error(f"[CRITICAL] [REQ:{request_id}] Error saving to DynamoDB: {str(e)}")
                    final_results['storage_saved'] = False
            else:
                logger.info(f"[INFO] [REQ:{request_id}] DynamoDB storage disabled - results not saved")
                final_results['storage_saved'] = False

            # Save final completion step progress
            progress_saved = await storage.save_step_progress(
                optimization_id=request_id,
                step_name="optimization_completed",
                step_data={
                    'duration': step_time,
                    'total_processing_time': total_time,
                    'storage_saved': final_results.get('storage_saved', False),
                    'success': True
                },
                status="completed"
            )

            if not progress_saved:
                logger.warning(f"[WARN] [REQ:{request_id}] Failed to save completion progress to DynamoDB")

        except Exception as e:
            step_time = time.time() - step_start
            state["error"] = f"Error compiling results: {str(e)}"
            state["status"] = "Failed to compile results"
            state["final_results"] = {
                "success": False,
                "error": state["error"],
                "status": state["status"],
                "step_timings": state.get("step_timings"),
                "storage_saved": False
            }
            logger.error(f"[ERROR] [REQ:{request_id}] Results compilation failed after {step_time:.2f}s: {str(e)}")

            # Save failed status to DynamoDB
            await storage.save_step_progress(
                optimization_id=request_id,
                step_name="optimization_completed",
                step_data={
                    'duration': step_time,
                    'error': str(e),
                    'success': False
                },
                status="failed"
            )

        return state

    def _generate_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate a summary of the optimization results."""
        try:
            analysis = state.get("analysis_results", {})
            content = state.get("content_results", {})
            profile = state.get("profile_data", {})

            summary = {
                "profile_completeness": self._calculate_profile_completeness(profile),
                "optimization_score": analysis.get("overall_score", 0),
                "key_improvements": analysis.get("next_steps", [])[:3],  # Top 3
                "content_strategy": content.get("content_strategy", {}).get("content_pillars", [])[:3],  # Top 3
                "recommended_actions": self._generate_recommended_actions(analysis, content)
            }

            return summary

        except Exception as e:
            return {"error": f"Error generating summary: {str(e)}"}

    def _calculate_profile_completeness(self, profile_data: Dict[str, Any]) -> int:
        """Calculate profile completeness percentage."""
        try:
            if not profile_data:
                return 0

            sections = [
                "personal_info", "summary", "experience", "education",
                "skills", "certifications", "recommendations"
            ]

            completed = 0
            for section in sections:
                data = profile_data.get(section)
                if section == "personal_info":
                    if data and data.get("name") and data.get("title"):
                        completed += 1
                elif section == "summary":
                    if data and data.strip():
                        completed += 1
                else:
                    if data and len(data) > 0:
                        completed += 1

            return int((completed / len(sections)) * 100)

        except Exception:
            return 0

    def _generate_recommended_actions(self, analysis: Dict[str, Any], content: Dict[str, Any]) -> list:
        """Generate top recommended actions for the user."""
        actions = []

        try:
            # Add top analysis recommendations
            next_steps = analysis.get("next_steps", [])
            actions.extend(next_steps[:2])

            # Add content strategy recommendation
            strategy = content.get("content_strategy", {})
            if strategy.get("posting_frequency"):
                actions.append(f"Start posting {strategy.get('posting_frequency')} to build your LinkedIn presence")

            return actions[:5]  # Return top 5 actions

        except Exception:
            return ["Review and optimize your LinkedIn profile based on the provided analysis"]

    async def run_optimization(self, pdf_path: Optional[str] = None,
                              pdf_bytes: Optional[bytes] = None,
                              target_role: Optional[str] = None,
                              request_id: Optional[str] = None,
                              api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete LinkedIn profile optimization workflow.

        Args:
            pdf_path (Optional[str]): Path to the LinkedIn profile PDF
            pdf_bytes (Optional[bytes]): PDF content as bytes
            target_role (Optional[str]): Target role/industry for optimization
            request_id (Optional[str]): Request ID for tracking
            api_key (Optional[str]): OpenAI API key (overrides constructor value)

        Returns:
            Dict[str, Any]: Complete optimization results
        """
        req_id = request_id or "unknown"
        workflow_start = time.time()

        logger.info(f"[INFO] [REQ:{req_id}] Initializing LinkedIn Profile Optimization Workflow...")

        try:
            # Initialize state
            initial_state = WorkflowState(
                pdf_path=pdf_path,
                pdf_bytes=pdf_bytes,
                target_role=target_role,
                profile_data=None,
                analysis_results=None,
                content_results=None,
                final_results=None,
                error=None,
                status="Starting LinkedIn Profile optimization...",
                request_id=req_id,
                api_key=api_key or self.api_key,
                step_timings={}
            )

            # Save initial progress tracking
            progress_saved = await storage.save_step_progress(
                optimization_id=req_id,
                step_name="optimization_started",
                step_data={
                    'target_role': target_role,
                    'has_pdf_path': bool(pdf_path),
                    'has_pdf_bytes': bool(pdf_bytes),
                    'pdf_size': len(pdf_bytes) if pdf_bytes else 0
                },
                status="processing"
            )

            if progress_saved:
                logger.info(f"[OK] [REQ:{req_id}] Initial progress saved to DynamoDB")
            else:
                logger.error(f"[ERROR] [REQ:{req_id}] Failed to save initial progress to DynamoDB")

            logger.info(f"[INFO] [REQ:{req_id}] Starting LangGraph workflow execution...")

            # Run the workflow
            config = {"configurable": {"thread_id": f"linkedin_optimizer_{req_id}"}}
            result = await self.workflow.ainvoke(initial_state, config=config)

            workflow_time = time.time() - workflow_start
            logger.info(f"[OK] [REQ:{req_id}] LangGraph workflow completed in {workflow_time:.2f}s")

            final_results = result.get("final_results", {
                "success": False,
                "error": "No final results generated",
                "status": "Workflow execution failed"
            })

            if final_results.get("success"):
                logger.info(f"[SUCCESS] [REQ:{req_id}] Optimization workflow completed successfully!")
            else:
                logger.error(f"[ERROR] [REQ:{req_id}] Optimization workflow failed: {final_results.get('error', 'Unknown error')}")

            return final_results

        except Exception as e:
            workflow_time = time.time() - workflow_start
            logger.error(f"[CRITICAL] [REQ:{req_id}] Critical workflow failure after {workflow_time:.2f}s: {str(e)}")
            return {
                "success": False,
                "error": f"Workflow execution error: {str(e)}",
                "status": "Critical workflow failure"
            }

    async def get_workflow_status(self, thread_id: str = "linkedin_optimizer") -> Dict[str, Any]:
        """
        Get the current status of a running workflow.

        Args:
            thread_id (str): Thread ID of the workflow

        Returns:
            Dict[str, Any]: Current workflow status
        """
        try:
            config = {"configurable": {"thread_id": thread_id}}
            # This would require implementing state persistence
            # For now, return a basic status
            return {
                "status": "Workflow status tracking not implemented",
                "message": "Use run_optimization for complete workflow execution"
            }
        except Exception as e:
            return {
                "status": "Error getting workflow status",
                "error": str(e)
            }