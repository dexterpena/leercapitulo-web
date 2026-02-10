from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import auth, manga, reader, library, anilist, chapters

app = FastAPI(title="FiebreReader", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(manga.router)
app.include_router(reader.router)
app.include_router(library.router)
app.include_router(anilist.router)
app.include_router(chapters.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
