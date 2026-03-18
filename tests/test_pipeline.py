"""Tests for the gh-galaxy-quest pipeline."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from sniper.n0_target_ingest import load_config, TargetRepo, ExpertiseDomain, PipelineConfig
from sniper.n1_graphql_fetch import Discussion
from sniper.n2_relevance_score import score_discussion, rank_discussions, ScoredDiscussion
from sniper.n3_triage_queue import upsert_discussions, get_actionable, mark_status


# --- n0: config loading ---


def test_load_config_from_default():
    config = load_config()
    assert len(config.target_repos) > 0
    assert len(config.expertise_matrix) > 0


def test_target_repo_full_name():
    repo = TargetRepo(owner="aws", name="aws-cdk")
    assert repo.full_name == "aws/aws-cdk"


# --- n2: scoring ---


def _make_discussion(title: str, body: str = "") -> Discussion:
    return Discussion(
        id="test-1",
        number=1,
        title=title,
        body=body,
        url="https://github.com/test/test/discussions/1",
        created_at="2026-01-01T00:00:00Z",
        author="testuser",
        category="Q&A",
        labels=[],
        repo_owner="test",
        repo_name="test",
    )


SAMPLE_EXPERTISE = [
    ExpertiseDomain(
        domain="aws-security",
        weight=9,
        keywords=["IAM", "security group", "VPC", "least privilege"],
    ),
    ExpertiseDomain(
        domain="python",
        weight=7,
        keywords=["poetry", "asyncio", "pytest"],
    ),
]


def test_score_with_matches():
    d = _make_discussion("How do I set up IAM least privilege for my VPC?")
    result = score_discussion(d, SAMPLE_EXPERTISE)
    assert result.score > 0
    assert "aws-security" in result.matched_domains
    assert len(result.matched_keywords) >= 2


def test_score_no_matches():
    d = _make_discussion("How do I center a div in CSS?")
    result = score_discussion(d, SAMPLE_EXPERTISE)
    assert result.score == 0
    assert result.matched_domains == []


def test_rank_filters_low_scores():
    discussions = [
        _make_discussion("IAM least privilege VPC security group"),
        _make_discussion("How to center a div"),
    ]
    ranked = rank_discussions(discussions, SAMPLE_EXPERTISE, min_score=0.5)
    assert len(ranked) == 1
    assert ranked[0].discussion.title.startswith("IAM")


def test_rank_order_descending():
    discussions = [
        _make_discussion("poetry question"),
        _make_discussion("IAM least privilege VPC security group"),
    ]
    ranked = rank_discussions(discussions, SAMPLE_EXPERTISE, min_score=0.0)
    assert ranked[0].score >= ranked[1].score


# --- n3: triage queue ---


def test_upsert_and_retrieve():
    d = _make_discussion("IAM least privilege VPC")
    scored = score_discussion(d, SAMPLE_EXPERTISE)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        new_count = upsert_discussions([scored], db_path=db_path)
        assert new_count == 1

        items = get_actionable(db_path=db_path)
        assert len(items) == 1
        assert items[0]["title"] == d.title


def test_mark_status_filters():
    d = _make_discussion("IAM least privilege VPC")
    scored = score_discussion(d, SAMPLE_EXPERTISE)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        upsert_discussions([scored], db_path=db_path)
        mark_status(d.id, "ignored", db_path=db_path)

        items = get_actionable(db_path=db_path)
        assert len(items) == 0
