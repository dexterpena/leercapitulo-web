from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.supabase_client import get_supabase

router = APIRouter(prefix="/api/chapters", tags=["chapters"])


class MarkReadRequest(BaseModel):
    manga_url: str
    chapter_url: str
    is_read: bool = True


class BookmarkRequest(BaseModel):
    manga_url: str
    chapter_url: str
    is_bookmarked: bool = True


class MarkPreviousReadRequest(BaseModel):
    manga_url: str
    chapter_urls: list[str]


@router.get("/status")
async def get_chapter_statuses(
    manga_url: str = Query(...), user=Depends(get_current_user)
):
    """Get read/bookmark status for all chapters of a manga."""
    result = (
        get_supabase()
        .table("chapter_status")
        .select("chapter_url, is_read, is_bookmarked")
        .eq("user_id", str(user.id))
        .eq("manga_url", manga_url)
        .execute()
    )
    return {"statuses": {row["chapter_url"]: row for row in result.data}}


@router.post("/mark-read")
async def mark_read(req: MarkReadRequest, user=Depends(get_current_user)):
    """Mark a single chapter as read or unread."""
    get_supabase().table("chapter_status").upsert(
        {
            "user_id": str(user.id),
            "manga_url": req.manga_url,
            "chapter_url": req.chapter_url,
            "is_read": req.is_read,
        },
        on_conflict="user_id,chapter_url",
    ).execute()
    return {"ok": True}


@router.post("/bookmark")
async def bookmark(req: BookmarkRequest, user=Depends(get_current_user)):
    """Bookmark or unbookmark a chapter."""
    get_supabase().table("chapter_status").upsert(
        {
            "user_id": str(user.id),
            "manga_url": req.manga_url,
            "chapter_url": req.chapter_url,
            "is_bookmarked": req.is_bookmarked,
        },
        on_conflict="user_id,chapter_url",
    ).execute()
    return {"ok": True}


@router.post("/mark-previous-read")
async def mark_previous_read(
    req: MarkPreviousReadRequest, user=Depends(get_current_user)
):
    """Mark multiple chapters as read (all previous chapters)."""
    rows = [
        {
            "user_id": str(user.id),
            "manga_url": req.manga_url,
            "chapter_url": url,
            "is_read": True,
        }
        for url in req.chapter_urls
    ]
    if rows:
        get_supabase().table("chapter_status").upsert(
            rows, on_conflict="user_id,chapter_url"
        ).execute()
    return {"ok": True, "count": len(rows)}
