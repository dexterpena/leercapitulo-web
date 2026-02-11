import { useEffect, useState } from "react";
import { useSearchParams, Navigate, useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAuth } from "../contexts/AuthContext";

interface AnilistStatus {
  linked: boolean;
  anilist_user_id?: number;
  anilist_username?: string;
}

export default function Settings() {
  const { user, loading: authLoading } = useAuth();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [anilistStatus, setAnilistStatus] = useState<AnilistStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle Anilist OAuth callback
  useEffect(() => {
    const code = params.get("code");
    const isCallback = params.get("anilist_callback");
    if (code && isCallback && user) {
      setError(null);
      const redirectUri = `${window.location.origin}/settings?anilist_callback=true`;
      api("/api/anilist/exchange-code", {
        method: "POST",
        body: JSON.stringify({ code, redirect_uri: redirectUri }),
      })
        .then(() => {
          // Clean up URL params after successful exchange
          navigate("/settings", { replace: true });
          loadAnilistStatus();
        })
        .catch((err) => {
          setError(`Anilist link failed: ${err.message}`);
          navigate("/settings", { replace: true });
        });
    }
  }, [params, user, navigate]);

  const loadAnilistStatus = async () => {
    try {
      const data = await api<AnilistStatus>("/api/anilist/status");
      setAnilistStatus(data);
    } catch {
      setAnilistStatus({ linked: false });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) loadAnilistStatus();
    else setLoading(false);
  }, [user]);

  if (authLoading) return <div className="loading">Loading...</div>;
  if (!user) return <Navigate to="/login" />;

  const linkAnilist = async () => {
    setError(null);
    try {
      const redirectUri = `${window.location.origin}/settings?anilist_callback=true`;
      const data = await api<{ url: string }>(
        `/api/anilist/auth-url?redirect_uri=${encodeURIComponent(redirectUri)}`
      );
      window.location.href = data.url;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start Anilist OAuth");
    }
  };

  const unlinkAnilist = async () => {
    await api("/api/anilist/unlink", { method: "DELETE" });
    setAnilistStatus({ linked: false });
  };

  const syncFromAnilist = async () => {
    setSyncing(true);
    setError(null);
    try {
      const data = await api<{
        imported: number;
        not_found: number;
        not_found_titles: string[];
      }>("/api/anilist/import", { method: "POST" });
      let msg = `Imported ${data.imported} manga into your library.`;
      if (data.not_found > 0) {
        msg += `\n${data.not_found} not found on FiebreReader:\n${data.not_found_titles.join(", ")}`;
      }
      alert(msg);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Import failed");
    } finally {
      setSyncing(false);
    }
  };

  if (loading) return <div className="loading">Loading settings...</div>;

  return (
    <div className="settings-page">
      <h1>Settings</h1>
      <section className="settings-section">
        <h2>Account</h2>
        <p>Logged in as: {user.email}</p>
      </section>
      <section className="settings-section">
        <h2>Anilist Integration</h2>
        {error && <p className="error-msg" style={{ marginBottom: "0.75rem" }}>{error}</p>}
        {anilistStatus?.linked ? (
          <div>
            <p>
              Connected as: <strong>{anilistStatus.anilist_username}</strong>
            </p>
            <p>
              Reading progress is automatically synced to Anilist when you finish
              a chapter.
            </p>
            <div className="settings-buttons">
              <button onClick={syncFromAnilist} className="btn" disabled={syncing}>
                {syncing ? "Syncing..." : "Import from Anilist"}
              </button>
              <button onClick={unlinkAnilist} className="btn btn-danger">
                Unlink Anilist
              </button>
            </div>
          </div>
        ) : (
          <div>
            <p>
              Link your Anilist account to sync your reading progress
              automatically.
            </p>
            <button onClick={linkAnilist} className="btn">
              Connect Anilist
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
