from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.research import (  # noqa: E402
    AppIdentity,
    build_query,
    citation_is_technical_evidence,
    citation_matches_identity,
    parse_cli_output,
    score_citation,
)


class IdentityGuardTests(unittest.TestCase):
    def test_rejects_close_name_collision(self) -> None:
        identity = AppIdentity(8, "Close", "CRM & Sales", ("close.com",))
        wrong = {"title": "Close payments", "url": "https://stripe.com/docs/payments"}
        right = {"title": "Authentication", "url": "https://developer.close.com/topics/authentication/"}
        self.assertFalse(citation_matches_identity(wrong, identity))
        self.assertTrue(citation_matches_identity(right, identity))
        self.assertGreater(score_citation(right, identity), score_citation(wrong, identity))

    def test_shared_github_host_requires_project_path(self) -> None:
        identity = AppIdentity(98, "Mermaid CLI", "AI", ("github.com",), ("mermaid-js/mermaid-cli",))
        chart = {"url": "https://github.com/Mermaid-Chart/mermaid-live-editor"}
        cli = {"url": "https://github.com/mermaid-js/mermaid-cli"}
        self.assertFalse(citation_matches_identity(chart, identity))
        self.assertTrue(citation_matches_identity(cli, identity))

    def test_query_contains_entity_lock_and_unknown_rule(self) -> None:
        identity = AppIdentity(99, "YouTube Transcript", "AI", ("transcriptapi.com",))
        query = build_query(identity)
        self.assertIn('exact product "YouTube Transcript"', query)
        self.assertIn("transcriptapi.com", query)
        self.assertIn("unknown", query)

    def test_official_blog_is_not_technical_evidence(self) -> None:
        identity = AppIdentity(17, "Plain", "Support", ("plain.com",))
        blog = {"title": "What is API-first support?", "url": "https://www.plain.com/blog/api-first"}
        docs = {"title": "GraphQL API", "url": "https://www.plain.com/docs/graphql/introduction"}
        self.assertTrue(citation_matches_identity(blog, identity))
        self.assertFalse(citation_is_technical_evidence(blog, identity))
        self.assertTrue(citation_is_technical_evidence(docs, identity))


class CliParsingTests(unittest.TestCase):
    def test_parses_nested_composio_envelope(self) -> None:
        stdout = json.dumps({"successful": True, "data": {"answer": "Documented answer", "citations": [{"url": "https://example.com/docs"}]}})
        answer, citations = parse_cli_output(stdout)
        self.assertEqual(answer, "Documented answer")
        self.assertEqual(citations[0]["url"], "https://example.com/docs")

    def test_rejects_non_json(self) -> None:
        with self.assertRaises(ValueError):
            parse_cli_output("not json")


if __name__ == "__main__":
    unittest.main()
