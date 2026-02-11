from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_current_user
from app.supabase_client import get_supabase
from app import anilist
from app import scraper

router = APIRouter(prefix="/api/anilist", tags=["anilist"])


@router.get("/auth-url")
async def get_auth_url(
    redirect_uri: str = Query(None), user=Depends(get_current_user)
):
    """Return the Anilist OAuth URL to redirect the user to."""
    from app.config import settings as cfg

    if not cfg.anilist_client_id:
        raise HTTPException(
            status_code=400,
            detail="Anilist integration is not configured. Set ANILIST_CLIENT_ID and ANILIST_CLIENT_SECRET in backend .env",
        )
    return {"url": anilist.get_authorize_url(redirect_uri)}


class ExchangeCodeRequest(BaseModel):
    code: str
    redirect_uri: str | None = None


@router.post("/exchange-code")
async def exchange_code(req: ExchangeCodeRequest, user=Depends(get_current_user)):
    """Exchange the OAuth code for an access token and store it."""
    try:
        token_data = await anilist.exchange_code(req.code, req.redirect_uri)
        access_token = token_data["access_token"]

        # Get the Anilist user info
        viewer = await anilist.get_viewer(access_token)

        # Store in Supabase
        get_supabase().table("anilist_tokens").upsert(
            {
                "user_id": str(user.id),
                "access_token": access_token,
                "anilist_user_id": viewer["id"],
                "anilist_username": viewer["name"],
            },
            on_conflict="user_id",
        ).execute()

        return {
            "anilist_user": {
                "id": viewer["id"],
                "name": viewer["name"],
                "avatar": viewer.get("avatar", {}).get("large"),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def anilist_status(user=Depends(get_current_user)):
    """Check if the user has linked their Anilist account."""
    result = (
        get_supabase()
        .table("anilist_tokens")
        .select("anilist_user_id, anilist_username")
        .eq("user_id", str(user.id))
        .execute()
    )
    if result.data:
        return {"linked": True, **result.data[0]}
    return {"linked": False}


@router.delete("/unlink")
async def unlink_anilist(user=Depends(get_current_user)):
    """Remove the Anilist connection."""
    get_supabase().table("anilist_tokens").delete().eq("user_id", str(user.id)).execute()
    return {"unlinked": True}


@router.get("/search")
async def search_anilist(
    title: str = Query(...), user=Depends(get_current_user)
):
    """Search Anilist for a manga to link."""
    token_row = _get_token(user)
    results = await anilist.search_manga(title, token_row["access_token"])
    return {"results": results}


class SyncProgressRequest(BaseModel):
    anilist_media_id: int
    chapter: int
    status: str = "reading"


@router.post("/sync")
async def sync_progress(req: SyncProgressRequest, user=Depends(get_current_user)):
    """Push reading progress to Anilist."""
    token_row = _get_token(user)
    result = await anilist.update_progress(
        req.anilist_media_id, req.chapter, req.status, token_row["access_token"]
    )
    return {"anilist_entry": result}


@router.get("/manga-list")
async def get_anilist_manga_list(user=Depends(get_current_user)):
    """Fetch the user's full Anilist manga list."""
    token_row = _get_token(user)
    entries = await anilist.get_user_manga_list(token_row["access_token"])
    return {"entries": entries}


@router.post("/import")
async def import_from_anilist(user=Depends(get_current_user)):
    """Import Anilist manga list into the user's library by searching leercapitulo."""
    token_row = _get_token(user)
    entries = await anilist.get_user_manga_list(token_row["access_token"])

    status_map = {
        "CURRENT": "reading",
        "COMPLETED": "completed",
        "PLANNING": "plan_to_read",
        "DROPPED": "dropped",
        "PAUSED": "on_hold",
        "REPEATING": "reading",
    }

    imported = []
    not_found = []

    for entry in entries:
        media = entry.get("media", {})
        titles = media.get("title", {})
        # Try romaji first, then english, then native
        search_title = titles.get("romaji") or titles.get("english") or titles.get("native") or ""
        if not search_title:
            continue

        # Search leercapitulo for this manga
        try:
            results = await scraper.search_manga(search_title)
            mangas = results.get("mangas", [])
        except Exception:
            mangas = []

        if not mangas:
            not_found.append(search_title)
            continue

        # Use the first match
        match = mangas[0]
        al_status = entry.get("status", "CURRENT")
        lib_status = status_map.get(al_status, "reading")
        cover = match.get("thumbnail") or (media.get("coverImage") or {}).get("large", "")

        get_supabase().table("library").upsert(
            {
                "user_id": str(user.id),
                "manga_url": match["url"],
                "manga_title": match["title"],
                "cover_url": cover,
                "status": lib_status,
                "current_chapter": entry.get("progress", 0),
                "anilist_media_id": media.get("id"),
            },
            on_conflict="user_id,manga_url",
        ).execute()

        imported.append(match["title"])

    return {
        "imported": len(imported),
        "not_found": len(not_found),
        "imported_titles": imported,
        "not_found_titles": not_found,
    }


def _get_token(user) -> dict:
    result = (
        get_supabase()
        .table("anilist_tokens")
        .select("access_token")
        .eq("user_id", str(user.id))
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=400, detail="Anilist account not linked")
    return result.data[0]
