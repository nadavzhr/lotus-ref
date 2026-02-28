/**
 * Thin HTTP client abstraction.
 * All API calls go through here so we can swap to Electron IPC later.
 */
import { useLogStore } from "@/stores/log-store";

const BASE_URL = "/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response, label?: string): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = body.detail ?? res.statusText;
    useLogStore
      .getState()
      .push("error", `[${res.status}] ${label ?? res.url}: ${detail}`);
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

/** Push an info entry to the log (imported by specific API functions). */
export function logInfo(message: string) {
  useLogStore.getState().push("info", message);
}

export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  return handleResponse<T>(res, `GET ${path}`);
}

export async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res, `POST ${path}`);
}

export async function put<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(res, `PUT ${path}`);
}

export async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, { method: "DELETE" });
  return handleResponse<T>(res, `DELETE ${path}`);
}
