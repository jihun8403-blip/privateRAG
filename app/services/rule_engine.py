"""URL Rule Engine — regex 기반 URL 분류기."""

import re
from typing import Literal
from urllib.parse import urlparse

from app.core.logging import get_logger
from app.models.topic import TopicRule

logger = get_logger(__name__)

UrlClassification = Literal["blocked", "preferred", "neutral"]


class RuleSet:
    """컴파일된 URL 분류 규칙 세트."""

    def __init__(self, rules: list[TopicRule]):
        self.blocked_url: list[tuple[re.Pattern, TopicRule]] = []
        self.blocked_domain: list[tuple[re.Pattern, TopicRule]] = []
        self.preferred_url: list[tuple[re.Pattern, TopicRule]] = []
        self.preferred_domain: list[tuple[re.Pattern, TopicRule]] = []

        for rule in sorted(rules, key=lambda r: r.priority):
            if not rule.enabled:
                continue
            try:
                pattern = re.compile(rule.pattern, re.IGNORECASE)
            except re.error as e:
                logger.warning("잘못된 regex 패턴 무시", pattern=rule.pattern, error=str(e))
                continue

            if rule.rule_type == "blocked_url":
                self.blocked_url.append((pattern, rule))
            elif rule.rule_type == "blocked_domain":
                self.blocked_domain.append((pattern, rule))
            elif rule.rule_type == "preferred_url":
                self.preferred_url.append((pattern, rule))
            elif rule.rule_type == "preferred_domain":
                self.preferred_domain.append((pattern, rule))


def classify_url(url: str, rule_set: RuleSet) -> tuple[UrlClassification, str | None]:
    """URL을 규칙에 따라 분류합니다.

    적용 순서: blocked_url > blocked_domain > preferred_url > preferred_domain
    (FR-D02 차단 우선 원칙)

    Returns:
        (분류 결과, 매칭된 패턴 문자열 또는 None)
    """
    try:
        domain = urlparse(url).netloc
    except Exception:
        domain = ""

    # 1. blocked_url
    for pattern, rule in rule_set.blocked_url:
        if pattern.search(url):
            return "blocked", rule.pattern

    # 2. blocked_domain
    for pattern, rule in rule_set.blocked_domain:
        if pattern.search(domain):
            return "blocked", rule.pattern

    # 3. preferred_url
    for pattern, rule in rule_set.preferred_url:
        if pattern.search(url):
            return "preferred", rule.pattern

    # 4. preferred_domain
    for pattern, rule in rule_set.preferred_domain:
        if pattern.search(domain):
            return "preferred", rule.pattern

    return "neutral", None
