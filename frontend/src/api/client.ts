const getApiBaseUrl = (): string => {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl) {
    return envUrl.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    const host = window.location.hostname === "localhost" ? "localhost" : "127.0.0.1";
    return `http://${host}:8000`;
  }
  return "http://127.0.0.1:8000";
};

const apiBaseUrl = getApiBaseUrl();

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}${path}`, {
      credentials: "include",
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError("Backend connection unavailable", 0);
  }

  if (!response.ok) {
    let errorDetail = `Backend request failed with status ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && typeof errData.detail === "string") {
        errorDetail = errData.detail;
      }
    } catch {
      // JSON parsing failed, use default status text
    }
    throw new ApiError(errorDetail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export { apiBaseUrl };
