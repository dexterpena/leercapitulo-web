import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.supabase_client import get_supabase
from app import scraper, anilist

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/library", tags=["library"])


class AddToLibraryRequest(BaseModel):
    manga_url: str
    manga_title: str
    cover_url: str | None = None
    status: str = "reading"


class UpdateLibraryRequest(BaseModel):
    status: str | None = None
    current_chapter: float | None = None
    anilist_media_id: int | None = None


@router.get("")
async def get_library(user=Depends(get_current_user)):
    result = (
        get_supabase()
        .table("library")
        .select("*")
        .eq("user_id", str(user.id))
        .order("updated_at", desc=True)
        .execute()
    )
    return {"entries": result.data}


@router.post("")
async def add_to_library(req: AddToLibraryRequest, user=Depends(get_current_user)):
    try:
        result = (
            get_supabase()
            .table("library")
            .upsert(
                {
                    "user_id": str(user.id),
                    "manga_url": req.manga_url,
                    "manga_title": req.manga_title,
                    "cover_url": req.cover_url,
                    "status": req.status,
                },
                on_conflict="user_id,manga_url",
            )
            .execute()
        )
        return {"entry": result.data[0] if result.data else None}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{entry_id}")
async def update_library_entry(
    entry_id: str, req: UpdateLibraryRequest, user=Depends(get_current_user)
):
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates["updated_at"] = "now()"

    result = (
        get_supabase()
        .table("library")
        .update(updates)
        .eq("id", entry_id)
        .eq("user_id", str(user.id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"entry": result.data[0]}


class ChangeStatusRequest(BaseModel):
    status: str


@router.post("/{entry_id}/status")
async def change_status(
    entry_id: str, req: ChangeStatusRequest, user=Depends(get_current_user)
):
    """Change manga status. If 'completed', mark all chapters as read and sync to Anilist."""
    sb = get_supabase()
    user_id = str(user.id)

    # Get the library entry
    lib_result = (
        sb.table("library")
        .select("*")
        .eq("id", entry_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not lib_result.data:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry = lib_result.data[0]
    manga_url = entry["manga_url"]

    # Update status
    sb.table("library").update(
        {"status": req.status, "updated_at": "now()"}
    ).eq("id", entry_id).execute()

    if req.status == "completed":
        # Fetch all chapters and mark them all as read
        try:
            chapters = await scraper.get_chapters(manga_url)
            if chapters:
                rows = [
                    {
                        "user_id": user_id,
                        "manga_url": manga_url,
                        "chapter_url": ch["url"],
                        "is_read": True,
                    }
                    for ch in chapters
                ]
                sb.table("chapter_status").upsert(
                    rows, on_conflict="user_id,chapter_url"
                ).execute()

                # Update current_chapter to the highest
                max_ch = max(ch["chapter_number"] for ch in chapters)
                sb.table("library").update(
                    {"current_chapter": max_ch}
                ).eq("id", entry_id).execute()

                # Sync completed status to Anilist
                if entry.get("anilist_media_id"):
                    await _sync_anilist_status(
                        sb, user_id, entry["anilist_media_id"],
                        int(max_ch), "completed"
                    )
        except Exception as e:
            logger.warning(f"Failed to mark all chapters as read: {e}")

    elif req.status != "completed" and entry.get("anilist_media_id"):
        # Sync the new status to Anilist
        anilist_status_map = {
            "reading": "reading",
            "on_hold": "paused",
            "plan_to_read": "plan_to_read",
            "dropped": "dropped",
        }
        mapped = anilist_status_map.get(req.status, "reading")
        current_ch = entry.get("current_chapter", 0) or 0
        await _sync_anilist_status(
            sb, user_id, entry["anilist_media_id"],
            int(current_ch), mapped
        )

    return {"ok": True}


async def _sync_anilist_status(sb, user_id: str, media_id: int, progress: int, status: str):
    """Push status and progress to Anilist."""
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


@router.delete("/{entry_id}")
async def remove_from_library(entry_id: str, user=Depends(get_current_user)):
    result = (
        get_supabase()
        .table("library")
        .delete()
        .eq("id", entry_id)
        .eq("user_id", str(user.id))
        .execute()
    )
    return {"deleted": bool(result.data)}
