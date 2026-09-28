#!/usr/bin/env python3
"""Apply only the 2027 HUE application units proven by the published guide.

The teacher-training-special guide treats one campus as one application and
allows ranked program preferences within that application. The 2027 school-
recommendation guide was scheduled for late September but is not listed yet;
its actual application units remain queued and are deliberately not added.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-28"
UNIVERSITY = "北海道教育大学"
INDEX = "https://www.hokkyodai.ac.jp/exam/faculties/exam/download/"
GUIDE = (
    "https://www.hokkyodai.ac.jp/files/00000200/00000285/"
    "%E4%BB%A4%E5%92%8C%EF%BC%99%E5%B9%B4%E5%BA%A6%E5%AD%A6%E7%94%9F%E5%8B%9F%E9%9B%86%E8%A6%81%E9%A0%85"
    "%EF%BC%88%E6%95%99%E5%93%A1%E9%A4%8A%E6%88%90%E7%89%B9%E5%88%A5%E5%85%A5%E8%A9%A6%EF%BC%89.pdf"
)
OUTLINE = (
    "https://www.hokkyodai.ac.jp/files/00000200/00000285/"
    "%E4%BB%A4%E5%92%8C%EF%BC%99%E5%B9%B4%E5%BA%A6%E5%85%A5%E5%AD%A6%E8%80%85%E9%81%B8%E6%8A%9C%E8%A6%81%E9%A0%85%20.pdf"
)
APPLICATION = "総合型選抜（教員養成特別入試）"
QUEUE_ID = "UQ-2027-0046"
CORRECTION_ID = "CC-2027-0010"


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=header, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def make_row(header: list[str], campus: str, record_id: str) -> dict[str, str]:
    row = {key: "" for key in header}
    row.update({
        "record_id": record_id,
        "admission_year": "2027",
        "institution_type": "国立",
        "university": UNIVERSITY,
        "prefecture": "北海道",
        "academic_field": "教育",
        "stem_flag": "False",
        "faculty_school": f"教育学部 教員養成課程 {campus}校",
        "department": "修学希望専攻・分野（キャンパス内順位指定）",
        "selection_category": "総合型選抜",
        "selection_name": APPLICATION,
        "slot_type": f"{campus}校（1校出願・希望順位選択）",
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "No",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        # The guide says "若干人" by preference area and gives no campus total.
        "capacity": "",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "専願",
        "exclusive_enrollment": "合格した場合は入学を確約。教員養成特別入試の出願は1校に限り、同大学の学校推薦型選抜、北海道みらいの教員養成枠、自己推薦入試とは併願不可（第一次検査不合格の場合を除く）。",
        "exclusive_enrollment_evidence": "合格した場合，入学を確約できる者",
        "exclusive_enrollment_evidence_page": "PDF 7/32",
        "exclusive_enrollment_evidence_url": GUIDE,
        "eligibility_graduation": "2027年3月に高等学校又は中等教育学校を卒業見込み。学校教育法施行規則第93条に該当する留学又は単位制課程により2026年度途中に卒業した者を含む。",
        "gpa_requirement": "数値による評定基準の記載なし",
        # Exact existing crosswalk label intentionally classifies this as
        # review_required, not as proof that no English-related condition exists.
        "english_requirement": "外部英語資格要件の明示なし。",
        "subject_prerequisites": "教職を志望する強い意欲があり、2027年度大学入学共通テストで本学指定教科・科目を受験すること。希望専攻・分野によって第二次検査で実技を実施。",
        "common_test_required": "Yes",
        "common_test_usage": "指定教科・科目の受験が要件。成績を含めて総合判定。教科・科目は募集要項別紙1-1・1-2参照。",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Yes",
        "academic_record_type": "調査書",
        "academic_record_detail": "在学学校長作成・厳封。取得できない場合は卒業証明書又は成績通信簿。",
        "documents_summary": "入学志願票、調査書、志望理由書。希望分野に応じて実技検査選択票、実技活動歴調査書、音楽実技楽譜・伴奏譜等を追加。",
        "selection_process": "志望者多数の場合は調査書・志望理由書による第一次検査。第二次検査は講義に基づくグループ討論・レポート、面接、該当専攻・分野の実技。これらと大学入学共通テストを総合判定。",
        "selection_document_review": "Yes",
        "selection_interview": "Yes",
        "selection_oral_exam": "Yes" if campus == "旭川" else "No",
        "selection_presentation": "No",
        "selection_essay": "No",
        "selection_written_exam": "No",
        "selection_practical": "Yes",
        "selection_group_discussion": "Yes",
        "selection_aptitude_test": "No",
        "selection_common_test": "Yes",
        "interview_detail": "提出書類の記載内容に基づく面接。旭川校は口頭試問を含む。",
        "oral_exam_detail": "旭川校の面接は口頭試問を含む。" if campus == "旭川" else "",
        "selection_method_detail": (
            "出願単位は札幌校一括。志願票に修学希望の専攻・分野を最大5希望まで順位記入できる。"
            "希望順の分野を別レコードとして重複計上せず、専攻・分野ごとの受入枠は個別の募集人員として分解しない。"
            "専攻・分野別の受入人員は若干人で、札幌校合計の数値は公表要項に記載なし。"
            if campus == "札幌" else
            "出願単位は旭川校一括。志願票には修学希望専攻・分野を第1希望のみ記入できる。"
            "希望分野を独立した別出願とはせず、専攻・分野別の受入枠は個別の募集人員として分解しない。"
            "受入人員は若干人で、旭川校合計の数値は公表要項に記載なし。"
        ),
        "application_start": "2026-09-02",
        "application_end": "2026-09-09",
        "web_registration_period": "2026-08-26 10:00開始（登録締切時刻は募集要項本文に明記なし）",
        "first_stage_result_date": "2026-09-30",
        "second_stage_start": "2026-10-17",
        "second_stage_end": "2026-10-18",
        "final_result_date": "2027-02-10",
        "source_status": "2027年度公式学生募集要項確認済",
        "detail_completeness": "partial（2027年度入学者選抜要項で主要必須項目確認済。出願書類の細目は学生募集要項確認待ち）",
        "verification_grade": "A",
        "verified_on": DATE,
        "source_url": INDEX,
        "schedule_url": GUIDE,
        "guideline_url": GUIDE,
        "notes": "2027年度教員養成特別入試要項で1出願=1修学校を確認。札幌校は最大5希望を順位記入、旭川校は第1希望のみ。希望分野は同一出願内の順位選択として保持。合格発表2027-02-10。入学手続期限は当該ガイドで確認できず空欄。",
        "information_year": "2027",
        "publication_status": "2027年度公式情報",
        "fallback_previous_year": "No",
    })
    return row


def main() -> None:
    master_path = ROOT / "data/canonical/kokkoritsu/master.csv"
    master_header, master = read_csv(master_path)
    ids = {r["record_id"] for r in master}
    additions = [
        make_row(master_header, "札幌", "HUE-2027-AO-TEACHER-SAPPORO"),
        make_row(master_header, "旭川", "HUE-2027-AO-TEACHER-ASAHIKAWA"),
    ]
    positions = {r["record_id"]: i for i, r in enumerate(master)}
    for row in additions:
        if row["record_id"] in positions:
            master[positions[row["record_id"]]] = row
        else:
            master.append(row)
            positions[row["record_id"]] = len(master) - 1
        ids.add(row["record_id"])
    write_csv(master_path, master_header, master)
    hue_count = sum(r["university"] == UNIVERSITY for r in master)

    coverage_path = ROOT / "data/canonical/kokkoritsu/coverage.csv"
    ch, coverage = read_csv(coverage_path)
    for row in coverage:
        if row["university"] == UNIVERSITY:
            row["master_rows"] = str(hue_count)
            row["checked_on"] = DATE
            row["notes"] += (
                " 2026-09-28再監査：2027教員養成特別入試は出願単位を札幌校・旭川校の各1件と確定し2行追加。"
                "札幌校の最大5希望・旭川校の第1希望のみは同一出願内の順位選択として記録。"
                "学校推薦型（一般・地域指定）の詳細出願書類は公開予定時期（9月下旬）時点で公式一覧に未掲載のため追加確認待ち。"
            )
    write_csv(coverage_path, ch, coverage)

    ops_path = ROOT / "data/operations/coverage_reaudit_2027.csv"
    oh, ops = read_csv(ops_path)
    for row in ops:
        if row["university"] == UNIVERSITY:
            row.update({
                "reaudit_status": "追加確認待ち",
                "official_system_checked": "実施済",
                "capacity_table_checked": "実施済",
                "schedule_checked": "実施済",
                "guideline_index_checked": "実施済",
                "master_compared": "実施済",
                "missing_candidate_count": "0",
                "ambiguous_candidate_count": "",
                "obsolete_candidate_count": "0",
                "update_queue_open_count": "1",
                "last_audited_on": DATE,
                "notes": (
                    "2027年度教員養成特別入試の専用募集要項で出願単位を確認。出願は1修学校のみで、"
                    "札幌校は最大5希望を順位記入、旭川校は第1希望のみ。希望先の順位は同一出願内の選択であり、"
                    "キャンパス別2行を追加。札幌・旭川の募集人員は専攻・分野別『若干人』でキャンパス合計は明記なし。"
                    "学校推薦型（一般・地域指定）は9月下旬公開予定だが、2026-09-28時点の公式一覧に2027詳細要項・出願書類なし。"
                    "同選抜および岩見沢音楽文化等の出願単位・複数希望処理は確定せず未反映。出願案内公開後に再確認。"
                ),
            })
    write_csv(ops_path, oh, ops)

    queue_path = ROOT / "data/operations/update_queue.csv"
    qh, queue = read_csv(queue_path)
    if not any(r["queue_id"] == QUEUE_ID for r in queue):
        queue.append({
            "queue_id": QUEUE_ID,
            "institution_type": "国立",
            "university": UNIVERSITY,
            "faculty_school": "教育学部・全校",
            "selection_name": "学校推薦型選抜（一般・地域指定）",
            "document_type": "2027年度学生募集要項・出願書類・Web出願手順",
            "publication_status": "公開予定",
            "release_expected_text": "2026年9月下旬",
            "release_expected_from": "2026-09-21",
            "release_expected_to": "2026-09-30",
            "release_schedule_url": OUTLINE,
            "last_checked_on": DATE,
            "next_check_on": "2026-10-01",
            "actual_release_on": "",
            "action_status": "確認時期到来",
            "related_record_id": "",
            "notes": (
                "2027入学者選抜要項は学校推薦型（一般・地域指定）詳細要項の公開時期を9月下旬と案内。"
                "2026-09-28時点の現行公式ダウンロード一覧には未掲載。2027詳細書類が公開されたら、"
                "志願票・Web入力の選択肢で一般/地域指定の同時出願可否、各校・専攻/分野/コースの実出願単位、"
                "希望順位、1志願票当たり出願数を確定する。前年書類は比較参考のみでcanonical判断に使用しない。"
            ),
        })
    write_csv(queue_path, qh, queue)

    ledger_path = ROOT / "data/operations/canonical_corrections_2027.jsonl"
    records = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line]
    if not any(r.get("correction_id") == CORRECTION_ID for r in records):
        records.append({
            "correction_id": CORRECTION_ID,
            "dataset": "kokkoritsu",
            "university": UNIVERSITY,
            "detected_on": DATE,
            "status": "applied_partial_pending_detail",
            "reason": "公式2027教員養成特別入試要項で、札幌校・旭川校の2キャンパス出願単位が現Masterに未収録と確認。学校推薦型は詳細出願書類の公開待ち。",
            "existing_master_rows": 4,
            "missing_selection_groups": [
                {
                    "selection_name": APPLICATION,
                    "confirmed_units": 2,
                    "grain": "一つの志願票で出願できる修学校（キャンパス）単位。札幌校は最大5希望を順位記入、旭川校は第1希望のみ。順位指定先を別出願として重複計上しない。",
                    "apply_status": "applied_complete",
                    "record_ids": [r["record_id"] for r in additions],
                },
                {
                    "selection_name": "学校推薦型選抜（一般・地域指定）",
                    "confirmed_units": None,
                    "grain": "未確定。現行の2027詳細要項・出願書類が未掲載。専攻/分野/コースおよび一般・地域指定の出願票上の選択単位を確認後に決める。",
                    "apply_status": "pending_official_application_documents",
                    "update_queue_id": QUEUE_ID,
                },
            ],
            "confirmed_missing_units_total": 2,
            "applied_master_rows": 2,
            "current_university_master_rows": hue_count,
            "official_source": "2027年度総合型選抜（教員養成特別入試）学生募集要項・北海道教育大学学生募集要項一覧・2027年度入学者選抜要項",
            "official_url": GUIDE,
            "update_queue_id": QUEUE_ID,
            "audit_note": (
                "要項の出願方法等に『一つの修学校に限り出願』とあり、札幌校は志望専攻・分野を最大第5希望、"
                "旭川校は第1希望のみ記入する。よって希望順位は同一キャンパス出願の内部選択で、分野数ぶんの別Master行にしない。"
                "各希望の受入人員は若干人でキャンパス単位の数値はないためcapacityは空欄。"
                "学校推薦型（一般・地域指定）および岩見沢校音楽文化等は2027専用出願書類が未掲載のため、実出願単位を推定せず未反映。"
            ),
        })
        ledger_path.write_text(
            "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records),
            encoding="utf-8",
        )

    print(f"HUE teacher-training-special: 2 campus application units applied; HUE Master rows={hue_count}; school recommendation queued")


if __name__ == "__main__":
    main()
