"""
Stories router
Handles story-related endpoints for fetching story content
"""

import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stories", tags=["stories"])

# Base directory for stories
STORIES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "stories")
STORIES_MANIFEST = os.path.join(STORIES_DIR, "stories.json")


def load_stories_manifest():
    """Load and return the stories manifest"""
    try:
        with open(STORIES_MANIFEST, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Stories manifest not found at {STORIES_MANIFEST}")
        raise HTTPException(status_code=500, detail="Stories configuration not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in stories manifest: {e}")
        raise HTTPException(status_code=500, detail="Invalid stories configuration")


def validate_story_exists(story_id: str) -> bool:
    """Check if a story exists in the manifest"""
    manifest = load_stories_manifest()
    return any(story['id'] == story_id for story in manifest['stories'])


def get_story_page_count(story_id: str) -> int:
    """Get the page count for a specific story"""
    manifest = load_stories_manifest()
    for story in manifest['stories']:
        if story['id'] == story_id:
            return story['pageCount']
    raise HTTPException(status_code=404, detail="Story not found")


@router.get("")
async def get_stories(current_user: dict = Depends(get_current_user)):
    """
    Get list of all available stories with metadata.
    
    Returns:
        JSON object containing list of stories with their metadata
        
    Raises:
        HTTPException: 500 if manifest cannot be loaded
    """
    logger.info(f"User '{current_user.get('sub')}' requested stories list")
    
    manifest = load_stories_manifest()
    
    return manifest


@router.get("/{story_id}/cover")
async def get_story_cover(
    story_id: str
):
    """
    Get the cover image for a specific story.
    
    Args:
        story_id: The unique identifier for the story
        
    Returns:
        FileResponse: The cover image file
        
    Raises:
        HTTPException: 404 if story or cover image not found
    """
    logger.info(f"Requested cover for story '{story_id}'")
    
    # Validate story exists
    if not validate_story_exists(story_id):
        raise HTTPException(status_code=404, detail=f"Story '{story_id}' not found")
    
    # Construct path to cover image
    cover_path = os.path.join(STORIES_DIR, story_id, "cover.jpg")
    
    if not os.path.exists(cover_path):
        logger.error(f"Cover image not found at {cover_path}")
        raise HTTPException(status_code=404, detail="Cover image not found")
    
    return FileResponse(cover_path, media_type="image/jpeg")

@router.get("/{story_id}/text")
async def get_story_text(story_id: str, current_user: dict = Depends(get_current_user)):
    """
    Gets the story text of a specific story.
    
    Args:
        story_id: The unique identifier for the story

    Returns:
        str: The text for the story
    
    Raises:
        HTTPException: 404 if story not found
    """
    logger.info(f"User '{current_user.get('sub')}' requested text for story '{story_id}'")

    # Validate story exists
    if not validate_story_exists(story_id):
        raise HTTPException(status_code=404, detail=f"Story '{story_id}' not found")
    
    text_path = os.path.join(STORIES_DIR, story_id, "text.json")
    if not os.path.exists(text_path):
        logger.error(f"Text not found at {text_path}")
        raise HTTPException(status_code=404, detail="Text not found")
    
    with open(text_path) as text_file:
        data = json.load(text_file)

    return data

@router.get("/{story_id}/pages/{page_number}/image")
async def get_story_page_image(
    story_id: str,
    page_number: int
):
    """
    Get the image for a specific page of a story.
    
    Args:
        story_id: The unique identifier for the story
        page_number: The page number (1-indexed)
        
    Returns:
        FileResponse: The page image file
        
    Raises:
        HTTPException: 404 if story, page, or image not found
        HTTPException: 400 if page_number is invalid
    """
    logger.info(f"Requested page {page_number} image for story '{story_id}'")
    
    # Validate story exists
    if not validate_story_exists(story_id):
        raise HTTPException(status_code=404, detail=f"Story '{story_id}' not found")
    
    # Validate page number
    page_count = get_story_page_count(story_id)
    if page_number < 1 or page_number > page_count:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page number. Story has {page_count} pages."
        )
    
    # Construct path to page image
    image_path = os.path.join(STORIES_DIR, story_id, "pages", f"page-{page_number}.jpg")
    
    if not os.path.exists(image_path):
        logger.error(f"Page image not found at {image_path}")
        raise HTTPException(status_code=404, detail="Page image not found")
    
    return FileResponse(image_path, media_type="image/jpeg")


@router.get("/{story_id}/pages/{page_number}/audio")
async def get_story_page_audio(
    story_id: str,
    page_number: int
):
    """
    Get the audio file for a specific page of a story.
    
    Args:
        story_id: The unique identifier for the story
        page_number: The page number (1-indexed)
        
    Returns:
        FileResponse: The page audio file
        
    Raises:
        HTTPException: 404 if story, page, or audio not found
        HTTPException: 400 if page_number is invalid
    """
    logger.info(f"Requested page {page_number} audio for story '{story_id}'")
    
    # Validate story exists
    if not validate_story_exists(story_id):
        raise HTTPException(status_code=404, detail=f"Story '{story_id}' not found")
    
    # Validate page number
    page_count = get_story_page_count(story_id)
    if page_number < 1 or page_number > page_count:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid page number. Story has {page_count} pages."
        )
    
    # Construct path to page audio
    audio_path = os.path.join(STORIES_DIR, story_id, "pages", f"page-{page_number}.wav")
    if os.path.exists(audio_path):
        return FileResponse(audio_path)
    if os.path.exists(audio_path_alt := audio_path.rstrip('.wav') + '.WAV'):
        return FileResponse(audio_path_alt)
    logger.error(f"Page audio not found at {audio_path} or {audio_path_alt}")
    raise HTTPException(status_code=404, detail='Page audio not found')
