#!/usr/bin/env python3
"""One-shot 2027 re-audit for Ochanomizu University."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data/canonical/kokkoritsu/master.csv"
COVERAGE = ROOT / "data/canonical/kokkoritsu/coverage.csv"
OPS = ROOT / "data/operations/coverage_reaudit_2027.csv"
KAWAI = ROOT / "data/operations/kawai_coverage_audit_2027.csv"
PILOT = ROOT / "data/operations/candidate_fields_pilot_2027.csv"
CORR = ROOT / "data/operations/canonical_corrections_2027.jsonl"

PAGE = "https://www.ao.ocha.ac.jp/application/faculty/"
SENBATSU = "https://www.ao.ocha.ac.jp/application/faculty/body/application_faculty_d/fil/R09senbatsu.pdf"
PFI_GUIDE = "https://www.ao.ocha.ac.jp/application/faculty/body/application_faculty_d/fil/R09shihiryu.pdf"
AO_GUIDE = "https://www.ao.ocha.ac.jp/application/faculty/body/application_faculty_d/fil/R9sougou.pdf"

def read(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r.fieldnames or []), [dict(x) for x in r]

def write(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="raise")
        w.writeheader()
        w.writerows(rows)

def blank(header):
    return {k: "" for k in header}

def upsert(rows, key, row):
    for i, old in enumerate(rows):
        if old.get(key) == row.get(key):
            rows[i] = row
            return
    rows.append(row)

UNITS = [
    ("HUM", "文教育学部", "人文科学科", "人文", "人文科学科"),
    ("LANG", "文教育学部", "言語文化学科", "外国語・国際", "言語文化学科"),
    ("SOC", "文教育学部", "人間社会科学科", "人文・社会", "人間社会科学科"),
    ("SOC-CHILD", "文教育学部", "人間社会科学科 教育科学・子ども学コース", "教育", "教育科学・子ども学コース"),
    ("DANCE", "文教育学部", "芸術・表現行動学科 舞踊教育学専修プログラム", "芸術・デザイン", "舞踊教育学専修プログラム"),
    ("MUSIC", "文教育学部", "芸術・表現行動学科 音楽表現専修プログラム", "音楽", "音楽表現専修プログラム"),
    ("MATH", "理学部", "数学科", "理学", "数学科"),
    ("PHYS", "理学部", "物理学科", "理学", "物理学科"),
    ("CHEM", "理学部", "化学科", "理学", "化学科"),
    ("BIO", "理学部", "生物学科", "理学", "生物学科"),
    ("INFO", "理学部", "情報科学科", "情報", "情報科学科"),
    ("NUTRI", "生活科学部", "食物栄養学科", "食品・生命", "食物栄養学科"),
    ("HOME", "生活科学部", "人間生活学科", "生活科学", "人間生活学科"),
    ("PSY", "生活科学部", "心理学科", "心理", "心理学科"),
    ("HENV", "共創工学部", "人間環境工学科", "工学・環境", "人間環境工学科"),
    ("CULTINFO", "共創工学部", "文化情報工学科", "文化・情報", "文化情報工学科"),
]

def exam_profile(code):
    if code == "PHYS":
        return {
            "written": "No",
            "oral": "No",
            "practical": "No",
            "detail": "本学の個別試験は課さない。日本留学試験、TOEFL iBT、最終出身校の成績証明書等の提出書類により判定。",
            "written_detail": "",
            "start": "",
            "end": "",
        }
    if code in {"DANCE", "MUSIC"}:
        return {
            "written": "Yes",
            "oral": "Yes",
            "practical": "Yes",
            "detail": "2月25日に外国語の個別テストと実技検査、2月26日に口述試験を実施し、日本留学試験成績・提出書類と総合して判定。",
            "written_detail": "外国語（英語コミュニケーションI・II・III）。",
            "start": "2027-02-25",
            "end": "2027-02-26",
        }
    written = {
        "HUM": "外国語（英語コミュニケーションI・II・III）。",
        "LANG": "外国語（英語コミュニケーションI・II・III）。",
        "SOC": "外国語（英語コミュニケーションI・II・III）。",
        "SOC-CHILD": "外国語（英語コミュニケーションI・II・III）。",
        "MATH": "数学（数学I・II・III・A・B・C）＋外国語。",
        "CHEM": "数学＋理科（化学必須、物理・生物から1科目）＋外国語。",
        "BIO": "数学＋理科（生物必須、物理・化学から1科目）＋外国語。",
        "INFO": "数学＋数学・理科から2科目＋外国語。",
        "NUTRI": "数学＋理科（物理・化学・生物から1科目）＋外国語。",
        "HOME": "外国語（英語コミュニケーションI・II・III）。",
        "PSY": "外国語（英語コミュニケーションI・II・III）。",
        "HENV": "数学＋数学・理科から2科目＋外国語。",
        "CULTINFO": "外国語（英語コミュニケーションI・II・III）。",
    }[code]
    return {
        "written": "Yes",
        "oral": "Yes",
        "practical": "No",
        "detail": "2月25日に学科指定の教科・科目に係る個別テスト、2月26日に口述試験を実施し、日本留学試験成績・提出書類と総合して判定。",
        "written_detail": written,
        "start": "2027-02-25",
        "end": "2027-02-26",
    }

def eju_requirement(code):
    if code in {"HUM", "LANG", "SOC", "SOC-CHILD", "DANCE", "MUSIC"}:
        return "2026年度日本留学試験：日本語、総合科目、数学（コース1又は2）を日本語で受験。"
    if code == "MATH":
        return "2026年度日本留学試験：日本語、数学コース2、理科2科目自由選択を日本語で受験。"
    if code == "PHYS":
        return "2026年度日本留学試験：日本語、数学コース2、理科は物理必須＋化学又は生物を日本語で受験。"
    if code == "CHEM":
        return "2026年度日本留学試験：日本語、数学コース2、理科は化学必須＋物理又は生物を日本語で受験。"
    if code == "BIO":
        return "2026年度日本留学試験：日本語、数学コース2、理科は生物必須＋物理又は化学を日本語で受験。"
    if code in {"INFO", "NUTRI", "HENV"}:
        return "2026年度日本留学試験：日本語、数学コース2、理科2科目自由選択を日本語で受験。"
    return "2026年度日本留学試験：日本語、総合科目、数学（コース1又は2）を日本語で受験。"

def pfi_row(header, code, faculty, dept, field, slot):
    p = exam_profile(code)
    r = blank(header)
    r.update({
        "record_id": f"OCHA-2027-PFI-{code}",
        "admission_year": "2027",
        "institution_type": "国立",
        "university": "お茶の水女子大学",
        "prefecture": "東京都",
        "academic_field": field,
        "stem_flag": "True" if faculty in {"理学部", "共創工学部"} or code == "NUTRI" else "False",
        "faculty_school": faculty,
        "department": dept,
        "selection_category": "特別選抜",
        "selection_name": "私費外国人留学生特別選抜",
        "slot_type": slot,
        "international_baccalaureate_flag": "No",
        "private_foreign_student_flag": "Yes",
        "returnee_flag": "No",
        "regional_quota_flag": "No",
        "adult_selection_flag": "No",
        "capacity": "若干名",
        "school_recommendation_required": "No",
        "exclusive_enrollment_status": "不明",
        "exclusive_enrollment": "2027年度公式募集要項に、合格時の入学確約又は他大学との併願可を明示する記載を確認できないため不明。",
        "eligibility_graduation": "日本国籍を有しない女子で、在留資格「留学」等を有する又は取得見込みであり、外国の12年課程修了・IB等の大学入学資格のいずれかを満たし、2026年度日本留学試験を受験した者。",
        "gpa_requirement": "数値による評定要件なし。最終出身校の成績証明書を選抜資料として使用。",
        "english_requirement": "TOEFL iBTの受験・スコア提出が必要。" if code in {"PHYS", "NUTRI"} else "外部英語資格の必須要件なし。",
        "subject_prerequisites": eju_requirement(code),
        "common_test_required": "No",
        "common_test_usage": "大学入学共通テストは課さず、日本留学試験を利用。",
        "research_activity_level": "not_specified",
        "research_requirement_required": "No",
        "academic_record_required": "Yes",
        "academic_record_type": "成績証明書",
        "academic_record_detail": "出身学校の成績証明書原本を提出し、選抜資料として使用。",
        "documents_summary": "卒業（見込）証明書、成績証明書、最終出身校関係教員の推薦書、日本語作文、日本留学試験受験票写し、在留・本人確認書類等。該当学科はTOEFL、実技関係調査書、健康診断書も提出。",
        "selection_process": p["detail"],
        "selection_document_review": "Yes",
        "selection_interview": "No",
        "selection_oral_exam": p["oral"],
        "selection_presentation": "No",
        "selection_essay": "No",
        "selection_written_exam": p["written"],
        "selection_practical": p["practical"],
        "selection_group_discussion": "No",
        "selection_aptitude_test": "No",
        "selection_common_test": "No",
        "oral_exam_subjects": "学科別口述試験" if p["oral"] == "Yes" else "",
        "oral_exam_detail": "2月26日に口述試験を実施。" if p["oral"] == "Yes" else "",
        "written_exam_detail": p["written_detail"],
        "selection_method_detail": p["detail"],
        "application_start": "2026-12-01",
        "application_end": "2026-12-07",
        "second_stage_start": p["start"],
        "second_stage_end": p["end"],
        "final_result_date": "2027-03-09",
        "source_status": "2027年度私費外国人留学生特別選抜公式募集要項確認済",
        "detail_completeness": "complete（2027年度公式私費外国人留学生募集要項精査済）",
        "verification_grade": "A",
        "verified_on": "2026-09-28",
        "source_url": PAGE,
        "schedule_url": PFI_GUIDE,
        "guideline_url": PFI_GUIDE,
        "notes": "2026-09-28 Coverage再監査で2027年度公式私費外国人留学生募集要項から新規収録。人間社会科学科は出願時に通常区分と教育科学・子ども学コースを選択するため別募集単位化。芸術・表現行動学科は専修プログラム別に選考内容が異なるため別募集単位化。",
        "information_year": "2027",
        "publication_status": "2027年度公式募集要項公開済",
        "fallback_previous_year": "No",
    })
    return r

def main():
    header, rows = read(MASTER)
    rows = [
        r for r in rows
        if not (
            r.get("university") == "お茶の水女子大学"
            and re.match(r"^OCHA-2027-PFI-", r.get("record_id", ""))
        )
    ]
    base = len(rows)
    additions = [pfi_row(header, *x) for x in UNITS]
    rows.extend(additions)
    write(MASTER, header, rows)

    h2, cov = read(COVERAGE)
    c = next(x for x in cov if x["university"] == "お茶の水女子大学")
    c.update({
        "research_status": "再監査済（2027公式4対象選抜群・私費外国人留学生16募集単位を含む）",
        "master_rows": "49",
        "current_year_status": "2027年度公式情報を全対象選抜で確認済",
        "fallback_status": "不要（現行情報あり）",
        "checked_on": "2026-09-28",
        "official_source_url": PAGE,
        "notes": "2026-09-28 Coverage再監査：2027年度公式入試体系・募集要項を確認。既存33行（新フンボルト13＋学校推薦8＋帰国生徒等12）に私費外国人留学生16募集単位を追加し計49行。高大連携特別選抜は2026年度入試を最後に廃止済み。Kei-Net 2027推薦・総合型とクロスチェックし、掲載範囲でmissing candidateなし。",
    })
    write(COVERAGE, h2, cov)

    h3, ops = read(OPS)
    o = next(x for x in ops if x["source_dataset"] == "kokkoritsu" and x["university"] == "お茶の水女子大学")
    o.update({
        "reaudit_status": "再監査済",
        "official_system_checked": "実施済",
        "capacity_table_checked": "実施済",
        "schedule_checked": "実施済",
        "guideline_index_checked": "実施済",
        "master_compared": "実施済",
        "kawai_crosscheck": "実施済",
        "missing_candidate_count": "0",
        "ambiguous_candidate_count": "0",
        "obsolete_candidate_count": "0",
        "update_queue_open_count": "0",
        "last_audited_on": "2026-09-28",
        "notes": "2027公式入試体系・募集人員・日程・各募集要項とMasterを照合。私費外国人留学生16募集単位を追加し33→49行。新フンボルト・学校推薦・帰国生徒等は既存行と対応。高大連携は2026年度入試で廃止。Kei-Net 2027推薦・総合型をクロスチェックし掲載範囲でmissingなし。未公開資料なし。",
    })
    write(OPS, h3, ops)

    h4, kawai = read(KAWAI)
    k = next(x for x in kawai if x["source_dataset"] == "kokkoritsu" and x["university"] == "お茶の水女子大学")
    k.update({
        "kawai_rec_year": "2027",
        "kawai_ao_year": "2027",
        "kawai_crosscheck_status": "実施済",
        "missing_candidate_status": "なし（Kei-Net掲載範囲）",
        "official_confirmation_status": "確認済",
        "last_checked_on": "2026-09-28",
        "notes": "Kei-Net 2027学校推薦型・総合型を既存Masterと照合し、掲載範囲でmissing candidateなし。帰国生徒・私費外国人留学生はKei-Net推薦・総合型DB対象外のため大学公式2027募集要項でCoverage確認。",
    })
    write(KAWAI, h4, kawai)

    h5, pilot = read(PILOT)
    def pilot_row(rid, faculty, dept, sel, slot, deadline, grad_status, years, grad_detail, gender, gender_detail, guide, note):
        x = blank(h5)
        x.update({
            "source_dataset": "kokkoritsu",
            "record_id": rid,
            "university": "お茶の水女子大学",
            "faculty_school": faculty,
            "department": dept,
            "selection_name": sel,
            "slot_type": slot,
            "enrollment_procedure_deadline": deadline,
            "enrollment_procedure_detail": f"入学手続期間の最終日：{deadline}" if deadline else "",
            "graduation_eligibility_status": grad_status,
            "years_since_graduation_max": years,
            "graduation_eligibility_detail": grad_detail,
            "regional_requirement_status": "No",
            "regional_requirement_detail": "2027年度公式募集要項の出願資格を確認し、居住地・高校所在地等の地域要件なし。",
            "gender_requirement": gender,
            "gender_requirement_detail": gender_detail,
            "guideline_url": guide,
            "reviewed_on": "2026-09-28",
            "pilot_status": "pilot",
            "notes": note,
        })
        return x

    samples = [
        pilot_row(
            "OCHA-2027-AO-HUM", "文教育学部", "人文科学科", "総合型選抜（新フンボルト入試）", "人文科学科",
            "2026-12-17", "既卒可", "2",
            "高等学校・中等教育学校を2025年3月以降に卒業した者又は2027年3月卒業見込み等。",
            "女性", "自身の性自認に基づき、女子大学で学ぶことを希望する者を受け入れる。",
            AO_GUIDE, "お茶の水女子大学の国内早期選抜代表。4候補項目を公式要項から収集。"
        ),
        pilot_row(
            "OCHA-2027-PFI-HUM", "文教育学部", "人文科学科", "私費外国人留学生特別選抜", "人文科学科",
            "2027-03-15", "その他", "",
            "日本国籍を有しない女子で、外国の12年課程修了・IB等の大学入学資格を満たす者等。",
            "女性", "公式募集要項で日本国籍を有しない女子を出願資格とする。",
            PFI_GUIDE, "私費外国人留学生代表。入学手続締切・卒業条件・地域条件・性別条件を2027公式要項から収集。"
        ),
    ]
    for x in samples:
        upsert(pilot, "record_id", x)
    write(PILOT, h5, pilot)

    items = [json.loads(x) for x in CORR.read_text(encoding="utf-8").splitlines() if x.strip()]
    cc = {
        "correction_id": "CC-2027-0006",
        "dataset": "kokkoritsu",
        "university": "お茶の水女子大学",
        "detected_on": "2026-09-28",
        "status": "applied_complete",
        "reason": "Coverage re-audit found the 2027 private-foreign undergraduate special selection absent from canonical Master.",
        "existing_master_rows": 33,
        "missing_selection_groups": [
            {
                "selection_name": "私費外国人留学生特別選抜",
                "confirmed_units": 16,
                "apply_status": "applied_complete",
                "grain_note": "Human and Social Sciences is split into regular and Education Science/Child Studies choices because applicants select the route at application; Dance and Music are separate specialization choices."
            }
        ],
        "confirmed_missing_units_total": 16,
        "applied_master_rows": 16,
        "current_university_master_rows": 49,
        "official_source": "2027年度お茶の水女子大学 入学者選抜要項・私費外国人留学生特別選抜学生募集要項",
        "official_url": PAGE,
        "audit_note": "All 2027 undergraduate early/special-selection groups in scope are now represented. High-school/university collaboration selection ended with the 2026 admission cycle.",
    }
    items = [x for x in items if x.get("correction_id") != "CC-2027-0006"] + [cc]
    CORR.write_text("\n".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")) for x in items) + "\n", encoding="utf-8")

    ids = [r["record_id"] for r in rows]
    ocha = [r for r in rows if r.get("university") == "お茶の水女子大学"]
    assert len(rows) == base + 16
    assert len(ids) == len(set(ids))
    assert len(ocha) == 49
    assert sum(r.get("private_foreign_student_flag") == "Yes" for r in ocha) == 16
    assert sum(r.get("returnee_flag") == "Yes" for r in ocha) == 12
    assert sum(r.get("adult_selection_flag") == "Yes" for r in ocha) == 0
    assert sum(r.get("regional_quota_flag") == "Yes" for r in ocha) == 0
    assert sum(r.get("international_baccalaureate_flag") == "Yes" for r in ocha) == 0
    assert len(additions) == 16

    print(json.dumps({
        "kokkoritsu_rows_after": len(rows),
        "ocha_rows": len(ocha),
        "ocha_private_foreign": 16,
        "ocha_returnee": 12,
        "reaudit_status": "再監査済",
    }, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
