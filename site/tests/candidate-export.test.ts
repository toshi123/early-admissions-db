// @vitest-environment node
import { describe, expect, it } from "vitest";
import ExcelJS from "@protobi/exceljs";
import { candidateCsv, candidateExportRows, csvCell, EXPORT_COLUMNS, exportFilename } from "../src/candidate-export";
import { candidateXlsx } from "../src/candidate-xlsx";
import { CandidateStore, candidateKey, resolveCandidates } from "../src/candidates";
import { candidateDetail, candidateRow } from "./candidate-fixtures";

async function exported() {
  const store = new CandidateStore(null);
  const a = candidateRow(); const b = candidateRow({ record_id: "B" }); const stale = candidateRow({ source_version: "old", record_id: "C" });
  [a, b, stale].forEach((row) => store.add(row, new Date("2026-09-21T00:00:00Z")));
  return candidateExportRows(resolveCandidates(store.items, new Map([a, b].map((row) => [candidateKey(row), row]))),
    new Set([candidateKey(a), candidateKey(stale)]), "https://local.example", async (row) => candidateDetail(row));
}

describe("candidate export contract", () => {
  it("exports only selected logical keys, with fixed columns, raw conditions, stale status and runtime-origin URLs", async () => {
    const values = await exported();
    expect(values).toHaveLength(2); expect(values.every((row) => row.length === EXPORT_COLUMNS.length)).toBe(true);
    expect(values[0][7]).toBe(candidateRow().application_end);
    expect(values[0][9]).toBe("英検2級以上");
    expect(values[0][10]).toBe('研究発表, "受賞"\n証明書を提出');
    expect(values[0][11]).toBe("面接・小論文");
    expect(values[0][13]).toBe("https://local.example/admissions/kokkoritsu/5.61/A%2F1");
    expect(values[1][14]).toBe("stale：現在データで確認できず");
    expect(values[1][7]).toBeNull();
    expect(values.map((row) => row[18])).toEqual(["A/1", "C"]);
  });

  it("produces BOM UTF-8 CSV with Japanese headers and RFC 4180 escaping", async () => {
    const csv = candidateCsv(await exported());
    expect(Buffer.from(csv).subarray(0, 3).toString("hex")).toBe("efbbbf");
    expect(csv.startsWith('\uFEFF"大学名","学部","学科","選抜区分"')).toBe(true);
    expect(csv).toContain('"研究発表, ""受賞""\n証明書を提出"');
    expect(csv).toContain('" 11月6日（必着）\n午後5時 "');
    expect(csv.endsWith("\r\n")).toBe(true);
    expect(csvCell("=SUM(A1)" )).toBe('"\'=SUM(A1)"');
    expect(exportFilename("csv", new Date(2026, 8, 21))).toBe("early-admissions-candidates-2026-09-21.csv");
  });

  it("writes a valid XLSX with selected rows, Japanese headers, filter, frozen row, hyperlinks and wrapped text", async () => {
    const values = await exported(); const bytes = await candidateXlsx(values);
    expect([...bytes.slice(0, 2)]).toEqual([80, 75]);
    const workbook = new ExcelJS.Workbook(); await workbook.xlsx.load(Buffer.from(bytes) as never);
    const sheet = workbook.getWorksheet("候補リスト")!;
    expect(sheet.rowCount).toBe(3); expect(sheet.columnCount).toBe(19);
    expect(sheet.getRow(1).values).toEqual([undefined, ...EXPORT_COLUMNS]);
    expect(sheet.views[0]).toMatchObject({ state: "frozen", ySplit: 1 });
    expect(sheet.autoFilter).toBe("A1:S3");
    expect(sheet.getCell("N2").value).toEqual({ text: values[0][13], hyperlink: values[0][13] });
    expect(sheet.getCell("O3").value).toBe("stale：現在データで確認できず");
    expect(sheet.getCell("H2").value).toBe(candidateRow().application_end);
    expect(sheet.getCell("K2").alignment.wrapText).toBe(true);
    expect(sheet.getColumn(11).width).toBe(38);
  });

  it("keeps formula-like raw values as text in XLSX", async () => {
    const values = await exported(); values[0][0] = '=HYPERLINK("bad")';
    const workbook = new ExcelJS.Workbook(); await workbook.xlsx.load(Buffer.from(await candidateXlsx(values)) as never);
    expect(workbook.worksheets[0].getCell("A2").value).toBe('=HYPERLINK("bad")');
    expect(workbook.worksheets[0].getCell("A2").type).toBe(ExcelJS.ValueType.String);
  });

  it("fails the entire export on missing or mismatched current detail", async () => {
    const store = new CandidateStore(null); const row = candidateRow(); store.add(row);
    const items = resolveCandidates(store.items, new Map([[candidateKey(row), row]]));
    await expect(candidateExportRows(items, new Set([candidateKey(row)]), "https://local.example", async () => { throw new Error("corrupt"); })).rejects.toThrow("corrupt");
    await expect(candidateExportRows(items, new Set([candidateKey(row)]), "https://local.example", async () => candidateDetail(candidateRow({ record_id: "B" })))).rejects.toThrow("一致しません");
  });
});
