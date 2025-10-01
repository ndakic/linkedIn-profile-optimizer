import logging
import time
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from workflows.linkedin_optimizer_workflow import LinkedInOptimizerWorkflow
from config import config, validate_config
from utils.dynamodb_storage import storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Validate configuration on startup
if not validate_config():
    print("[ERROR] Configuration validation failed. Please check your environment variables.")
    exit(1)

app = FastAPI(
    title="LinkedIn Profile Optimizer",
    description="Multi-Agent System for optimizing LinkedIn profiles using AI",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the workflow
workflow = LinkedInOptimizerWorkflow()


class OptimizationRequest(BaseModel):
    target_role: Optional[str] = None


class OptimizationResponse(BaseModel):
    success: bool
    status: str
    profile_data: Optional[dict] = None
    analysis_results: Optional[dict] = None
    content_results: Optional[dict] = None
    summary: Optional[dict] = None
    error: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "LinkedIn Profile Optimizer API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": [
            "POST /optimize-profile - Upload PDF and get optimization results",
            "GET /results/{optimization_id} - Retrieve saved optimization results by ID",
            "GET /progress/{optimization_id} - Get real-time optimization progress",
            "GET /health - Health check endpoint"
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "LinkedIn Profile Optimizer API is running"
    }


@app.post("/optimize-profile", response_model=OptimizationResponse)
async def optimize_profile(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    optimization_id: Optional[str] = Form(None),
    api_key: Optional[str] = Form(None)
):
    """
    Main endpoint for optimizing LinkedIn profiles.

    Args:
        file: PDF file of the LinkedIn profile
        target_role: Optional target role/industry for optimization
        optimization_id: Optional pre-generated optimization ID
        api_key: Optional OpenAI API key (uses server default if not provided)

    Returns:
        Optimization results including analysis and content suggestions
    """
    # Validate API key if provided
    if api_key:
        if not api_key.startswith('sk-'):
            logger.warning(f"[ERROR] Invalid API key format provided")
            raise HTTPException(
                status_code=400,
                detail="Invalid API key format. OpenAI API keys should start with 'sk-'"
            )
        if len(api_key) < 20:
            logger.warning(f"[ERROR] API key too short")
            raise HTTPException(
                status_code=400,
                detail="Invalid API key length"
            )
        logger.info(f"[INFO] Using user-provided API key")
    else:
        # Check if server has default API key configured
        if not config.OPENAI_API_KEY:
            logger.warning(f"[ERROR] No API key provided and server has no default key")
            raise HTTPException(
                status_code=400,
                detail="OpenAI API key required. Please provide your API key or contact administrator."
            )
        logger.info(f"[INFO] Using server default API key")

    # Use provided optimization_id or generate unique request ID for tracking (36-char UUID)
    request_id = optimization_id or str(uuid.uuid4())
    start_time = time.time()

    logger.info(f"[INFO] [REQ:{request_id}] Starting profile optimization request")
    logger.info(f"[INFO] [REQ:{request_id}] File: {file.filename}, Size: {file.size} bytes, Target Role: {target_role or 'None'}")

    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"[ERROR] [REQ:{request_id}] Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted"
            )

        # Check file size
        if file.size > config.MAX_FILE_SIZE:
            logger.warning(f"[ERROR] [REQ:{request_id}] File size too large: {file.size} bytes")
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {config.MAX_FILE_SIZE // 1024 // 1024}MB limit"
            )

        # Read file content
        logger.info(f"[INFO] [REQ:{request_id}] Reading PDF content...")
        pdf_content = await file.read()

        if not pdf_content:
            logger.warning(f"[ERROR] [REQ:{request_id}] Empty file uploaded")
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )

        logger.info(f"[OK] [REQ:{request_id}] PDF content read successfully ({len(pdf_content)} bytes)")

        # Run the optimization workflow with API key
        logger.info(f"[INFO] [REQ:{request_id}] Starting LinkedIn profile optimization workflow...")
        results = await workflow.run_optimization(
            pdf_bytes=pdf_content,
            target_role=target_role,
            request_id=request_id,
            api_key=api_key
        )

        processing_time = time.time() - start_time
        logger.info(f"[OK] [REQ:{request_id}] Optimization completed successfully in {processing_time:.2f}s")

        # Log summary of results
        if results.get("success"):
            summary = results.get("summary", {})
            logger.info(f"[INFO] [REQ:{request_id}] Results Summary:")
            logger.info(f"    - Profile Score: {summary.get('optimization_score', 'N/A')}/100")
            logger.info(f"    - Completeness: {summary.get('profile_completeness', 'N/A')}%")
            logger.info(f"    - Recommendations: {len(summary.get('key_improvements', []))}")
            logger.info(f"    - Content Ideas: {results.get('content_results', {}).get('content_ideas', []) and len(results['content_results']['content_ideas']) or 0}")

        # Return results
        return OptimizationResponse(
            success=results.get("success", False),
            status=results.get("status", "Unknown status"),
            profile_data=results.get("profile_data"),
            analysis_results=results.get("analysis_results"),
            content_results=results.get("content_results"),
            summary=results.get("summary"),
            error=results.get("error")
        )

    except HTTPException as e:
        processing_time = time.time() - start_time
        logger.error(f"[ERROR] [REQ:{request_id}] HTTP Error after {processing_time:.2f}s: {e.detail}")
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"[CRITICAL] [REQ:{request_id}] Unexpected error after {processing_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/results/{optimization_id}")
async def get_optimization_results(optimization_id: str):
    """
    Retrieve optimization results by ID.

    Args:
        optimization_id: Unique identifier for the optimization

    Returns:
        Optimization results if found
    """
    start_time = time.time()
    logger.info(f"[INFO] [ID:{optimization_id}] Retrieving optimization results...")

    try:
        # Validate ID format (basic validation)
        if len(optimization_id) < 6 or len(optimization_id) > 50:
            logger.warning(f"[ERROR] [ID:{optimization_id}] Invalid optimization ID format")
            raise HTTPException(
                status_code=400,
                detail="Invalid optimization ID format"
            )

        # Retrieve results from DynamoDB
        results = await storage.get_optimization_result(optimization_id)

        if results is None:
            retrieval_time = time.time() - start_time
            logger.warning(f"[NOTFOUND] [ID:{optimization_id}] Results not found after {retrieval_time:.2f}s")
            raise HTTPException(
                status_code=404,
                detail="Optimization results not found"
            )

        retrieval_time = time.time() - start_time
        logger.info(f"[OK] [ID:{optimization_id}] Results retrieved successfully in {retrieval_time:.2f}s")

        return results

    except HTTPException:
        raise
    except Exception as e:
        retrieval_time = time.time() - start_time
        logger.error(f"[CRITICAL] [ID:{optimization_id}] Error retrieving results after {retrieval_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving optimization results: {str(e)}"
        )


@app.get("/progress/{optimization_id}")
async def get_optimization_progress(optimization_id: str):
    """
    Retrieve optimization progress by ID.

    Args:
        optimization_id: Unique identifier for the optimization

    Returns:
        Progress information including current step and completed steps
    """
    start_time = time.time()
    logger.info(f"[INFO] [ID:{optimization_id}] Retrieving optimization progress...")

    try:
        # Validate ID format (basic validation)
        if len(optimization_id) < 6 or len(optimization_id) > 50:
            logger.warning(f"[ERROR] [ID:{optimization_id}] Invalid optimization ID format")
            raise HTTPException(
                status_code=400,
                detail="Invalid optimization ID format"
            )

        progress = await storage.get_optimization_progress(optimization_id)

        if not progress:
            retrieve_time = time.time() - start_time
            logger.info(f"[INFO] [ID:{optimization_id}] Progress not found after {retrieve_time:.2f}s")
            raise HTTPException(
                status_code=404,
                detail="Optimization progress not found"
            )

        retrieve_time = time.time() - start_time
        logger.info(f"[OK] [ID:{optimization_id}] Progress retrieved in {retrieve_time:.2f}s")

        # Calculate progress percentage and estimated completion
        completed_steps = progress.get('processing_steps', [])
        all_steps = ['optimization_started', 'profile_extraction', 'profile_analysis', 'content_generation', 'optimization_completed']

        progress_percentage = (len(completed_steps) / len(all_steps)) * 100
        current_step = progress.get('current_step', 'unknown')
        status = progress.get('status', 'unknown')

        # If status is completed, ensure progress is 100%
        if status == 'completed':
            progress_percentage = 100.0

        # Estimate completion time based on current progress
        step_details = progress.get('step_details', {})
        total_elapsed = 0
        for step_name, details in step_details.items():
            total_elapsed += details.get('duration', 0)

        # Rough estimation: each step takes about 30 seconds on average
        remaining_steps = len(all_steps) - len(completed_steps)
        estimated_remaining = remaining_steps * 30  # seconds

        return {
            "optimization_id": optimization_id,
            "status": status,
            "current_step": current_step,
            "completed_steps": completed_steps,
            "progress_percentage": round(progress_percentage, 1),
            "step_details": step_details,
            "estimated_remaining_seconds": estimated_remaining if status == 'processing' else 0,
            "created_at": progress.get('created_at'),
            "updated_at": progress.get('updated_at')
        }

    except HTTPException:
        raise
    except Exception as e:
        retrieve_time = time.time() - start_time
        logger.error(f"[ERROR] [ID:{optimization_id}] Error retrieving progress after {retrieve_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving progress"
        )


@app.get("/workflow-status/{thread_id}")
async def get_workflow_status(thread_id: str):
    """
    Get the status of a running workflow.

    Args:
        thread_id: Thread ID of the workflow

    Returns:
        Current workflow status
    """
    try:
        status = await workflow.get_workflow_status(thread_id)
        return status
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting workflow status: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    # Print configuration on startup
    config.print_config()

    # Log startup information
    logger.info("[CONFIG] Initializing LinkedIn Profile Optimizer API...")
    logger.info(f"[SERVER] Server will start on {config.HOST}:{config.PORT}")
    logger.info(f"[INFO] Debug mode: {config.DEBUG}")
    logger.info(f"[LLM] OpenAI Model: {config.OPENAI_MODEL}")
    logger.info("[OK] Application startup complete")

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )