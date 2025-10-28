"""Processing router - handles blog processing requests."""

import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from ...models.schemas import ProcessBlogRequest, ProcessingResult, ErrorResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process", response_model=ProcessingResult)
async def process_blog(
    request: Request,
    blog_request: ProcessBlogRequest
):
    """
    Process a blog URL through the complete pipeline.
    
    This will:
    1. Crawl the URL and extract content
    2. Generate summary, questions, and embeddings (in parallel!)
    3. Save everything to the database
    
    **Optimization**: LLM operations run in parallel, saving ~1500ms
    """
    try:
        logger.info(f"📥 Processing request: {blog_request.url}")
        
        pipeline = request.app.state.pipeline
        
        result = await pipeline.process_blog(
            url=blog_request.url,
            num_questions=blog_request.num_questions,
            force_refresh=blog_request.force_refresh
        )
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Processing failed: {str(e)}"
        )


@router.post("/process-async")
async def process_blog_async(
    request: Request,
    blog_request: ProcessBlogRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a blog in the background.
    
    Returns immediately with a 202 Accepted status.
    Useful for long-running operations.
    """
    try:
        pipeline = request.app.state.pipeline
        
        # Add to background tasks
        background_tasks.add_task(
            pipeline.process_blog,
            url=blog_request.url,
            num_questions=blog_request.num_questions,
            force_refresh=blog_request.force_refresh
        )
        
        return {
            "status": "accepted",
            "message": f"Processing started for {blog_request.url}",
            "url": blog_request.url
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start background processing: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing: {str(e)}"
        )

