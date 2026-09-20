import type { SearchRequest } from "./types";
import { serializeRequest } from "./url-state";

export const LAST_SEARCH_QUERY_KEY = "early-admissions:last-search-query";

export interface SearchStateStorage {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

export function canonicalSearchQuery(request: SearchRequest): string {
  return serializeRequest({ ...request, page: 1 }).toString();
}

export function rememberLastSearch(
  request: SearchRequest,
  storage: SearchStateStorage | null = safeSessionStorage(),
): string {
  const query = canonicalSearchQuery(request);
  try {
    storage?.setItem(LAST_SEARCH_QUERY_KEY, query);
  } catch {
    // Storage can be unavailable in privacy-restricted browsing contexts.
  }
  return query;
}

export function readLastSearchQuery(
  storage: SearchStateStorage | null = safeSessionStorage(),
): string {
  try {
    return storage?.getItem(LAST_SEARCH_QUERY_KEY) ?? "";
  } catch {
    return "";
  }
}

export function headerSearchHref(
  pathname: string,
  request: SearchRequest,
  storage: SearchStateStorage | null = safeSessionStorage(),
): string {
  const query = pathname === "/search" || pathname === "/results"
    ? canonicalSearchQuery(request)
    : readLastSearchQuery(storage);
  return `/search${query ? `?${query}` : ""}`;
}

function safeSessionStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}
