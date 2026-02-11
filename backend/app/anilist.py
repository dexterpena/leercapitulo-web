"""
Anilist API client — OAuth2 + GraphQL for manga tracking.
"""

from urllib.parse import quote

import httpx
from app.config import settings

ANILIST_AUTH_URL = "https://anilist.co/api/v2/oauth/authorize"
ANILIST_TOKEN_URL = "https://anilist.co/api/v2/oauth/token"
GRAPHQL_URL = "https://graphql.anilist.co"


def get_authorize_url(redirect_uri: str | None = None) -> str:
    """Return the URL to redirect users to for Anilist OAuth."""
    uri = redirect_uri or settings.anilist_redirect_uri
    return (
        f"{ANILIST_AUTH_URL}"
        f"?client_id={settings.anilist_client_id}"
        f"&redirect_uri={quote(uri, safe='')}"
        f"&response_type=code"
    )


async def exchange_code(code: str, redirect_uri: str | None = None) -> dict:
    """Exchange an authorization code for an access token."""
    uri = redirect_uri or settings.anilist_redirect_uri
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            ANILIST_TOKEN_URL,
            json={
                "grant_type": "authorization_code",
                "client_id": settings.anilist_client_id,
                "client_secret": settings.anilist_client_secret,
                "redirect_uri": uri,
                "code": code,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


async def _graphql(query: str, variables: dict, access_token: str) -> dict:
    """Execute a GraphQL query against the Anilist API."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise Exception(f"Anilist GraphQL error: {data['errors']}")
        return data["data"]


async def get_viewer(access_token: str) -> dict:
    """Get the authenticated user's info."""
    query = """
    query {
      Viewer {
        id
        name
        avatar { large }
      }
    }
    """
    data = await _graphql(query, {}, access_token)
    return data["Viewer"]


async def search_manga(title: str, access_token: str, page: int = 1) -> list[dict]:
    """Search Anilist for manga by title."""
    query = """
    query ($search: String!, $page: Int) {
      Page(page: $page, perPage: 10) {
        media(search: $search, type: MANGA) {
          id
          title { romaji english native }
          coverImage { large }
          chapters
          status
        }
      }
    }
    """
    data = await _graphql(query, {"search": title, "page": page}, access_token)
    return data["Page"]["media"]


async def get_user_manga_list(access_token: str) -> list[dict]:
    """Get the authenticated user's full manga list."""
    viewer = await get_viewer(access_token)
    query = """
    query ($userId: Int!) {
      MediaListCollection(userId: $userId, type: MANGA) {
        lists {
          name
          entries {
            id
            mediaId
            status
            progress
            media {
              id
              title { romaji english native }
              coverImage { large }
              chapters
            }
          }
        }
      }
    }
    """
    data = await _graphql(query, {"userId": viewer["id"]}, access_token)
    entries = []
    for lst in data["MediaListCollection"]["lists"]:
        entries.extend(lst["entries"])
    return entries


async def update_progress(
    media_id: int, progress: int, status: str, access_token: str
) -> dict:
    """Update reading progress on Anilist."""
    mutation = """
    mutation ($mediaId: Int!, $progress: Int!, $status: MediaListStatus) {
      SaveMediaListEntry(mediaId: $mediaId, progress: $progress, status: $status) {
        id
        status
        progress
      }
    }
    """
    # Map our status strings to Anilist enum values
    status_map = {
        "reading": "CURRENT",
        "completed": "COMPLETED",
        "on_hold": "PAUSED",
        "plan_to_read": "PLANNING",
        "dropped": "DROPPED",
        "paused": "PAUSED",
    }
    anilist_status = status_map.get(status, "CURRENT")

    data = await _graphql(
        mutation,
        {"mediaId": media_id, "progress": progress, "status": anilist_status},
        access_token,
    )
    return data["SaveMediaListEntry"]
