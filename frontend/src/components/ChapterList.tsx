import { useState, useMemo, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface Chapter {
  url: string;
  name: string;
  chapter_number: number;
  date: string | null;
}

interface ChapterStatusMap {
  [chapterUrl: string]: { is_read: boolean; is_bookmarked: boolean };
}

interface Props {
  chapters: Chapter[];
  mangaUrl: string;
}

export default function ChapterList({ chapters, mangaUrl }: Props) {
  const { user } = useAuth();
  const [sortDesc, setSortDesc] = useState(true);
  const [filter, setFilter] = useState("");
  const [statuses, setStatuses] = useState<ChapterStatusMap>({});

  // Load chapter statuses if logged in
  useEffect(() => {
    if (!user || !mangaUrl) return;
    api<{ statuses: ChapterStatusMap }>(
      `/api/chapters/status?manga_url=${encodeURIComponent(mangaUrl)}`
    )
      .then((data) => setStatuses(data.statuses))
      .catch(() => {});
  }, [user, mangaUrl]);

  const filtered = useMemo(() => {
    let list = chapters;
    if (filter.trim()) {
      const q = filter.toLowerCase();
      list = list.filter(
        (ch) =>
          ch.name.toLowerCase().includes(q) ||
          String(ch.chapter_number).includes(q)
      );
    }
    return [...list].sort((a, b) =>
      sortDesc
        ? b.chapter_number - a.chapter_number
        : a.chapter_number - b.chapter_number
    );
  }, [chapters, sortDesc, filter]);

  const toggleRead = async (ch: Chapter) => {
    const current = statuses[ch.url]?.is_read || false;
    const newVal = !current;
    setStatuses((prev) => ({
      ...prev,
      [ch.url]: { ...prev[ch.url], is_read: newVal, is_bookmarked: prev[ch.url]?.is_bookmarked || false },
    }));
    await api("/api/chapters/mark-read", {
      method: "POST",
      body: JSON.stringify({ manga_url: mangaUrl, chapter_url: ch.url, is_read: newVal }),
    }).catch(() => {});
  };

  const toggleBookmark = async (ch: Chapter) => {
    const current = statuses[ch.url]?.is_bookmarked || false;
    const newVal = !current;
    setStatuses((prev) => ({
      ...prev,
      [ch.url]: { ...prev[ch.url], is_bookmarked: newVal, is_read: prev[ch.url]?.is_read || false },
    }));
    await api("/api/chapters/bookmark", {
      method: "POST",
      body: JSON.stringify({ manga_url: mangaUrl, chapter_url: ch.url, is_bookmarked: newVal }),
    }).catch(() => {});
  };

  const markPreviousRead = async (ch: Chapter) => {
    // Find all chapters with lower or equal chapter number
    const urls = chapters
      .filter((c) => c.chapter_number <= ch.chapter_number)
      .map((c) => c.url);
    // Optimistic update
    setStatuses((prev) => {
      const next = { ...prev };
      for (const url of urls) {
        next[url] = { ...next[url], is_read: true, is_bookmarked: next[url]?.is_bookmarked || false };
      }
      return next;
    });
    await api("/api/chapters/mark-previous-read", {
      method: "POST",
      body: JSON.stringify({ manga_url: mangaUrl, chapter_urls: urls }),
    }).catch(() => {});
  };

  return (
    <div className="chapter-list">
      <div className="chapter-list-header">
        <h2>Chapters ({chapters.length})</h2>
        <div className="chapter-controls">
          <input
            type="text"
            className="chapter-filter"
            placeholder="Filter chapters..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <button
            className="btn btn-sm"
            onClick={() => setSortDesc((p) => !p)}
            title={sortDesc ? "Sorted descending" : "Sorted ascending"}
          >
            {sortDesc ? "\u2193 Newest" : "\u2191 Oldest"}
          </button>
        </div>
      </div>
      {filtered.length === 0 ? (
        <p className="no-results">No chapters match your filter.</p>
      ) : (
        <ul>
          {filtered.map((ch, i) => {
            const isRead = statuses[ch.url]?.is_read || false;
            const isBookmarked = statuses[ch.url]?.is_bookmarked || false;
            return (
              <li key={i} className={`chapter-item${isRead ? " is-read" : ""}`}>
                <div className="chapter-item-row">
                  <Link
                    to={`/read?url=${encodeURIComponent(ch.url)}&manga=${encodeURIComponent(mangaUrl)}`}
                    className="chapter-item-link"
                  >
                    <span className="chapter-name">{ch.name}</span>
                    {ch.date && (
                      <span className="chapter-date">
                        {new Date(ch.date).toLocaleDateString()}
                      </span>
                    )}
                  </Link>
                  {user && (
                    <div className="chapter-actions">
                      <button
                        className={`btn-icon${isRead ? " active" : ""}`}
                        onClick={() => toggleRead(ch)}
                        title={isRead ? "Mark as unread" : "Mark as read"}
                      >
                        {isRead ? "\u2714" : "\u25CB"}
                      </button>
                      <button
                        className={`btn-icon${isBookmarked ? " active" : ""}`}
                        onClick={() => toggleBookmark(ch)}
                        title={isBookmarked ? "Remove bookmark" : "Bookmark"}
                      >
                        {isBookmarked ? "\u2605" : "\u2606"}
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => markPreviousRead(ch)}
                        title="Mark all previous as read"
                      >
                        \u21E7
                      </button>
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
