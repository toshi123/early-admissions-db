import type { SearchRequest } from "./types";
import { serializeRequest } from "./url-state";

export interface SearchNavigationDependencies {
  pushState: (state: unknown, title: string, url: string) => void;
  render: () => Promise<void> | void;
  scrollTo: (options: ScrollToOptions) => void;
}

export async function submitSearchNavigation(
  request: SearchRequest,
  dependencies: SearchNavigationDependencies,
): Promise<void> {
  const query = serializeRequest(request).toString();
  dependencies.pushState(
    { transition: "search-submit" },
    "",
    `/results${query ? `?${query}` : ""}`,
  );
  await dependencies.render();
  dependencies.scrollTo({ top: 0, left: 0, behavior: "auto" });
}
