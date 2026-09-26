"""n0_target_ingest — Load target repos and expertise matrix from YAML config."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TargetRepo:
    owner: str
    name: str
    categories: list[str] = field(default_factory=lambda: ["Q&A"])

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class ExpertiseDomain:
    domain: str
    weight: int
    keywords: list[str]


@dataclass(frozen=True)
class PipelineConfig:
    target_repos: list[TargetRepo]
    expertise_matrix: list[ExpertiseDomain]


def load_config(config_path: Path | None = None) -> PipelineConfig:
    """Load pipeline configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "data" / "config.yaml"

    with open(config_path) as f:
        raw = yaml.safe_load(f)

    repos = [
        TargetRepo(
            owner=r["owner"],
            name=r["name"],
            categories=r.get("categories", ["Q&A"]),
        )
        for r in raw["target_repos"]
    ]

    domains = [
        ExpertiseDomain(
            domain=d["domain"],
            weight=d["weight"],
            keywords=d["keywords"],
        )
        for d in raw["expertise_matrix"]
    ]

    return PipelineConfig(target_repos=repos, expertise_matrix=domains)
