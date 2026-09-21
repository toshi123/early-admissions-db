import ExcelJS from "@protobi/exceljs";
import { EXPORT_COLUMNS, type ExportRow } from "./candidate-export";

export async function candidateXlsx(rows: ExportRow[]): Promise<Uint8Array> {
  const workbook = new ExcelJS.Workbook();
  const sheet = workbook.addWorksheet("候補リスト", { views: [{ state: "frozen", ySplit: 1 }] });
  sheet.columns = EXPORT_COLUMNS.map((header, index) => ({ header, width:
    [7, 8, 9, 10].includes(index) ? 38 : [12, 13].includes(index) ? 44 : index >= 15 ? 26 : 22 }));
  for (const values of rows) {
    if (values.some((value) => value !== null && value.length > 32767)) {
      throw new Error("Excelのセル文字数上限を超える値があります。CSVで出力してください。");
    }
    const row = sheet.addRow(values);
    row.eachCell((cell, index) => {
      const value = values[index - 1];
      cell.numFmt = "@";
      cell.alignment = { vertical: "top", wrapText: true };
      if ((index === 13 || index === 14) && value) {
        try {
          const url = new URL(value);
          if (["https:", "http:"].includes(url.protocol)) {
            cell.value = { text: value, hyperlink: value };
            cell.font = { color: { argb: "FF00118F" }, underline: true };
          }
        } catch { /* Keep invalid source URLs as text; never invent a URL. */ }
      }
    });
  }
  sheet.autoFilter = { from: { row: 1, column: 1 }, to: { row: rows.length + 1, column: EXPORT_COLUMNS.length } };
  sheet.getRow(1).font = { bold: true };
  sheet.getRow(1).alignment = { vertical: "top", wrapText: true };
  return new Uint8Array(await workbook.xlsx.writeBuffer());
}
