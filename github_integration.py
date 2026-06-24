"""
GitHub integration for Asford Materials game.
Commits year-end narratives to a dedicated branch for history tracking.
Keeps DeepSeek token-efficient by storing narrative history in GitHub instead of passing it to the API.
"""
import os
import json
from typing import Optional
from datetime import datetime
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO", "amundsenmilo-collab/simulationgame")
GITHUB_BRANCH = "game-state"  # Dedicated branch for game state
GITHUB_API = "https://api.github.com"


class GitHubGameState:
    """Manages game state commits to GitHub."""

    def __init__(self):
        self.token = GITHUB_TOKEN
        self.repo = GITHUB_REPO
        self.branch = GITHUB_BRANCH
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _ensure_branch_exists(self) -> bool:
        """Ensure the game-state branch exists."""
        if not self.token:
            print("[GITHUB] No token configured")
            return False

        try:
            # Check if branch exists
            url = f"{GITHUB_API}/repos/{self.repo}/branches/{self.branch}"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                return True

            # Create branch from main
            url = f"{GITHUB_API}/repos/{self.repo}/git/refs/heads/main"
            resp = requests.get(url, headers=self.headers)
            if resp.status_code != 200:
                print("[GITHUB] Could not get main branch")
                return False

            main_sha = resp.json()["object"]["sha"]

            # Create new branch
            url = f"{GITHUB_API}/repos/{self.repo}/git/refs"
            payload = {
                "ref": f"refs/heads/{self.branch}",
                "sha": main_sha,
            }
            resp = requests.post(url, headers=self.headers, json=payload)
            if resp.status_code == 201:
                print(f"[GITHUB] Created branch {self.branch}")
                return True
            else:
                print(f"[GITHUB] Failed to create branch: {resp.status_code}")
                return False

        except Exception as e:
            print(f"[GITHUB] Branch check error: {e}")
            return False

    def commit_year(self, year: int, narrative: str, financials: dict) -> bool:
        """
        Commit a year's narrative and financials to GitHub.
        Creates a file: years/year_YYYY.json
        """
        if not self.token:
            print("[GITHUB] No token configured")
            return False

        try:
            # Ensure branch exists
            if not self._ensure_branch_exists():
                return False

            # Prepare file content
            file_content = {
                "year": year,
                "narrative": narrative,
                "financials": financials,
                "committed_at": datetime.now().isoformat(),
            }
            file_json = json.dumps(file_content, indent=2)

            # Get current file (if exists) to get its SHA
            file_path = f"years/year_{year:04d}.json"
            url = f"{GITHUB_API}/repos/{self.repo}/contents/{file_path}"
            resp = requests.get(url, headers=self.headers, params={"ref": self.branch})

            sha = None
            if resp.status_code == 200:
                sha = resp.json()["sha"]

            # Commit file
            import base64
            encoded_content = base64.b64encode(file_json.encode()).decode()

            payload = {
                "message": f"Year {year}: {narrative[:50]}...",
                "content": encoded_content,
                "branch": self.branch,
            }
            if sha:
                payload["sha"] = sha

            resp = requests.put(url, headers=self.headers, json=payload)
            if resp.status_code in [200, 201]:
                print(f"[GITHUB] Committed year {year}")
                return True
            else:
                print(f"[GITHUB] Commit failed: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            print(f"[GITHUB] Commit error: {e}")
            return False

    def get_year_narrative(self, year: int) -> Optional[str]:
        """
        Retrieve a year's narrative from GitHub.
        Falls back to database if GitHub is unavailable.
        """
        if not self.token:
            return None

        try:
            file_path = f"years/year_{year:04d}.json"
            url = f"{GITHUB_API}/repos/{self.repo}/contents/{file_path}"
            resp = requests.get(url, headers=self.headers, params={"ref": self.branch})

            if resp.status_code == 200:
                import base64
                content = base64.b64decode(resp.json()["content"]).decode()
                data = json.loads(content)
                return data.get("narrative")
            else:
                return None

        except Exception as e:
            print(f"[GITHUB] Get narrative error: {e}")
            return None

