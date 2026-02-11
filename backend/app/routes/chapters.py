import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.supabase_client import get_supabase
from app import anilist, scraper

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chapters", tags=["chapters"])

CHAPTER_NUM_RE = re.compile(
    r"(?:Cap[ií]tulo|Cap\.?|Chapter|Ch\.?)\s*(\d+(?:\.\d+)?)", re.IGNORECASE
)


async def _recalc_progress(user_id: str, manga_url: str):
    """Recalculate the highest read chapter from the DB, update library + Anilist."""
    sb = get_supabase()

    # Get all read chapter URLs for this manga (paginated)
    read_rows = _fetch_all_rows(
        lambda: sb.table("chapter_status")
        .select("chapter_url")
        .eq("user_id", user_id)
        .eq("manga_url", manga_url)
        .eq("is_read", True)
    )

    # To get accurate chapter numbers, fetch the chapter list from the scraper
    # and build a URL -> chapter_number map
    try:
        chapters = await scraper.get_chapters(manga_url)
        url_to_num = {ch["url"]: ch["chapter_number"] for ch in chapters}
    except Exception:
        url_to_num = {}

    # Find the highest read chapter number
    max_chapter = 0
    read_urls = {row["chapter_url"] for row in read_rows}
    for url in read_urls:
        num = url_to_num.get(url, -1)
        if num > max_chapter:
            max_chapter = num

    # Check if library entry exists
    lib_result = (
        sb.table("library")
        .select("id, anilist_media_id, current_chapter, status")
        .eq("user_id", user_id)
        .eq("manga_url", manga_url)
        .execute()
    )

    if lib_result.data:
        entry = lib_result.data[0]
        updates = {"current_chapter": max_chapter, "updated_at": "now()"}

        # If manga was completed but a chapter was unmarked, change to reading
        old_status = entry.get("status", "reading")
        old_chapter = entry.get("current_chapter", 0) or 0
        if old_status == "completed" and max_chapter < old_chapter:
            updates["status"] = "reading"

        sb.table("library").update(updates).eq("id", entry["id"]).execute()

        # Sync to Anilist if linked
        if entry.get("anilist_media_id") and max_chapter > 0:
            anilist_status = updates.get("status", old_status)
            anilist_status_map = {"reading": "reading", "completed": "completed",
                                  "on_hold": "paused", "dropped": "dropped",
                                  "plan_to_read": "plan_to_read"}
            await _sync_anilist(sb, user_id, entry["anilist_media_id"],
                                int(max_chapter), anilist_status_map.get(anilist_status, "reading"))
    elif max_chapter > 0:
        # Auto-add to library if not present
        # Get manga title from scraper
        try:
            detail = await scraper.get_manga_detail(manga_url)
            title = detail.get("title", manga_url)
            cover = detail.get("cover", "")
        except Exception:
            title = manga_url
            cover = ""

        sb.table("library").upsert(
            {
                "user_id": user_id,
                "manga_url": manga_url,
                "manga_title": title,
                "cover_url": cover,
                "status": "reading",
                "current_chapter": max_chapter,
            },
            on_conflict="user_id,manga_url",
        ).execute()


async def _sync_anilist(sb, user_id: str, media_id: int, progress: int, status: str = "reading"):
    """Push progress and status to Anilist."""
    try:
        token_result = (
            sb.table("anilist_tokens")
            .select("access_token")
            .eq("user_id", user_id)
            .execute()
        )
        if token_result.data:
            await anilist.update_progress(
                media_id, progress, status,
                token_result.data[0]["access_token"],
            )
    except Exception as e:
        logger.warning(f"Anilist sync failed: {e}")


class MarkReadRequest(BaseModel):
    manga_url: str
    chapter_url: str
    chapter_number: float = -1
    is_read: bool = True


class BookmarkRequest(BaseModel):
    manga_url: str
    chapter_url: str
    is_bookmarked: bool = True


class MarkPreviousReadRequest(BaseModel):
    manga_url: str
    chapter_urls: list[str]
    max_chapter_number: float = -1
    is_read: bool = True


def _fetch_all_rows(query_fn, page_size=1000):
    """Fetch all rows from a Supabase query, paginating past the default limit."""
    all_data = []
    offset = 0
    while True:
        result = query_fn().range(offset, offset + page_size - 1).execute()
        all_data.extend(result.data)
        if len(result.data) < page_size:
            break
        offset += page_size
    return all_data


@router.get("/status")
async def get_chapter_statuses(
    manga_url: str = Query(...), user=Depends(get_current_user)
):
    """Get read/bookmark status for all chapters of a manga."""
    user_id = str(user.id)
    rows = _fetch_all_rows(
        lambda: get_supabase()
        .table("chapter_status")
        .select("chapter_url, is_read, is_bookmarked")
        .eq("user_id", user_id)
        .eq("manga_url", manga_url)
    )
    return {"statuses": {row["chapter_url"]: row for row in rows}}


@router.post("/mark-read")
async def mark_read(req: MarkReadRequest, user=Depends(get_current_user)):
    """Mark a single chapter as read or unread."""
    user_id = str(user.id)
    logger.info(f"mark-read: user={user_id}, manga={req.manga_url}, chapter={req.chapter_url}, is_read={req.is_read}")
    get_supabase().table("chapter_status").upsert(
        {
            "user_id": user_id,
            "manga_url": req.manga_url,
            "chapter_url": req.chapter_url,
            "is_read": req.is_read,
        },
        on_conflict="user_id,chapter_url",
    ).execute()
    await _recalc_progress(user_id, req.manga_url)
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
    """Mark or unmark multiple chapters as read (all previous chapters)."""
    rows = [
        {
            "user_id": str(user.id),
            "manga_url": req.manga_url,
            "chapter_url": url,
            "is_read": req.is_read,
        }
        for url in req.chapter_urls
    ]
    if rows:
        get_supabase().table("chapter_status").upsert(
            rows, on_conflict="user_id,chapter_url"
        ).execute()
    await _recalc_progress(str(user.id), req.manga_url)
    return {"ok": True, "count": len(rows)}
