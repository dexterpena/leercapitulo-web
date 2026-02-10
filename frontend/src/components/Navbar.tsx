import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { useTheme } from "../contexts/ThemeContext";

export default function Navbar() {
  const { user, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  return (
    <nav className="navbar">
      <div className="navbar-left">
        <Link to="/" className="navbar-brand">
          FiebreReader
        </Link>
        <Link to="/">Home</Link>
        <Link to="/search">Search</Link>
        {user && <Link to="/library">Library</Link>}
      </div>
      <div className="navbar-right">
        <button onClick={toggleTheme} className="btn-icon" title="Toggle theme">
          {theme === "dark" ? "\u2600" : "\u263E"}
        </button>
        {user ? (
          <>
            <Link to="/settings">Settings</Link>
            <button onClick={handleSignOut} className="btn btn-sm">
              Sign Out
            </button>
          </>
        ) : (
          <>
            <Link to="/login">Login</Link>
            <Link to="/signup">Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  );
}
