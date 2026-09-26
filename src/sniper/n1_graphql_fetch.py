"""n1_graphql_fetch — Retrieve open Q&A discussions without accepted answers via GitHub GraphQL API."""

from __future__ import annotations

import subprocess
import json
from dataclasses import dataclass

from .n0_target_ingest import TargetRepo


DISCUSSIONS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    discussions(
      first: 50
      after: $cursor
      categoryId: null
      states: [OPEN]
      orderBy: {field: CREATED_AT, direction: DESC}
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        url
        createdAt
        author {
          login
        }
        category {
          name
        }
        answer {
          id
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
}
"""


@dataclass(frozen=True)
class Discussion:
    id: str
    number: int
    title: str
    body: str
    url: str
    created_at: str
    author: str
    category: str
    labels: list[str]
    repo_owner: str
    repo_name: str

    @property
    def repo_full_name(self) -> str:
        return f"{self.repo_owner}/{self.repo_name}"


def _run_graphql(query: str, variables: dict) -> dict:
    """Execute a GraphQL query via gh api graphql."""
    payload = json.dumps({"query": query, "variables": variables})
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"]
        + [item for k, v in variables.items() for item in ["-f", f"{k}={v}"]],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def fetch_unanswered_discussions(
    repo: TargetRepo, max_pages: int = 3
) -> list[Discussion]:
    """Fetch open discussions without accepted answers for a target repo."""
    discussions: list[Discussion] = []
    cursor: str | None = None

    for _ in range(max_pages):
        variables: dict[str, str] = {
            "owner": repo.owner,
            "name": repo.name,
        }
        if cursor:
            variables["cursor"] = cursor

        data = _run_graphql(DISCUSSIONS_QUERY, variables)
        repo_data = data.get("data", {}).get("repository", {})
        disc_data = repo_data.get("discussions", {})

        for node in disc_data.get("nodes", []):
            # Skip discussions that already have an accepted answer
            if node.get("answer") is not None:
                continue

            # Filter to Q&A category
            category_name = node.get("category", {}).get("name", "")
            if category_name not in repo.categories:
                continue

            discussions.append(
                Discussion(
                    id=node["id"],
                    number=node["number"],
                    title=node["title"],
                    body=node.get("body", "")[:2000],  # Truncate long bodies
                    url=node["url"],
                    created_at=node["createdAt"],
                    author=node.get("author", {}).get("login", "unknown"),
                    category=category_name,
                    labels=[lb["name"] for lb in node.get("labels", {}).get("nodes", [])],
                    repo_owner=repo.owner,
                    repo_name=repo.name,
                )
            )

        page_info = disc_data.get("pageInfo", {})
        if not page_info.get("hasNextPage", False):
            break
        cursor = page_info.get("endCursor")

    return discussions
