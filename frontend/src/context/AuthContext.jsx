import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(localStorage.getItem("access_token") || "");
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refresh_token") || "");
  const [username, setUsername] = useState(localStorage.getItem("username") || "");

  const login = ({ access, refresh, username: nextUsername }) => {
    const normalizedAccess = access || "";
    const normalizedRefresh = refresh || "";
    const normalizedUsername = nextUsername || "";
    localStorage.setItem("access_token", normalizedAccess);
    localStorage.setItem("refresh_token", normalizedRefresh);
    localStorage.setItem("username", normalizedUsername);
    setAccessToken(normalizedAccess);
    setRefreshToken(normalizedRefresh);
    setUsername(normalizedUsername);
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("username");
    setAccessToken("");
    setRefreshToken("");
    setUsername("");
  };

  const setTokens = ({ access, refresh }) => {
    if (access) {
      localStorage.setItem("access_token", access);
      setAccessToken(access);
    }
    if (refresh) {
      localStorage.setItem("refresh_token", refresh);
      setRefreshToken(refresh);
    }
  };

  const value = useMemo(
    () => ({
      accessToken,
      refreshToken,
      username,
      isAuthenticated: Boolean(accessToken),
      login,
      logout,
      setTokens,
    }),
    [accessToken, refreshToken, username]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
