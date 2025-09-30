import os
import tempfile
import logging
import time
import uuid
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from workflows.linkedin_optimizer_workflow import LinkedInOptimizerWorkflow
from config import config, validate_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Validate configuration on startup
if not validate_config():
    print("❌ Configuration validation failed. Please check your environment variables.")
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
    target_role: Optional[str] = Form(None)
):
    """
    Main endpoint for optimizing LinkedIn profiles.

    Args:
        file: PDF file of the LinkedIn profile
        target_role: Optional target role/industry for optimization

    Returns:
        Optimization results including analysis and content suggestions
    """
    # Generate unique request ID for tracking
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()

    logger.info(f"🚀 [REQ:{request_id}] Starting profile optimization request")
    logger.info(f"📄 [REQ:{request_id}] File: {file.filename}, Size: {file.size} bytes, Target Role: {target_role or 'None'}")

    try:
        # Validate file type
        if not file.filename.lower().endswith('.pdf'):
            logger.warning(f"❌ [REQ:{request_id}] Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted"
            )

        # Check file size
        if file.size > config.MAX_FILE_SIZE:
            logger.warning(f"❌ [REQ:{request_id}] File size too large: {file.size} bytes")
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {config.MAX_FILE_SIZE // 1024 // 1024}MB limit"
            )

        # Read file content
        logger.info(f"📖 [REQ:{request_id}] Reading PDF content...")
        pdf_content = await file.read()

        if not pdf_content:
            logger.warning(f"❌ [REQ:{request_id}] Empty file uploaded")
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )

        logger.info(f"✅ [REQ:{request_id}] PDF content read successfully ({len(pdf_content)} bytes)")

        # Run the optimization workflow
        logger.info(f"🔄 [REQ:{request_id}] Starting LinkedIn profile optimization workflow...")
        results = await workflow.run_optimization(
            pdf_bytes=pdf_content,
            target_role=target_role,
            request_id=request_id
        )

        processing_time = time.time() - start_time
        logger.info(f"✅ [REQ:{request_id}] Optimization completed successfully in {processing_time:.2f}s")

        # Log summary of results
        if results.get("success"):
            summary = results.get("summary", {})
            logger.info(f"📊 [REQ:{request_id}] Results Summary:")
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
        logger.error(f"❌ [REQ:{request_id}] HTTP Error after {processing_time:.2f}s: {e.detail}")
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"💥 [REQ:{request_id}] Unexpected error after {processing_time:.2f}s: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/analyze-profile")
async def analyze_profile_only(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None)
):
    """
    Endpoint for only analyzing profiles without content generation.

    Args:
        file: PDF file of the LinkedIn profile
        target_role: Optional target role/industry for optimization

    Returns:
        Profile analysis results only
    """
    try:
        # Validate file
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are accepted"
            )

        pdf_content = await file.read()

        # Initialize agents
        from agents.profile_collector import ProfileCollectorAgent
        from agents.profile_analyzer import ProfileAnalyzerAgent

        collector = ProfileCollectorAgent()
        analyzer = ProfileAnalyzerAgent()

        # Extract and analyze profile
        profile_data = await collector.extract_profile_data_from_bytes(pdf_content)
        analysis_results = await analyzer.analyze_profile(profile_data, target_role)

        return {
            "success": True,
            "profile_data": profile_data,
            "analysis_results": analysis_results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing profile: {str(e)}"
        )


@app.post("/generate-content")
async def generate_content_only(request: dict):
    """
    Endpoint for generating content based on existing profile analysis.

    Args:
        request: Dictionary containing profile_data and analysis_results

    Returns:
        Generated content ideas and posts
    """
    try:
        profile_data = request.get("profile_data")
        analysis_results = request.get("analysis_results")

        if not profile_data or not analysis_results:
            raise HTTPException(
                status_code=400,
                detail="Both profile_data and analysis_results are required"
            )

        # Initialize content generator
        from agents.content_generator import ContentGeneratorAgent

        generator = ContentGeneratorAgent()
        content_results = await generator.generate_content(profile_data, analysis_results)

        return {
            "success": True,
            "content_results": content_results
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating content: {str(e)}"
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
    logger.info("🔧 Initializing LinkedIn Profile Optimizer API...")
    logger.info(f"🌐 Server will start on {config.HOST}:{config.PORT}")
    logger.info(f"🔄 Debug mode: {config.DEBUG}")
    logger.info(f"🤖 OpenAI Model: {config.OPENAI_MODEL}")
    logger.info("✅ Application startup complete")

    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level="info"
    )