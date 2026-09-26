"""n2_relevance_score — Rank discussions against the expertise matrix."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .n0_target_ingest import ExpertiseDomain
from .n1_graphql_fetch import Discussion


@dataclass(frozen=True)
class ScoredDiscussion:
    discussion: Discussion
    score: float
    matched_domains: list[str]
    matched_keywords: list[str]


def _normalize(text: str) -> str:
    """Lowercase and collapse whitespace for matching."""
    return re.sub(r"\s+", " ", text.lower())


def score_discussion(
    discussion: Discussion,
    expertise: list[ExpertiseDomain],
) -> ScoredDiscussion:
    """Score a single discussion against the expertise matrix.

    Scoring: for each domain, check how many keywords appear in the
    discussion title + body. Score contribution per domain =
    (matched_keyword_count / total_keywords) * domain_weight.
    Final score is the sum across all domains.
    """
    text = _normalize(f"{discussion.title} {discussion.body}")
    total_score = 0.0
    matched_domains: list[str] = []
    matched_keywords: list[str] = []

    for domain in expertise:
        domain_matches: list[str] = []
        for keyword in domain.keywords:
            if _normalize(keyword) in text:
                domain_matches.append(keyword)

        if domain_matches:
            coverage = len(domain_matches) / len(domain.keywords)
            total_score += coverage * domain.weight
            matched_domains.append(domain.domain)
            matched_keywords.extend(domain_matches)

    return ScoredDiscussion(
        discussion=discussion,
        score=round(total_score, 2),
        matched_domains=matched_domains,
        matched_keywords=list(set(matched_keywords)),
    )


def rank_discussions(
    discussions: list[Discussion],
    expertise: list[ExpertiseDomain],
    min_score: float = 0.5,
) -> list[ScoredDiscussion]:
    """Score and rank all discussions. Filter below min_score."""
    scored = [score_discussion(d, expertise) for d in discussions]
    filtered = [s for s in scored if s.score >= min_score]
    return sorted(filtered, key=lambda s: s.score, reverse=True)
