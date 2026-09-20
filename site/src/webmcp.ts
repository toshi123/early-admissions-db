import type { SearchRequest } from "./types";

declare global {
  interface Document { modelContext?: { registerTool(tool: unknown, options?: { signal?: AbortSignal }): void | Promise<void> }; }
}

export function registerSearchTools(
  apply: (partial: Partial<SearchRequest>) => Promise<{ total: number; universities: number }>,
  read: () => { total: number; universities: number; url: string },
): () => void {
  const context = document.modelContext;
  if (!context?.registerTool) return () => undefined;
  const lifecycle = new AbortController();
  const report = (error: unknown) => console.warn("WebMCP registration failed", error);
  try {
    void Promise.resolve(context.registerTool({
      name: "apply_admission_search_filters",
      title: "入試検索条件を適用",
      description: "表示中の構造化検索へ都道府県、大学種別、GPA、GPA modeを適用し、同じ画面状態とURLを更新します。",
      inputSchema: {
        type: "object", additionalProperties: false,
        properties: {
          prefecture_membership: { type: "array", items: { type: "string" } },
          institution_type: { type: "array", items: { type: "string" } },
          gpa_tenths: { type: ["integer", "null"], minimum: 0, maximum: 50 },
          gpa_mode: { type: "string", enum: ["safe", "review", "all"] },
        },
      },
      annotations: { readOnlyHint: false, untrustedContentHint: false },
      execute: async (input: unknown) => {
        if (!input || typeof input !== "object" || Array.isArray(input)) throw new Error("object input required");
        const record = input as Record<string, unknown>;
        const allowed = new Set(["prefecture_membership", "institution_type", "gpa_tenths", "gpa_mode"]);
        if (Object.keys(record).some((key) => !allowed.has(key))) throw new Error("unsupported field");
        for (const field of ["prefecture_membership", "institution_type"] as const) {
          if (record[field] !== undefined && (!Array.isArray(record[field]) || record[field].some((value) => typeof value !== "string" || !value))) {
            throw new Error(`${field} must be a list of non-empty strings`);
          }
        }
        if (record.gpa_tenths !== undefined && record.gpa_tenths !== null &&
          (!Number.isInteger(record.gpa_tenths) || (record.gpa_tenths as number) < 0 || (record.gpa_tenths as number) > 50)) {
          throw new Error("gpa_tenths must be an integer from 0 to 50");
        }
        if (record.gpa_mode !== undefined && !["safe", "review", "all"].includes(record.gpa_mode as string)) throw new Error("unsupported gpa_mode");
        return apply(record as Partial<SearchRequest>);
      },
    }, { signal: lifecycle.signal })).catch(report);
    void Promise.resolve(context.registerTool({
      name: "read_admission_search_summary",
      title: "入試検索結果を確認",
      description: "表示中の検索結果件数、大学数、共有可能なURLを読み取ります。",
      inputSchema: { type: "object", properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, untrustedContentHint: false },
      execute: () => read(),
    }, { signal: lifecycle.signal })).catch(report);
  } catch (error) { report(error); }
  return () => lifecycle.abort();
}
