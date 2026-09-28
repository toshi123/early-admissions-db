#!/usr/bin/env python3
"""Complete the 2027 TUAT special-selection detailed-guide review."""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = "https://www.tuat.ac.jp/admission/nyushi_gakubu/youkou/"
GUIDE = "https://www.tuat.ac.jp/documents/tuat/admission/nyushi_gakubu/youkou/R9_tokubetu_youkou.pdf"
DATE = "2026-09-28"


def read(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


def write(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


ADULT_DOCS = (
    "本学所定の入学志願票・写真票・受験票、出身学校調査書（発行者厳封。調査書を得られない所定の場合は"
    "卒業証明書と単位取得証明書・成績通信簿等で代替）、志望理由書、職歴調書、在職証明書（自営業者は"
    "確定申告書類・納税証明書等）、連絡用シール、返信用封筒。在留資格確認書類は該当者のみ。"
)
ADULT_ACADEMIC = (
    "出身学校調査書（発行者厳封）。保存期間経過・廃校・被災等で調査書を得られない所定の場合は、"
    "卒業証明書に単位取得証明書・成績通信簿等を添えて代替可。その他の出願資格者は修了証明書、成績証明書、"
    "合格証明書等。中退者で取得単位がある場合は当該内容を記載した調査書も提出。"
)
PFI_DOCS = (
    "本学所定の入学志願票・写真票・受験票、資格経路別の卒業（見込）証明書と学業成績証明書または資格証書・"
    "成績評価証明書、2026年度日本留学試験の受験票・成績確認書・成績通知書のいずれか、TOEIC L&R公開テスト"
    "またはTOEFL iBTの成績証明、履歴書、在留カード等（海外在住者は旅券）コピー、連絡用シール、返信用封筒。"
    "外国語証明には日本語訳を添付。TOEFL公式スコアはETSから大学へ直送。"
)
PFI_ACADEMIC = (
    "出願資格経路に応じ、通常課程等の出願者は卒業（見込）証明書原本および高校相当課程すべての成績証明書原本。"
    "IBは資格証書コピーと最終試験6科目の成績評価証明書、Abitur・仏バカロレア・GCE/IGCE-A Level・"
    "欧州バカロレア等は資格別の成績証明書等を提出。"
)

EJU = {
    "生物生産学科": "2026年度日本留学試験は日本語。",
    "応用生物科学科": "2026年度日本留学試験は数学コース2。",
    "環境資源科学科": "2026年度日本留学試験は日本語、数学コース2、物理・化学・生物から2科目。",
    "地域生態システム学科": "2026年度日本留学試験は日本語、数学コース2、物理・化学・生物から2科目。",
    "共同獣医学科": "2026年度日本留学試験は理科の化学・生物の2科目。",
    "生命工学科": "2026年度日本留学試験は日本語、数学コース2、物理・化学・生物から2科目。",
    "生体医用システム工学科": "2026年度日本留学試験は日本語、数学コース2、物理と化学・生物から1科目。",
    "応用化学科": "2026年度日本留学試験は日本語、数学コース2、物理・化学。",
    "化学物理工学科": "2026年度日本留学試験は日本語、数学コース2、物理・化学。",
    "機械システム工学科": "2026年度日本留学試験は日本語、数学コース2、物理と化学・生物から1科目。",
    "知能情報システム工学科": "2026年度日本留学試験は日本語、数学コース2、物理と化学・生物から1科目。",
}


def update_master() -> None:
    path = ROOT / "data/canonical/kokkoritsu/master.csv"
    header, rows = read(path)
    hit = [r for r in rows if r.get("university") == "東京農工大学" and r.get("record_id", "").startswith("TUAT-2027-") and ("-SOC-" in r["record_id"] or "-FOR-" in r["record_id"])]
    if len(hit) != 15 or sum("-SOC-" in r["record_id"] for r in hit) != 4 or sum("-FOR-" in r["record_id"] for r in hit) != 11:
        raise SystemExit(f"Expected 4 adult and 11 private-foreign units; found {len(hit)}")

    for row in hit:
        row.update({
            "verified_on": DATE,
            "source_url": PAGE,
            "schedule_url": GUIDE,
            "guideline_url": GUIDE,
            "publication_status": "2027年度特別選抜学生募集要項公開済",
            "current_year_release_expected": "",
            "source_status": "2027年度特別選抜学生募集要項確認済",
            "detail_completeness": "complete（2027年度特別選抜学生募集要項まで確認済）",
            "verification_grade": "A",
            "academic_record_required": "Yes",
            "selection_document_review": "Yes",
            "application_start": "2027-01-14" if "-SOC-" in row["record_id"] else "2027-01-15",
            "application_end": "2027-01-20" if "-SOC-" in row["record_id"] else "2027-01-25",
            "final_result_date": "2027-03-06",
        })
        if "-SOC-" in row["record_id"]:
            row.update({
                "capacity": "若干名",
                "academic_record_type": "出身学校調査書、または資格別の卒業・成績証明書等",
                "academic_record_detail": ADULT_ACADEMIC,
                "documents_summary": ADULT_DOCS,
                "selection_written_exam": "Yes",
                "selection_interview": "Yes",
                "second_stage_start": "2027-02-25",
                "second_stage_end": "2027-02-26",
                "selection_process": "大学入学共通テストを免除。学科別の学力試験（理科・英語）、面接、志望理由書、出身学校調査書等を総合して選考。",
                "selection_method_detail": "学力試験は一般選抜前期日程と同内容。生物生産学科は化学・生物から1科目と英語、他3学科は物理・化学・生物から1科目と英語。試験は2027-02-25、面接は02-26。入学手続は2027-03-15 16時必着。",
                "notes": f"2026-09-28詳細再監査。公式2027特別選抜学生募集要項 p6-9,21：{GUIDE}。提出書類・調査書代替条件・学科別学力試験・日程を反映。入学手続期限は2027-03-15 16時必着。",
            })
        else:
            dept = row["department"]
            row.update({
                "capacity": "若干名",
                "academic_record_type": "資格経路別の卒業（見込）証明書・学業成績証明書または資格証書・成績評価証明書",
                "academic_record_detail": PFI_ACADEMIC,
                "documents_summary": PFI_DOCS,
                "english_requirement": "TOEIC L&R公開テスト500点以上またはTOEFL iBT 52点以上。出願初日から遡り2年以内。TOEFLはTest Dateスコアを利用し、Official Score ReportをETSから大学へ直送。",
                "subject_prerequisites": EJU[dept] + "出願資格経路により12年課程修了等が必要。",
                "selection_written_exam": "No",
                "selection_interview": "Yes",
                "selection_oral_exam": "Yes",
                "second_stage_start": "2027-02-26",
                "second_stage_end": "2027-02-26",
                "selection_process": "大学入学共通テストを免除。日本留学試験（800点）と面接試験（口頭試問を含む、200点）の計1000点、各種証明書等を総合して選考。",
                "selection_method_detail": EJU[dept] + "日本留学試験800点、面接（口頭試問を含む）200点、計1000点。面接は2027-02-26。入学手続は2027-03-15 16時必着。",
                "notes": f"2026-09-28詳細再監査。公式2027特別選抜学生募集要項 p11-17,21：{GUIDE}。資格経路別の成績書類、EJU科目、英語証明、提出書類を反映。TOEFL公式スコアはETS直送。入学手続期限は2027-03-15 16時必着。",
            })
    write(path, header, rows)


def update_operations() -> None:
    path = ROOT / "data/canonical/kokkoritsu/coverage.csv"
    header, rows = read(path)
    row = next(r for r in rows if r.get("university") == "東京農工大学")
    row.update({
        "research_status": "Master反映済・特別選抜詳細再監査済",
        "master_rows": "33",
        "current_year_status": "2027年度の特別選抜（社会人4・私費外国人留学生11）を詳細要項まで再監査済",
        "fallback_status": "不要（2027年度公式詳細要項確認済）",
        "checked_on": DATE,
        "official_source_url": PAGE,
        "notes": "2027年度公式入試体系および特別選抜詳細要項をMaster全33行と照合。社会人4・私費外国人留学生11募集単位の提出書類、成績関係書類、選考方法、日程、入学手続期限を反映。",
    })
    write(path, header, rows)

    path = ROOT / "data/operations/coverage_reaudit_2027.csv"
    header, rows = read(path)
    row = next(r for r in rows if r.get("source_dataset") == "kokkoritsu" and r.get("university") == "東京農工大学")
    row.update({
        "reaudit_status": "再監査済",
        "update_queue_open_count": "0",
        "last_audited_on": DATE,
        "notes": "2027年度公式入試体系・募集人員・日程・特別選抜詳細要項を確認しMaster全33行と照合。社会人4・私費外国人留学生11募集単位の提出書類、成績関係書類、選考方法、日程、入学手続期限まで反映。Kei-Net掲載範囲は別途クロスチェック済み。",
    })
    write(path, header, rows)

    path = ROOT / "data/operations/update_queue.csv"
    header, rows = read(path)
    row = next(r for r in rows if r.get("queue_id") == "UQ-2027-0037")
    row.update({
        "last_checked_on": DATE,
        "next_check_on": "",
        "action_status": "完了",
        "notes": "2026-08-28公開の2027年度特別選抜学生募集要項を確認。社会人4・私費外国人留学生11の計15行へ提出書類・成績関係書類・学科別選考方法・日程・入学手続期限を反映済。",
    })
    write(path, header, rows)

    path = ROOT / "data/operations/canonical_corrections_2027.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    correction = next(r for r in records if r.get("correction_id") == "CC-2027-0003")
    correction.update({
        "status": "applied_complete",
        "audit_note": "公式2027特別選抜学生募集要項を確認し、社会人4・私費外国人留学生11の全15行を詳細更新。出願書類・成績書類・学科別選考方法・日程・入学手続期限を記録。募集単位は公式実施学科一覧と照合済み。",
    })
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in records), encoding="utf-8")


def main() -> None:
    update_master()
    update_operations()
    print("Completed official detail review for TUAT: 15 Master rows")


if __name__ == "__main__":
    main()
