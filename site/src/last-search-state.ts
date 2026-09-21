import type { FilterOptions, SearchRequest } from "./types";
import { parseSearchParams, serializeRequest } from "./url-state";

export const LAST_SEARCH_QUERY_KEY = "early-admissions:last-search-query";
export const LAST_RESULTS_URL_KEY = "early-admissions:last-results-url";

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

export function canonicalResultsUrl(request: SearchRequest): string {
  const query = serializeRequest(request).toString();
  return `/results${query ? `?${query}` : ""}`;
}

export function rememberLastResults(
  request: SearchRequest,
  storage: SearchStateStorage | null = safeSessionStorage(),
): string {
  const url = canonicalResultsUrl(request);
  try {
    storage?.setItem(LAST_RESULTS_URL_KEY, url);
  } catch {
    // Storage can be unavailable in privacy-restricted browsing contexts.
  }
  return url;
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

export function readLastResultsUrl(
  options: FilterOptions,
  storage: SearchStateStorage | null = safeSessionStorage(),
): string {
  try {
    const value = storage?.getItem(LAST_RESULTS_URL_KEY);
    if (!value) return "";
    const url = new URL(value, "https://early-admissions.invalid");
    if (url.origin !== "https://early-admissions.invalid" || url.pathname !== "/results" || url.hash) return "";
    const parsed = parseSearchParams(url.searchParams, options);
    return canonicalResultsUrl(parsed.request);
  } catch {
    return "";
  }
}

export type DetailReturnTarget =
  | { mode: "history"; label: "検索結果へ" }
  | { mode: "url"; label: "検索結果へ" | "検索へ"; href: string };

export function detailReturnTarget(
  state: unknown,
  options: FilterOptions,
  storage: SearchStateStorage | null = safeSessionStorage(),
): DetailReturnTarget {
  const from = state && typeof state === "object"
    ? (state as { from?: unknown }).from
    : null;
  if (typeof from === "string" && /^\/results(?:\?|$)/.test(from)) {
    return { mode: "history", label: "検索結果へ" };
  }
  const resultsUrl = readLastResultsUrl(options, storage);
  if (resultsUrl) return { mode: "url", label: "検索結果へ", href: resultsUrl };
  const query = readLastSearchQuery(storage);
  return {
    mode: "url",
    label: "検索へ",
    href: `/search${query ? `?${query}` : ""}`,
  };
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
