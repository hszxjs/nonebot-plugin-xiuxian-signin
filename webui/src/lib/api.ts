export type ApiOptions = RequestInit & { rawBody?: string };

const TOKEN_KEY = "xiuxianAdminToken";

function adminBasePath() {
  if (typeof window === "undefined") {
    return "";
  }
  const pathname = window.location.pathname.replace(/\/$/, "");
  if (!pathname || pathname === "/") {
    return "";
  }
  const assetIndex = pathname.indexOf("/assets/");
  return assetIndex >= 0 ? pathname.slice(0, assetIndex) : pathname;
}

function apiUrl(path: string) {
  if (/^https?:\/\//i.test(path)) {
    return path;
  }
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${adminBasePath()}${normalizedPath}`;
}

function storage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    return window.localStorage;
  } catch (error) {
    if (error instanceof DOMException) {
      return null;
    }
    return null;
  }
}

export function getToken() {
  return storage()?.getItem(TOKEN_KEY) ?? "";
}

export function setToken(token: string) {
  const nextToken = token.trim();
  const localStorage = storage();
  if (!localStorage) {
    return;
  }
  if (nextToken) {
    localStorage.setItem(TOKEN_KEY, nextToken);
    return;
  }
  localStorage.removeItem(TOKEN_KEY);
}

export function initializeTokenFromUrl() {
  if (typeof window === "undefined") {
    return "";
  }
  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");
  if (token) {
    setToken(token);
    return token.trim();
  }
  return getToken();
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { rawBody, ...fetchOptions } = options;
  const headers = new Headers(fetchOptions.headers);
  const body = rawBody ?? fetchOptions.body;
  if (!headers.has("Content-Type") && body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const token = getToken();
  if (token) {
    headers.set("X-Xiuxian-Token", token);
  }

  const response = await fetch(apiUrl(path), { ...fetchOptions, body, headers });
  const text = await response.text();
  let data: unknown = {};
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new ApiError(response.status, "接口返回了无法解析的数据");
      }
      throw error;
    }
  }

  if (!response.ok) {
    const message = typeof data === "object" && data && "error" in data ? String(data.error) : response.statusText;
    throw new ApiError(response.status, message);
  }

  return data as T;
}
