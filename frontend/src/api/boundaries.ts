import { apiFetch } from "./client";
import type { ApiBoundary } from "../types/api";

export function getBoundaries() {
  return apiFetch<ApiBoundary[]>("/api/boundaries");
}
