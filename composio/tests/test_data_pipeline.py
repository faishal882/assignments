from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GeneratedDataTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_identity_registry_is_brief_derived(self) -> None:
        identities = self.load("data/app-identities.json")
        self.assertEqual(len(identities), 100)
        self.assertTrue(all(row["source"] == "assignment_brief" for row in identities))
        self.assertTrue(all(row["hosts"] for row in identities))
        self.assertNotIn("curation", json.dumps(identities).lower())

    def test_verification_totals_are_claim_derived(self) -> None:
        verification = self.load("data/verification.json")
        claims = verification["claimAudit"]
        self.assertEqual(len(claims), 160)
        self.assertEqual(sum(item["firstSupported"] for item in claims), 101)
        self.assertEqual(sum(item["finalSupported"] for item in claims), 157)
        self.assertEqual(verification["method"]["firstPass"]["accuracy"], 63.1)
        self.assertEqual(verification["method"]["finalPass"]["accuracy"], 98.1)

    def test_document_review_drives_final_support(self) -> None:
        review = self.load("artifacts/document-review.json")
        verification = self.load("data/verification.json")
        unsupported = {
            (row["appId"], field)
            for row in review["reviews"]
            for field in row["unsupportedFields"]
        }
        ledger_unsupported = {
            (claim["appId"], claim["field"])
            for claim in verification["claimAudit"]
            if not claim["finalSupported"]
        }
        self.assertEqual(review["summary"]["reviewedApps"], 20)
        self.assertEqual(review["summary"]["reviewedClaims"], 160)
        self.assertEqual(unsupported, ledger_unsupported)

    def test_human_gate_count_uses_set_union(self) -> None:
        patterns = self.load("data/patterns.json")
        self.assertEqual(patterns["humanGate"], {"formalReview": 11, "outreachFirst": 8, "overlap": 4, "uniqueApps": 15})


if __name__ == "__main__":
    unittest.main()
