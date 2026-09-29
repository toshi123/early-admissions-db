#!/usr/bin/env python3
"""Apply the verified part of the Hokkaido-area 2027 reaudit batch."""

from __future__ import annotations

import csv
import json
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-09-28"
MUR_PAGE = "https://muroran-it.ac.jp/entrance/admission/exam/uee/"
MUR_AO = "https://muroran-it.ac.jp/uploads/sites/6/2026/08/R9_sougo_bosyu.pdf"
MUR_SPECIAL = "https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027tokubetsu-1.pdf"
MUR_PFI = "https://muroran-it.ac.jp/uploads/sites/6/2026/08/2027shihiyoukou-1.pdf"
OBI_PAGE = "https://www.obihiro.ac.jp/undergrad-adm"
OBI_RETURN = "https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9kikoku.pdf"
OBI_SOCIAL = "https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9syakai.pdf"
OBI_IB = "https://www.obihiro.ac.jp/wp/wp-content/uploads/2026/08/R9Baccalaureate.pdf"


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), [dict(r) for r in reader]


def write_csv(path: Path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header, lineterminator="\n", extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def mur_rows(header, rows):
    existing = [r for r in rows if r["university"] == "室蘭工業大学"]
    if len(existing) != 2:
        raise SystemExit(f"Expected 2 existing Muroran rows; found {len(existing)}")
    if any(r["record_id"].startswith("MUR-2027-AO-") for r in rows):
        raise SystemExit("Muroran candidates already exist; refusing to append duplicate rows")
    base = deepcopy(existing[0])
    out = []
    shared = {
        "admission_year": "2027", "institution_type": "国立", "university": "室蘭工業大学",
        "prefecture": "北海道", "academic_field": "工学・理学", "stem_flag": "True",
        "faculty_school": "理工学部", "school_recommendation_required": "No",
        "school_nomination_limit": "", "school_nomination_limit_total": "",
        "school_nomination_limit_rule": "", "exclusive_enrollment_status": "専願",
        "exclusive_enrollment": "合格した場合は室蘭工業大学への入学を確約すること。",
        "exclusive_enrollment_evidence": "各2027年度募集要項で合格後の入学確約を確認。",
        "exclusive_enrollment_evidence_page": "募集要項「出願資格」", "exclusive_enrollment_evidence_url": MUR_AO,
        "common_test_required": "No", "common_test_usage": "大学入学共通テストを課さない。",
        "research_activity_level": "not_specified", "research_requirement_required": "No",
        "research_activity_detail": "Unknown", "research_requirement_summary": "Unknown",
        "academic_record_required": "Yes", "selection_document_review": "Yes",
        "selection_oral_exam": "No", "selection_essay": "No", "selection_written_exam": "Yes",
        "selection_practical": "No", "selection_group_discussion": "No", "selection_aptitude_test": "No",
        "selection_common_test": "No", "source_status": "2027年度公式募集要項確認済",
        "detail_completeness": "partial（公式要項確認済・一部項目Unknown）", "verification_grade": "A",
        "verified_on": DATE, "source_url": MUR_PAGE, "schedule_url": MUR_AO,
        "guideline_url": MUR_AO, "information_year": "2027",
        "publication_status": "2027年度公式募集要項公開済", "fallback_previous_year": "No",
        "current_year_release_expected": "", "previous_year_source_url": "", "fallback_note": "",
    }
    slots = [
        ("AO1-CRE-GEN", "創造工学科", "総合型選抜Ⅰ", "総合型選抜Ⅰ", "一般枠", "64", "No", MUR_AO),
        ("AO1-CRE-WOMEN", "創造工学科", "総合型選抜Ⅰ", "総合型選抜Ⅰ", "女子枠", "6", "No", MUR_AO),
        ("AO1-SYS-GEN", "システム理化学科", "総合型選抜Ⅰ", "総合型選抜Ⅰ", "一般枠", "46", "No", MUR_AO),
        ("AO1-SYS-WOMEN", "システム理化学科", "総合型選抜Ⅰ", "総合型選抜Ⅰ", "女子枠", "4", "No", MUR_AO),
        ("AO2-CRE-GEN", "創造工学科", "総合型選抜Ⅱ", "総合型選抜Ⅱ", "一般枠", "9", "No", MUR_AO),
        ("AO2-CRE-WOMEN", "創造工学科", "総合型選抜Ⅱ", "総合型選抜Ⅱ", "女子枠", "3", "No", MUR_AO),
        ("AO2-SYS-GEN", "システム理化学科", "総合型選抜Ⅱ", "総合型選抜Ⅱ", "一般枠", "6", "No", MUR_AO),
        ("AO2-SYS-WOMEN", "システム理化学科", "総合型選抜Ⅱ", "総合型選抜Ⅱ", "女子枠", "2", "No", MUR_AO),
        ("AO-NIGHT", "創造工学科（夜間主コース）", "総合型選抜", "総合型選抜（夜間主）", "夜間主", "10", "No", MUR_AO),
        ("RETURN-CRE", "創造工学科", "総合型選抜", "総合型選抜（帰国子女）", "帰国子女", "若干名", "Yes", MUR_SPECIAL),
        ("RETURN-SYS", "システム理化学科", "総合型選抜", "総合型選抜（帰国子女）", "帰国子女", "若干名", "Yes", MUR_SPECIAL),
        ("SOCIAL-NIGHT", "創造工学科（夜間主コース）", "総合型選抜", "総合型選抜（社会人）", "社会人", "若干名", "No", MUR_SPECIAL),
        ("COMPANY-NIGHT", "創造工学科（夜間主コース）", "総合型選抜", "総合型選抜（企業推薦型）", "企業推薦型", "若干名", "No", MUR_SPECIAL),
        ("PFI-CRE", "創造工学科", "総合型選抜", "総合型選抜（私費外国人留学生）", "私費外国人留学生", "若干名", "No", MUR_PFI),
        ("PFI-SYS", "システム理化学科", "総合型選抜", "総合型選抜（私費外国人留学生）", "私費外国人留学生", "若干名", "No", MUR_PFI),
    ]
    for suffix, dept, cat, name, slot, cap, returnee, guide in slots:
        r = deepcopy(base)
        r.update(shared)
        r.update({
            "record_id": f"MUR-2027-{suffix}", "department": dept,
            "selection_category": cat, "selection_name": name, "slot_type": slot,
            "capacity": cap, "international_baccalaureate_flag": "No",
            "private_foreign_student_flag": "Yes" if suffix.startswith("PFI") else "No",
            "returnee_flag": returnee, "regional_quota_flag": "No",
            "adult_selection_flag": "Yes" if suffix.startswith("SOCIAL") else "No",
            "exclusive_enrollment_evidence_url": guide,
            "schedule_url": guide, "guideline_url": guide,
        })
        if suffix.startswith(("AO1", "AO2")):
            category = "総合型選抜Ⅰ" if suffix.startswith("AO1") else "総合型選抜Ⅱ"
            female = "女子枠" in suffix
            lower = "全体の評定平均値3.5以上" + ("。数学・理科の指定単位修得が必要。" if suffix.startswith("AO1") else "。数学・理科の指定単位に加え、課題研究等の履修が必要。")
            r.update({"gpa_requirement": lower, "subject_prerequisites": "募集要項所定の数学・理科履修単位要件を満たすこと。",
                      "eligibility_graduation": "高等学校等の卒業者又は2027年3月卒業見込み等。合格後の入学確約が必要。",
                      "english_requirement": "個別の英語資格要件なし。", "academic_record_type": "調査書",
                      "academic_record_detail": "出身学校長作成・厳封の調査書。学習成績概評、特別活動、探究活動等を評価。",
                      "documents_summary": "入学志願票、写真票、調査書、自己推薦書。",
                      "selection_interview": "Yes", "selection_method_detail": "大学入学共通テストを免除。基礎学力検定、面接、自己推薦書及び調査書で選抜。女子枠志願者は一般枠との併願可。" + ("女子枠面接ではダイバーシティ理解等も評価。" if female else ""),
                      "selection_process": "基礎学力検定、面接、自己推薦書、調査書を総合して判定。",
                      "interview_detail": "志望学科・専門分野への関心、志望動機、考え、勉学姿勢等を問う。女子枠はダイバーシティに関する質問を含む。",
                      "written_exam_detail": "基礎学力検定。総合型選抜Ⅰは数学・理科、Ⅱは数学を出題。",
                      "application_start": "2026-09-09", "application_end": "2026-09-16", "web_registration_period": "2026-09-09～2026-09-16",
                      "final_result_date": "2026-11-02", "second_stage_start": "2026-11-05", "second_stage_end": "2026-11-12",
                      "notes": f"2026-09-28再監査。公式2027年度{category}要項 p.4-7,9-12。募集単位は学科×一般/女子枠。女子枠は一般枠との併願可、コースは入学後の分属希望で行を分割しない。公式要項で特定できない詳細はUnknownのまま。出願資格・日程の詳細は{guide}"})
        elif suffix == "AO-NIGHT":
            r.update({"gpa_requirement": "数値による評定要件の記載なし。", "eligibility_graduation": "高等学校等卒業者又は同等以上の学力を有する者。合格後の入学確約が必要。",
                      "english_requirement": "個別の英語資格要件なし。", "subject_prerequisites": "募集要項に定める数学・理科の履修要件。詳細はUnknown。",
                      "academic_record_type": "調査書", "academic_record_detail": "出身学校長作成・厳封の調査書。",
                      "documents_summary": "入学志願票、写真票、調査書、自己推薦書。", "selection_interview": "Yes",
                      "selection_process": "大学入学共通テストを免除。基礎学力検定、面接、自己推薦書及び調査書で選抜。",
                      "selection_method_detail": "夜間主コース創造工学科単位。基礎学力検定・面接・自己推薦書・調査書を総合評価。",
                      "written_exam_detail": "基礎学力検定（数学・理科）。", "application_start": "2026-09-09", "application_end": "2026-09-16",
                      "web_registration_period": "2026-09-09～2026-09-16", "final_result_date": "2026-11-02", "second_stage_start": "2026-11-05", "second_stage_end": "2026-11-12",
                      "notes": f"2026-09-28再監査。公式2027年度総合型選抜要項「夜間主」節。出願単位は創造工学科（夜間主）1単位。コース希望は出願時の別単位ではない。{guide}"})
        elif suffix.startswith("RETURN"):
            r.update({"gpa_requirement": "数値による評定要件の記載なし。", "eligibility_graduation": "日本国籍又は永住許可を有し、保護者の海外勤務等により外国の学校教育を受けた者。所定の外国12年課程又は外国大学入学資格を満たすこと。",
                      "english_requirement": "英語資格要件の詳細は募集要項の資格経路別条件を参照。Unknown。", "subject_prerequisites": "Unknown",
                      "academic_record_type": "最終学校の修了証明書・成績証明書、資格経路別証明書。該当者は日本の高校調査書。",
                      "academic_record_detail": "外国学校の成績証明書。IB等資格経路では資格証書と科目別成績証明書。日本の高校在学歴がある場合は調査書等を追加。",
                      "documents_summary": "入学志願票、受験票・写真票、最終学校の修了証明書・成績証明書、資格別証明書、推薦書、志望理由書、学習記録、TOEFL/IELTSスコア等（資格経路により異なる）。",
                      "selection_interview": "Yes", "selection_essay": "Yes", "selection_process": "出願書類、英語学部試験、小論文及び面接を総合して判定。",
                      "selection_method_detail": "創造工学科・システム理化学科ごとの帰国生選抜。出願資格と提出書類は資格経路で異なる。募集人員は各学科若干名。",
                      "application_start": "2026-09-09", "application_end": "2026-09-16", "final_result_date": "2026-11-02",
                      "notes": f"2026-09-28再監査。公式2027帰国子女要項 p.4-8。学科ごとに若干名、2学科で2出願単位。帰国生flag=Yes。募集要項の資格経路差を保持し、確定できない一律要件はUnknown。{guide}"})
        elif suffix.startswith("SOCIAL") or suffix.startswith("COMPANY"):
            is_social = suffix.startswith("SOCIAL")
            r.update({"school_recommendation_required": "Yes" if not is_social else "No",
                      "gpa_requirement": "数値による評定要件の記載なし。",
                      "eligibility_graduation": ("高等学校卒業等又は同等以上の学力を有し、2027年3月31日までに満23歳以上となる者。合格後の入学確約が必要。" if is_social else "高等学校卒業等又は同等以上の学力を有し、2027年3月31日までに満20歳以上かつ企業等の正規職員として1年以上勤務し、所属長の推薦を受ける者。"),
                      "english_requirement": "個別の英語資格要件なし。", "subject_prerequisites": "Unknown",
                      "academic_record_type": "調査書又は卒業・成績証明書等（資格経路による）。",
                      "academic_record_detail": "出願資格に応じた出身学校の調査書・証明書。",
                      "documents_summary": "入学志願票、受験票・写真票、調査書又は資格別証明書、自己推薦書・志望理由書" + ("、企業推薦書" if not is_social else "") + "。",
                      "selection_interview": "Yes", "selection_process": "基礎学力検定、面接及び志望理由書等の出願書類で総合判定。" if is_social else "面接、志望理由書及び企業推薦書で総合判定。",
                      "selection_method_detail": "創造工学科（夜間主コース）1出願単位。" + ("社会人選抜は23歳以上。" if is_social else "企業推薦型は20歳以上・正規職員1年以上・所属長推薦。") + "出願期間2026-10-13～10-20、合格発表2026-12-04、入学手続2027-02-11～02-17。",
                      "application_start": "2026-10-13", "application_end": "2026-10-20", "final_result_date": "2026-12-04",
                      "second_stage_start": "2027-02-11", "second_stage_end": "2027-02-17",
                      "notes": f"2026-09-28再監査。公式2027帰国・社会人・企業推薦型要項。夜間主創造工学科の方式別1募集単位。社会人のみadult_selection_flag=Yes。企業推薦は年齢・職歴要件だけでadult扱いしない。{guide}"})
        else:
            r.update({"gpa_requirement": "数値による評定要件の記載なし。", "eligibility_graduation": "外国の学校教育による12年課程修了等。日本の高校卒業者及び日本の永住許可者は出願不可。",
                      "english_requirement": "TOEFL iBT 32点以上（旧スコア換算、2024年12月～2026年12月受験、My Best Scores不可）。",
                      "subject_prerequisites": "EJU：日本語225点以上、数学コース2必須、理科は学科指定科目。創造工学科は物理必須＋化学/生物から1科目、システム理化学科は物理/化学/生物から2科目。数学・理科合計220点以上。",
                      "academic_record_type": "最終学校の成績証明書、卒業証明書等。",
                      "academic_record_detail": "最終出身学校の成績・修了証明を提出。外国語書類は和訳又は英訳を添付。",
                      "documents_summary": "入学志願票、写真票、最終学校の卒業・成績証明書、EJU成績、TOEFLスコア、推薦書、志望理由書等。",
                      "selection_interview": "Yes", "selection_process": "EJU、TOEFL成績、成績証明書、推薦書、志望理由書及び面接を総合して選考。",
                      "selection_method_detail": "学科別（創造工学科／システム理化学科）の私費外国人留学生選抜。各学科若干名。EJU日本語225点以上、数学・理科合計220点以上及びTOEFL iBT 32点以上。",
                      "application_start": "2026-12-22", "application_end": "2027-01-07", "final_result_date": "2027-01-22",
                      "second_stage_start": "2027-01-25", "second_stage_end": "2027-02-02",
                      "notes": f"2026-09-28再監査。公式2027私費外国人留学生要項 p.5,10-11。学科単位2募集枠。私費外国人flag=Yes。EJU・TOEFL要件、入学手続期限を反映。{guide}"})
        # Only flags with an explicitly named route are set to Yes.
        for c in ["international_baccalaureate_flag", "private_foreign_student_flag", "returnee_flag", "regional_quota_flag", "adult_selection_flag"]:
            r.setdefault(c, "No")
        out.append(r)
    rows.extend(out)
    return len(out)


def obi_rows(header, rows):
    if any(r["record_id"].startswith("OBI-2027-RET") for r in rows):
        raise SystemExit("Obihiro special candidates already exist; refusing duplicate append")
    base = deepcopy(next(r for r in rows if r["record_id"] == "OBI-2027-REC-C"))
    definitions = [
        ("RET", "畜産科学課程", "帰国生選抜", "帰国生", "若干人", OBI_RETURN, "No", "Yes", "No", "No", "No"),
        ("SOC", "畜産科学課程", "社会人選抜", "社会人", "若干人", OBI_SOCIAL, "No", "No", "No", "No", "Yes"),
        ("IB-ANI", "畜産科学課程", "国際バカロレア選抜", "国際バカロレア", "若干人", OBI_IB, "Yes", "No", "No", "No", "No"),
        ("IB-VET", "共同獣医学課程", "国際バカロレア選抜", "国際バカロレア", "若干人", OBI_IB, "Yes", "No", "No", "No", "No"),
    ]
    for suffix, dept, name, slot, cap, guide, ib, pfi, ret, regional, adult in definitions:
        r = deepcopy(base)
        r.update({"record_id": f"OBI-2027-{suffix}", "department": dept, "selection_category": name,
                  "selection_name": name, "slot_type": slot, "capacity": cap,
                  "international_baccalaureate_flag": ib, "private_foreign_student_flag": pfi,
                  "returnee_flag": ret, "regional_quota_flag": regional, "adult_selection_flag": adult,
                  "source_url": OBI_PAGE, "schedule_url": guide, "guideline_url": guide,
                  "verified_on": DATE, "source_status": "2027年度公式募集要項確認済",
                  "publication_status": "2027年度公式募集要項公開済", "current_year_release_expected": "",
                  "fallback_previous_year": "No", "previous_year_source_url": "", "fallback_note": "",
                  "common_test_required": "No", "common_test_usage": "大学入学共通テストを免除。",
                  "school_recommendation_required": "No", "school_nomination_limit": "", "school_nomination_limit_total": "",
                  "school_nomination_limit_rule": "", "research_activity_level": "not_specified",
                  "research_requirement_required": "No", "research_activity_detail": "Unknown", "research_requirement_summary": "Unknown",
                  "academic_record_required": "Yes", "academic_record_type": "募集要項記載の資格証明書・成績証明書等",
                  "selection_document_review": "Yes", "selection_oral_exam": "No", "selection_presentation": "No",
                  "selection_written_exam": "Yes", "selection_practical": "No", "selection_aptitude_test": "No",
                  "selection_common_test": "No", "detail_completeness": "partial（2027年度公式要項確認済）",
                  "verification_grade": "A", "notes": f"2026-09-28公式2027年度募集要項再監査。出願単位は{dept}の方式別枠。課程内ユニットは入学後分属のため分割しない。詳細値は選抜要項本文に基づき反映。{guide}"})
        # Clear route-specific values inherited from the recommendation template.
        r.update({"gpa_requirement": "Unknown", "subject_prerequisites": "Unknown",
                  "school_nomination_limit": "", "school_nomination_limit_total": "",
                  "school_nomination_limit_rule": "", "web_registration_period": "",
                  "application_start": "", "application_end": "", "first_stage_result_date": "",
                  "second_stage_start": "", "second_stage_end": "", "final_result_date": "",
                  "selection_interview": "No", "selection_essay": "No", "selection_written_exam": "No",
                  "selection_group_discussion": "No", "interview_detail": "", "essay_detail": "",
                  "written_exam_detail": "", "selection_method_detail": "",
                  "exclusive_enrollment_status": "専願",
                  "exclusive_enrollment": "合格した場合は帯広畜産大学への入学を確約すること。",
                  "exclusive_enrollment_evidence": "2027年度当該選抜募集要項の出願資格に入学確約を記載。",
                  "exclusive_enrollment_evidence_page": "募集要項「出願資格・要件」",
                  "exclusive_enrollment_evidence_url": guide})
        if suffix == "RET":
            r.update({"eligibility_graduation": "日本国籍又は永住許可を有し、外国で所定の12年課程等を修了した帰国生。最終学年を含む2年以上の在学等の条件あり。",
                      "english_requirement": "TOEFL又はIELTS Academic-moduleのスコア提出（2024-04-01以降受験）。",
                      "academic_record_detail": "最終出身学校の卒業（見込）証明書・成績証明書。資格経路別にIB等資格証書・成績評価証明書を提出。該当者は推薦書、TOEFL/IELTS成績、学習記録を提出。",
                      "documents_summary": "入学志願票、受験票・写真票、最終学校の修了・成績証明書又は資格別証明書、推薦書（該当者）、TOEFL/IELTS、志望理由書、学習記録等。",
                      "selection_interview": "Yes", "selection_essay": "Yes", "selection_process": "英語学部試験、小論文、面接、志望理由書及び成績証明書等を総合評価。",
                      "selection_method_detail": "畜産科学課程1単位、募集人員若干人。出願2026-10-23～10-29、合格発表2026-12-08、入学手続2026-12-08～12-23。",
                      "application_start": "2026-10-23", "application_end": "2026-10-29", "final_result_date": "2026-12-08",
                      "second_stage_start": "2026-12-08", "second_stage_end": "2026-12-23"})
        elif suffix == "SOC":
            r.update({"eligibility_graduation": "社会人選抜の出願資格を満たす者。",
                      "english_requirement": "外部英語試験スコアを提出。基準値の有無は募集要項に明確な数値記載なし。",
                      "academic_record_detail": "出身学校の成績証明書等。出願資格に応じた学校歴証明を提出。",
                      "documents_summary": "入学志願票、写真票、出身学校証明書・成績証明書、英語外部試験スコア、志望理由書等。",
                      "selection_interview": "Yes", "selection_essay": "Yes", "selection_process": "英語学部試験、小論文、面接、志望理由書及び成績関係書類を総合評価。",
                      "selection_method_detail": "畜産科学課程1単位、募集人員若干人。出願2026-10-23～10-29。",
                      "application_start": "2026-10-23", "application_end": "2026-10-29"})
        else:
            r.update({"eligibility_graduation": "IBフルディプロマを2025年4月～2027年3月に取得（見込を含む）、2027年3月31日までに18歳に達する者。課程別のIB科目要件を満たすこと。",
                      "english_requirement": "TOEFL又はIELTSの外部英語試験成績を提出（英語母語者を除く）。",
                      "academic_record_detail": "IB資格証書、成績評価証明、EE/TOK/CAS等の学習成果資料を提出。",
                      "documents_summary": "IB資格証書、志望理由書、学習記録（EE・TOK・CAS）、英語外部試験成績、成績関係書類等。",
                      "selection_interview": "Yes", "selection_essay": "Yes", "selection_process": "出願書類、小論文及び個人面接を総合評価。",
                      "selection_method_detail": f"{dept}1単位、募集人員若干人。出願2026-10-23～10-29、試験2026-11-28。",
                      "application_start": "2026-10-23", "application_end": "2026-10-29"})
        rows.append(r)
    return len(definitions)


def update_amu(rows):
    hit = [r for r in rows if r["university"] == "旭川医科大学"]
    if {r["record_id"] for r in hit} != {"AMU-2027-AO-MED", "AMU-2027-REC-MED", "AMU-2027-REC-NUR"}:
        raise SystemExit("Asahikawa Medical Master rows differ from the reviewed three units")
    for r in hit:
        r["verified_on"] = DATE
        r["notes"] = (r.get("notes", "") + " 2026-09-28再照合：旭川医科大学公式2027年度特別選抜要項及び入試日程を再確認。" +
                      "北海道特別選抜（医学科40）、道北・道東特別選抜（医学科7）、学校推薦型（看護学科10）の3出願単位でMaster一致。")


def main():
    mpath = ROOT / "data/canonical/kokkoritsu/master.csv"
    mh, mr = read_csv(mpath)
    mur_added = mur_rows(mh, mr)
    obi_added = obi_rows(mh, mr)
    update_amu(mr)
    write_csv(mpath, mh, mr)

    # Canonical coverage for completed/partially completed institutions.
    path = ROOT / "data/canonical/kokkoritsu/coverage.csv"
    h, rows = read_csv(path)
    counts = {"室蘭工業大学": 17, "帯広畜産大学": 8, "旭川医科大学": 3}
    notes = {
        "室蘭工業大学": "2027年度公式募集要項をMaster全17募集単位と照合。学校推薦2既収録に加え15単位を追加。学科×一般/女子枠、帰国生2、夜間主各選抜、私費外国人2を確認。コースは入学後分属のため分割せず。中国引揚等子女は公式募集停止予告により対象外。",
        "帯広畜産大学": "2027年度公式要項を確認。AO1、学校推薦A/B/C3、帰国生1、社会人1、IB2の計8募集単位。私費外国人留学生要項は公式入試日程で10月中旬公表予定のため未反映・再確認待ち。畜産科学課程のユニットは入学後分属のため分割せず。",
        "旭川医科大学": "2027年度公式特別選抜要項・日程をMaster3行と照合。医学科北海道特別選抜40、医学科道北・道東特別選抜7、看護学科学校推薦10。新規募集単位なし。",
    }
    for r in rows:
        u = r["university"]
        if u not in counts: continue
        r.update({"research_status": "Master反映済・2027年度詳細再監査済" if u != "帯広畜産大学" else "一部反映済・私費外国人要項公開待ち",
                  "master_rows": str(counts[u]), "current_year_status": notes[u], "fallback_status": "不要（確認済み選抜は2027年度公式資料あり）",
                  "checked_on": DATE, "notes": notes[u]})
    write_csv(path, h, rows)

    # Operations coverage: close the three worked institutions and keep explicit holds for Otaru/Kitami.
    path = ROOT / "data/operations/coverage_reaudit_2027.csv"
    h, rows = read_csv(path)
    op_notes = {
        "室蘭工業大学": ("再監査済", "2027年度募集要項により17単位、Master既収録2・追加15を確認。AO I/IIは学科×一般/女子枠、女子枠と一般枠は併願可。コースは入学後分属。confirmed missing=0。詳細はUnknown項目を残して出典・根拠を記載。"),
        "帯広畜産大学": ("追加確認待ち", "2027年度AO・推薦・帰国生・社会人・IB要項を確認し、Master4行に追加4（帰国1、社会人1、IB畜産科学1、IB共同獣医1）。私費外国人選抜の2027年度詳細要項は10月中旬公表予定。新要項確認までPFIを推測追加しない。"),
        "旭川医科大学": ("再監査済", "公式2027特別選抜要項・日程を既存3行と照合。選抜単位・募集人員・出願書類・日程の対応に欠落候補なし。"),
        "小樽商科大学": ("要項公開待ち", "2027年度公式ページで昼間学校推薦型・私費外国人の詳細募集要項未公表を確認。確定済みの他方式は既存Masterのまま維持し、未公表選抜の追加・詳細補完は行わない。公開後、志願票/Web入力項目、出願単位、書類、日程を公式要項で再確認する。"),
        "北見工業大学": ("要項公開待ち", "2027年度公式募集ページに総合型・私費外国人の要項は掲載、学校推薦型は2026年度要項のみ掲載。今回の対象である2027詳細要項未確認のためcanonical変更なし。2027学校推薦要項公開後、推薦枠・出願単位・提出物・日程を再確認する。"),
    }
    current_rows = {u: sum(1 for r in mr if r["university"] == u) for u in op_notes}
    for r in rows:
        u = r["university"]
        if u not in op_notes: continue
        status, note = op_notes[u]
        r.update({"reaudit_status": status, "official_system_checked": "実施済", "capacity_table_checked": "実施済",
                  "schedule_checked": "実施済", "guideline_index_checked": "実施済", "master_compared": "実施済",
                  "last_audited_on": DATE, "notes": note})
        if u == "室蘭工業大学":
            r.update({"missing_candidate_count": "0", "ambiguous_candidate_count": "0", "obsolete_candidate_count": "0", "update_queue_open_count": "0", "kawai_crosscheck": "未実施"})
        elif u == "帯広畜産大学":
            r.update({"missing_candidate_count": "0", "ambiguous_candidate_count": "0", "obsolete_candidate_count": "0", "update_queue_open_count": "1", "kawai_crosscheck": "未実施"})
        elif u == "旭川医科大学":
            r.update({"missing_candidate_count": "0", "ambiguous_candidate_count": "0", "obsolete_candidate_count": "0", "update_queue_open_count": "0", "kawai_crosscheck": "実施済"})
        else:
            r.update({"update_queue_open_count": "1", "kawai_crosscheck": "実施不能"})
    write_csv(path, h, rows)

    # Update existing queues and add the Obihiro PFI publication watch.
    path = ROOT / "data/operations/update_queue.csv"
    h, qs = read_csv(path)
    for q in qs:
        if q["queue_id"] == "UQ-2027-0047":
            q.update({"last_checked_on": DATE, "next_check_on": "", "action_status": "完了", "actual_release_on": DATE,
                      "notes": "公式2027詳細要項を照合し、総合型I/II・夜間主・帰国子女・社会人・企業推薦型・私費外国人の15追加募集単位をMasterへ反映。追加15行の不明項目はUnknownを保持。"})
        if q["queue_id"] in {"UQ-2027-0001", "UQ-2027-0002"}:
            q.update({"last_checked_on": DATE, "next_check_on": "2026-10-01", "action_status": "待機",
                      "notes": ("2026-09-28公式2027年度詳細要項の公開状況を再確認。未公表のためcanonical未変更。公開後に出願方法・入力票・募集単位・書類・日程を再確認する。" if q["queue_id"] == "UQ-2027-0001" else "2026-09-28公式ページ再確認。学校推薦型は2026年度要項のみ。2027年度詳細要項が公開されたら出願枠・推薦条件・提出書類を再監査し、canonicalと照合する。")})
    if not any(q["queue_id"] == "UQ-2027-0048" for q in qs):
        qs.append({"queue_id":"UQ-2027-0048","institution_type":"国立","university":"帯広畜産大学","faculty_school":"畜産学部","selection_name":"私費外国人留学生選抜","document_type":"2027年度学生募集要項","publication_status":"公開予定","release_expected_text":"2026年10月中旬","release_expected_from":"2026-10-11","release_expected_to":"2026-10-20","release_schedule_url":"https://www.obihiro.ac.jp/undergrad-adm","last_checked_on":DATE,"next_check_on":"2026-10-11","actual_release_on":"","action_status":"待機","related_record_id":"","notes":"2027年度入学者選抜要項に詳細要項公表予定が10月中旬と明記。2026年度資料でcanonicalを推測補完しない。2027詳細公開後に出願課程単位、EJU/英語、資格別成績証明、日程・手続を確認。"})
    write_csv(path, h, qs)

    # Append machine-readable correction records without rewriting prior entries.
    path = ROOT / "data/operations/canonical_corrections_2027.jsonl"
    existing = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = {r["correction_id"] for r in existing}
    additions = [
        {"correction_id":"CC-2027-0011","dataset":"kokkoritsu","university":"室蘭工業大学","detected_on":DATE,"status":"applied_complete","reason":"公式2027詳細募集要項を確認し、missing candidates 15単位をMasterに反映。","existing_master_rows":2,"confirmed_missing_units_total":15,"applied_master_rows":15,"current_university_master_rows":17,"official_source":"2027年度室蘭工業大学入学試験概要・各学生募集要項","official_url":MUR_PAGE,"audit_note":"AO I/IIは学科×一般/女子枠、夜間主・帰国・社会人・企業推薦・私費外国人は要項別の実際の学科単位で構成。コースは入学後分属。女子枠は一般枠との併願可。中国引揚等子女選抜は募集停止。確認できない項目はUnknownとして保持。"},
        {"correction_id":"CC-2027-0012","dataset":"kokkoritsu","university":"帯広畜産大学","detected_on":DATE,"status":"applied_partial_pending_detail","reason":"2027年度要項で帰国生・社会人・IBの募集単位を確認し、Master欠落4単位を追加。私費外国人要項は未公表。","existing_master_rows":4,"confirmed_missing_units_total":4,"applied_master_rows":4,"current_university_master_rows":8,"official_source":"2027年度帯広畜産大学帰国生・社会人・国際バカロレア選抜学生募集要項","official_url":OBI_PAGE,"update_queue_id":"UQ-2027-0048","audit_note":"帰国生1（畜産科学課程）、社会人1（畜産科学課程）、IB2（畜産科学課程・共同獣医学課程）を追加。私費外国人留学生は10月中旬公表予定のため未追加。"},
    ]
    for item in additions:
        if item["correction_id"] not in ids: existing.append(item)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in existing), encoding="utf-8")

    # Pilot rows for the verified selection-unit/deadline fields; no crosswalk changes.
    path = ROOT / "data/operations/candidate_fields_pilot_2027.csv"
    h, pilots = read_csv(path)
    pilot_ids = {p["record_id"] for p in pilots}
    for r in mr:
        if r["record_id"].startswith("MUR-2027-") and r["record_id"] not in pilot_ids:
            pilots.append({"source_dataset":"kokkoritsu","record_id":r["record_id"],"university":r["university"],"faculty_school":r["faculty_school"],"department":r["department"],"selection_name":r["selection_name"],"slot_type":r["slot_type"],"enrollment_procedure_deadline":r.get("second_stage_end", ""),"enrollment_procedure_detail":r.get("selection_method_detail", ""),"graduation_eligibility_status":"review_required","years_since_graduation_max":"","graduation_eligibility_detail":r.get("eligibility_graduation", ""),"regional_requirement_status":"No","regional_requirement_detail":"公式2027募集要項で地域枠の指定なし。","gender_requirement":"Yes" if "女子枠" in r["slot_type"] else "No","gender_requirement_detail":"戸籍上女性を対象とする女子枠。一般枠との併願可。" if "女子枠" in r["slot_type"] else "","guideline_url":r.get("guideline_url", ""),"reviewed_on":DATE,"pilot_status":"reviewed","notes":"公式2027年度募集要項に基づく候補行。Unknown/要項経路差はMaster notesに明記。"})
    write_csv(path, h, pilots)

    print(f"Applied batch candidates: Muroran +{mur_added}; Obihiro +{obi_added}; Asahikawa 3 reviewed; Master rows={len(mr)}")


if __name__ == "__main__":
    main()
