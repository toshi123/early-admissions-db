from pathlib import Path
import unittest

from early_admissions.update_acceptance import (
    _retarget_sqlite_schema_text,
    _retarget_unified_contract,
    _schema_contract_compatibility,
    _schema_identity_audit,
)


class UpdateAcceptanceSourceStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = {
            "path": Path("candidate_master.csv"),
            "coverage": Path("candidate_coverage.csv"),
            "research_requirements": Path("candidate_research.csv"),
            "candidate_schema": Path("candidate_schema.json"),
        }

    def _schema(self) -> dict:
        return {
            "version": "5.74",
            "dataset": "kokkoritsu_early_admissions_2027",
            "canonical_data": {
                "master": "candidate_master.csv",
                "coverage": "candidate_coverage.csv",
                "research_requirements": "candidate_research.csv",
                "schema": "candidate_schema.json",
            },
        }

    def test_explicit_unfrozen_is_a_stop_gate(self) -> None:
        schema = self._schema()
        schema["dataset_state"] = "UNFROZEN"
        schema["artifact_status"] = {"canonical_csv_json": "active_unfrozen"}
        result = _schema_identity_audit(
            "kokkoritsu", "5.74", schema, self.paths
        )
        self.assertTrue(result["identity_coherent"])
        self.assertTrue(result["explicitly_unfrozen"])
        self.assertEqual(result["effective_freeze_state"], "UNFROZEN")
        self.assertFalse(result["source_coherence_gate_passed"])


class UpdateAcceptanceFrozenAndSchemaCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.paths = {
            "path": Path("candidate_master.csv"),
            "coverage": Path("candidate_coverage.csv"),
            "research_requirements": Path("candidate_research.csv"),
            "candidate_schema": Path("candidate_schema.json"),
        }

    def _schema(self) -> dict:
        return {
            "version": "5.74",
            "dataset": "kokkoritsu_early_admissions_2027",
            "canonical_data": {
                "master": "candidate_master.csv",
                "coverage": "candidate_coverage.csv",
                "research_requirements": "candidate_research.csv",
                "schema": "candidate_schema.json",
            },
        }

    def test_reviewed_additive_declarations_are_compatible(self) -> None:
        current = {
            "enum_definitions": {"institution_type": ["国立", "公立", "私立"]},
            "normalization_rules": {"unknown_is_not_no": True},
        }
        candidate = {
            "enum_definitions": {
                **current["enum_definitions"],
                "fallback_previous_year": ["Yes", "No"],
            },
            "normalization_rules": {
                **current["normalization_rules"],
                "fallback_previous_year_values": ["Yes", "No"],
                "excel_in_canonical_freeze": False,
            },
        }
        result = _schema_contract_compatibility(
            current, candidate, ("enum_definitions", "normalization_rules")
        )
        self.assertTrue(result["contract_compatible_with_current"])
        self.assertEqual(result["incompatible_changed_keys"], [])

    def test_changed_or_unreviewed_declaration_remains_incompatible(self) -> None:
        current = {
            "enum_definitions": {"institution_type": ["国立", "公立", "私立"]}
        }
        candidate = {
            "enum_definitions": {
                "institution_type": ["国立", "公立"],
                "fallback_previous_year": ["Yes", "No"],
            }
        }
        result = _schema_contract_compatibility(
            current, candidate, ("enum_definitions",)
        )
        self.assertFalse(result["contract_compatible_with_current"])
        self.assertEqual(result["incompatible_changed_keys"], ["enum_definitions"])

    def test_isolated_unified_contract_versions_are_retargeted_together(self) -> None:
        contract = {
            "x-source-version-matrix": {"kokkoritsu": "5.61", "shidai": "0.97"},
            "$defs": {
                "sourceVersion": {"enum": ["5.61", "0.97"]},
                "sourcePairConstraint": {
                    "allOf": [
                        {
                            "if": {"properties": {"source_dataset": {"const": "kokkoritsu"}}},
                            "then": {"properties": {"source_version": {"const": "5.61"}}},
                        },
                        {
                            "if": {"properties": {"source_dataset": {"const": "shidai"}}},
                            "then": {"properties": {"source_version": {"const": "0.97"}}},
                        },
                    ]
                },
            },
        }
        _retarget_unified_contract(
            contract, {"kokkoritsu": "5.81", "shidai": "1.08"}
        )
        self.assertEqual(
            contract["$defs"]["sourceVersion"]["enum"], ["5.81", "1.08"]
        )
        self.assertEqual(
            [
                item["then"]["properties"]["source_version"]["const"]
                for item in contract["$defs"]["sourcePairConstraint"]["allOf"]
            ],
            ["5.81", "1.08"],
        )

    def test_isolated_sqlite_source_versions_are_retargeted(self) -> None:
        sql = "source_version IN ('5.61', '0.97'); pair='5.61'; other='0.97'"
        result = _retarget_sqlite_schema_text(
            sql,
            {"kokkoritsu": "5.61", "shidai": "0.97"},
            {"kokkoritsu": "5.81", "shidai": "1.08"},
        )
        self.assertNotIn("'5.61'", result)
        self.assertNotIn("'0.97'", result)
        self.assertEqual(result.count("'5.81'"), 2)
        self.assertEqual(result.count("'1.08'"), 2)

    def test_explicit_frozen_bundle_passes_source_state_gate(self) -> None:
        schema = self._schema()
        schema["dataset_state"] = "FROZEN"
        result = _schema_identity_audit(
            "kokkoritsu", "5.74", schema, self.paths
        )
        self.assertTrue(result["identity_coherent"])
        self.assertEqual(result["effective_freeze_state"], "FROZEN")
        self.assertTrue(result["source_coherence_gate_passed"])

    def test_source_freeze_status_is_an_equivalent_frozen_state(self) -> None:
        schema = self._schema()
        schema["sources"] = {"freeze_status": "FROZEN"}
        result = _schema_identity_audit(
            "kokkoritsu", "5.74", schema, self.paths
        )
        self.assertTrue(result["source_coherence_gate_passed"])

    def test_version_mismatch_fails_even_when_frozen(self) -> None:
        schema = self._schema()
        schema["version"] = "5.73"
        schema["sources"] = {"freeze_status": "FROZEN"}
        result = _schema_identity_audit(
            "kokkoritsu", "5.74", schema, self.paths
        )
        self.assertFalse(result["identity_coherent"])
        self.assertFalse(result["source_coherence_gate_passed"])


if __name__ == "__main__":
    unittest.main()
