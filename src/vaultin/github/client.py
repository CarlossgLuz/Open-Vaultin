from __future__ import annotations

import os

import httpx

from vaultin.vaults.registry import RemoteRepository


class GitHubClient:
    def __init__(
        self,
        *,
        owner: str,
        token: str | None = None,
        api_url: str = "https://api.github.com",
        client: httpx.Client | None = None,
    ) -> None:
        self.owner = owner
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.api_url = api_url.rstrip("/")
        self._client = client

    def _headers(self) -> dict[str, str]:
        if not self.token:
            raise RuntimeError("GitHub token is not available")
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def create_private_repository(self, name: str) -> RemoteRepository:
        client = self._client or httpx.Client(timeout=20)
        owns_client = self._client is None
        try:
            response = client.post(
                f"{self.api_url}/user/repos",
                headers=self._headers(),
                json={"name": name, "private": True, "auto_init": False},
            )
            if response.status_code == 422:
                response = client.get(
                    f"{self.api_url}/repos/{self.owner}/{name}",
                    headers=self._headers(),
                )
            response.raise_for_status()
            payload = response.json()
            full_name = str(payload.get("full_name", ""))
            private = bool(payload.get("private", False))
            if full_name != f"{self.owner}/{name}":
                raise RuntimeError(f"unexpected GitHub repository: {full_name}")
            if not private:
                raise RuntimeError(f"repository is not private: {full_name}")
            return RemoteRepository(full_name=full_name, private=private)
        finally:
            if owns_client:
                client.close()
