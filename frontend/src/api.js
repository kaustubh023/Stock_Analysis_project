import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

const isAuthEndpoint = (url = "") =>
  url.startsWith("/auth/login/") ||
  url.startsWith("/auth/register/") ||
  url.startsWith("/auth/user-exists/") ||
  url.startsWith("/auth/refresh/") ||
  url.startsWith("/user/login/") ||
  url.startsWith("/user/register/") ||
  url.startsWith("/user/token/refresh/");

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  const url = config.url || "";

  if (token && !isAuthEndpoint(url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config || {};
    const status = error?.response?.status;
    const originalUrl = originalRequest.url || "";

    if (status !== 401 || originalRequest._retry || isAuthEndpoint(originalUrl)) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("username");
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = api
          .post("/user/token/refresh/", { refresh: refreshToken })
          .finally(() => {
            refreshPromise = null;
          });
      }

      const refreshResponse = await refreshPromise;
      const nextAccess = refreshResponse?.data?.access;
      const nextRefresh = refreshResponse?.data?.refresh;

      if (!nextAccess) {
        throw new Error("Token refresh did not return access token.");
      }

      localStorage.setItem("access_token", nextAccess);
      if (nextRefresh) {
        localStorage.setItem("refresh_token", nextRefresh);
      }

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${nextAccess}`;
      return api(originalRequest);
    } catch (refreshError) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("username");
      return Promise.reject(refreshError);
    }
  }
);

export default api;
