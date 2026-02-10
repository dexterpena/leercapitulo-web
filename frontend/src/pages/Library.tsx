import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { api, imageProxyUrl } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface LibraryEntry {
  id: string;
  manga_url: string;
  manga_title: string;
  cover_url: string | null;
  status: string;
  current_chapter: number;
}

const STATUS_OPTIONS = ["reading", "completed", "plan_to_read", "dropped"];
const STATUS_LABELS: Record<string, string> = {
  reading: "Reading",
  completed: "Completed",
  plan_to_read: "Plan to Read",
  dropped: "Dropped",
};

export default function Library() {
  const { user, loading: authLoading } = useAuth();
  const [entries, setEntries] = useState<LibraryEntry[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user) return;
    api<{ entries: LibraryEntry[] }>("/api/library")
      .then((data) => setEntries(data.entries))
      .finally(() => setLoading(false));
  }, [user]);

  if (authLoading) return <div className="loading">Loading...</div>;
  if (!user) return <Navigate to="/login" />;

  const filtered =
    filter === "all" ? entries : entries.filter((e) => e.status === filter);

  const updateStatus = async (id: string, status: string) => {
    await api(`/api/library/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
    setEntries((prev) =>
      prev.map((e) => (e.id === id ? { ...e, status } : e))
    );
  };

  const removeEntry = async (id: string) => {
    await api(`/api/library/${id}`, { method: "DELETE" });
    setEntries((prev) => prev.filter((e) => e.id !== id));
  };

  if (loading) return <div className="loading">Loading library...</div>;

  return (
    <div className="library-page">
      <h1>My Library</h1>
      <div className="library-filters">
        <button
          className={`btn btn-sm ${filter === "all" ? "active" : ""}`}
          onClick={() => setFilter("all")}
        >
          All ({entries.length})
        </button>
        {STATUS_OPTIONS.map((s) => (
          <button
            key={s}
            className={`btn btn-sm ${filter === s ? "active" : ""}`}
            onClick={() => setFilter(s)}
          >
            {STATUS_LABELS[s] || s} ({entries.filter((e) => e.status === s).length})
          </button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <p className="no-results">No manga in this category.</p>
      ) : (
        <div className="library-list">
          {filtered.map((entry) => (
            <div key={entry.id} className="library-item">
              <Link to={`/manga?url=${encodeURIComponent(entry.manga_url)}`}>
                <img
                  src={
                    entry.cover_url
                      ? imageProxyUrl(entry.cover_url)
                      : "/placeholder.svg"
                  }
                  alt={entry.manga_title}
                  className="library-cover"
                />
              </Link>
              <div className="library-item-info">
                <Link to={`/manga?url=${encodeURIComponent(entry.manga_url)}`}>
                  <h3>{entry.manga_title}</h3>
                </Link>
                <p>Chapter {entry.current_chapter}</p>
                <select
                  value={entry.status}
                  onChange={(e) => updateStatus(entry.id, e.target.value)}
                >
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {STATUS_LABELS[s] || s}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => removeEntry(entry.id)}
                  className="btn btn-sm btn-danger"
                >
                  Remove
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
