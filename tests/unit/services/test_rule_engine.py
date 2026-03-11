"""URL Rule Engine 단위 테스트 (TC-R01~R05)."""

import pytest

from app.models.topic import TopicRule
from app.services.rule_engine import RuleSet, classify_url


def make_rule(rule_type: str, pattern: str, rule_id: str = "r1", priority: int = 0) -> TopicRule:
    return TopicRule(
        rule_id=rule_id,
        topic_id="t001",
        rule_type=rule_type,
        pattern=pattern,
        is_regex=True,
        enabled=True,
        priority=priority,
    )


class TestClassifyUrl:
    def test_blocked_url(self):
        """TC-R01: blocked_url 룰에 매칭되는 URL은 'blocked' 반환."""
        rules = [make_rule("blocked_url", r".*pinterest.*")]
        rule_set = RuleSet(rules)
        classification, matched = classify_url("https://www.pinterest.com/some/page", rule_set)
        assert classification == "blocked"
        assert matched == r".*pinterest.*"

    def test_preferred_domain(self):
        """TC-R02: preferred_domain 룰에 매칭되는 URL은 'preferred' 반환."""
        rules = [make_rule("preferred_domain", r"github\.com")]
        rule_set = RuleSet(rules)
        classification, _ = classify_url("https://github.com/owner/repo", rule_set)
        assert classification == "preferred"

    def test_blocked_takes_priority_over_preferred(self):
        """TC-R03: blocked_domain이 preferred_domain보다 우선 (차단 우선 원칙, FR-D02)."""
        rules = [
            make_rule("blocked_domain", r"github\.com", "r1"),
            make_rule("preferred_domain", r"github\.com", "r2"),
        ]
        rule_set = RuleSet(rules)
        classification, _ = classify_url("https://github.com/test", rule_set)
        assert classification == "blocked"

    def test_neutral_url(self):
        """TC-R04: 어떤 룰도 매칭 안 되면 'neutral' 반환."""
        rules = [make_rule("preferred_domain", r"github\.com")]
        rule_set = RuleSet(rules)
        classification, matched = classify_url("https://example.com/article", rule_set)
        assert classification == "neutral"
        assert matched is None

    def test_empty_ruleset(self):
        """룰이 없으면 항상 neutral."""
        rule_set = RuleSet([])
        classification, _ = classify_url("https://any.site.com/path", rule_set)
        assert classification == "neutral"

    def test_disabled_rule_ignored(self):
        """비활성 룰은 무시됨."""
        rule = make_rule("blocked_domain", r"example\.com")
        rule.enabled = False
        rule_set = RuleSet([rule])
        classification, _ = classify_url("https://example.com/page", rule_set)
        assert classification == "neutral"

    def test_invalid_regex_ignored(self):
        """잘못된 regex 패턴은 무시됨 (오류 없이)."""
        rule = make_rule("blocked_domain", r"[invalid")
        rule_set = RuleSet([rule])  # 오류 없이 처리
        classification, _ = classify_url("https://example.com", rule_set)
        assert classification == "neutral"
