import { describe, expect, it } from "vitest";
import { emptyRequest } from "../src/search";
import { discoverProvisional, hasUnverifiedFilters, provisionalCard, provisionalCountLabel } from "../src/public-discovery";
import type { ProvisionalAdmission } from "../src/types";

function item(status: ProvisionalAdmission["public_status"], update: Partial<ProvisionalAdmission> = {}): ProvisionalAdmission {
  return {
    provisional_id: "PA-2027-0001", university: "北海道教育大学", institution_type: "国立",
    faculty_school: "教育学部", selection_name: "学校推薦型選抜（一般・地域指定）",
    selection_family: "recommendation", special_filter_tag: "none",
    information_year: 2027, public_status: status, known_scope: "実施確認済み",
    known_detail: "2027年度入学者選抜要項", unknown_detail: "実出願単位・条件",
    official_source_url: "https://www.hokkyodai.ac.jp/exam/faculties/exam/download/",
    previous_year_source_url: null, previous_year_detail: null, release_expected_text: null,
    verified_on: "2026-09-28", related_update_queue_id: "UQ-2027-0046", ...update,
  };
}

describe("public discovery", () => {
  it("keeps Hokkaido Education visible even if the confirmed search has no matching row", () => {
    const request = emptyRequest(); request.university = ["北海道教育大学"];
    request.gpa_tenths = 38;
    expect(discoverProvisional([item("details_pending")], request)).toHaveLength(1);
    expect(hasUnverifiedFilters(request)).toBe(true);
    const html = provisionalCard(item("details_pending"), true);
    expect(html).toContain("2027年度実施確認済み・詳細確認中");
    expect(html).toContain("指定された詳細条件への適合は未判定");
    expect(html).toContain("www.hokkyodai.ac.jp");
    expect(html).not.toContain("条件：なし");
  });

  it("marks the 2026 source as a reference, never a confirmed 2027 condition", () => {
    const html = provisionalCard(item("previous_year_reference", {
      previous_year_source_url: "https://www.obihiro.ac.jp/2026.pdf",
      previous_year_detail: "2026年度要項", release_expected_text: "2026年10月中旬",
    }), false);
    expect(html).toContain("前年実績（2026年度）であり、2027年度は変更される可能性があります");
    expect(html).toContain("2026年度公式資料");
    expect(html).toContain("2026年10月中旬");
  });

  it("shows the publication schedule and official source", () => {
    const html = provisionalCard(item("publication_pending", {
      release_expected_text: "認可が下り次第公表", previous_year_source_url: null,
    }), false);
    expect(html).toContain("2027年度実施予定・募集要項公開待ち");
    expect(html).toContain("認可が下り次第公表");
    expect(html).toContain("2027年度大学公式情報");
    expect(provisionalCountLabel([item("details_pending")])).toBe("詳細確認中");
    expect(provisionalCountLabel([item("details_pending"), item("publication_pending")])).toBe("詳細確認中・公表待ち等");
  });

  it("only excludes on known university and institution type", () => {
    const records = [item("details_pending")];
    const request = emptyRequest(); request.selection_category = ["学校推薦型選抜"];
    expect(discoverProvisional(records, request)).toHaveLength(1);
    request.institution_type = ["私立"];
    expect(discoverProvisional(records, request)).toHaveLength(0);
  });

  it("uses reviewed provisional tags and keeps unclassified international status undecided", () => {
    const request = emptyRequest();
    const foreign = item("details_pending", { special_filter_tag: "private_foreign_student", selection_family: "other" });
    const general = item("details_pending", { special_filter_tag: "unclassified_international", selection_family: "other", provisional_id: "PA-2027-0010" });
    expect(discoverProvisional([foreign, general], request)).toEqual([general]);
    request.special_filters = ["private_foreign_student_flag"];
    expect(discoverProvisional([foreign, general], request)).toEqual([foreign, general]);
    expect(provisionalCard(general, true, request)).toContain("該当するか未確認");
  });
});
