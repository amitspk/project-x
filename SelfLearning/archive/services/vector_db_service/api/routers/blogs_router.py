"""Blogs Router - Blog content operations."""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ...data.database import db_manager
from ...core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class BlogResponse(BaseModel):
    """Blog response model."""
    blog_id: str
    url: str
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}


@router.get("/by-url", response_model=BlogResponse)
async def get_blog_by_url(url: str = Query(..., description="Blog URL")):
    """Get blog content by URL."""
    try:
        collection = db_manager.get_collection(settings.blog_collection)
        doc = await collection.find_one({"url": url})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Blog not found")
        
        return BlogResponse(
            blog_id=doc.get("blog_id", str(doc["_id"])),
            url=doc["url"],
            title=doc.get("title"),
            content=doc.get("content"),
            metadata=doc.get("metadata", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching blog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{blog_id}", response_model=BlogResponse)
async def get_blog_by_id(blog_id: str):
    """Get blog content by ID."""
    try:
        collection = db_manager.get_collection(settings.blog_collection)
        doc = await collection.find_one({"blog_id": blog_id})
        
        if not doc:
            raise HTTPException(status_code=404, detail="Blog not found")
        
        return BlogResponse(
            blog_id=doc["blog_id"],
            url=doc["url"],
            title=doc.get("title"),
            content=doc.get("content"),
            metadata=doc.get("metadata", {})
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching blog: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[BlogResponse])
async def list_blogs(skip: int = 0, limit: int = 10):
    """List all blogs with pagination."""
    try:
        collection = db_manager.get_collection(settings.blog_collection)
        cursor = collection.find().skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        
        return [
            BlogResponse(
                blog_id=doc.get("blog_id", str(doc["_id"])),
                url=doc["url"],
                title=doc.get("title"),
                content=doc.get("content"),
                metadata=doc.get("metadata", {})
            )
            for doc in docs
        ]
    except Exception as e:
        logger.error(f"Error listing blogs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

