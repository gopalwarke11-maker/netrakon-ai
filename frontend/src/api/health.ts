import { apiFetch } from "./client";
import type { ApiHealth } from "../types/api";

export function getHealth() {
  return apiFetch<ApiHealth>("/api/health");
}
