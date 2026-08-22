"""Locust scenarios for the YouTube RAG API.

Environment variables:
    LOAD_TEST_VIDEO_ID: An already initialized 11-character YouTube video ID.
    LOAD_TEST_ENABLE_CHAT: Set to true to exercise paid LLM requests.
    LOAD_TEST_API_KEY: Optional value sent through the X-API-Key header.
    LOAD_TEST_MAX_FAILURE_RATIO: Exit threshold, default 0.01.
    LOAD_TEST_MAX_P95_MS: Exit threshold in milliseconds, default 10000.
"""

import os
import random
from uuid import uuid4

from locust import HttpUser, between, events, task

VIDEO_ID = os.getenv("LOAD_TEST_VIDEO_ID", "3dhcmeOTZ_Q")
ENABLE_CHAT = os.getenv("LOAD_TEST_ENABLE_CHAT", "false").lower() == "true"
API_KEY = os.getenv("LOAD_TEST_API_KEY")
MAX_FAILURE_RATIO = float(os.getenv("LOAD_TEST_MAX_FAILURE_RATIO", "0.01"))
MAX_P95_MS = int(os.getenv("LOAD_TEST_MAX_P95_MS", "10000"))

QUERIES = (
    "What is this video about?",
    "What are the main ideas discussed?",
    "Explain one important point from the video.",
    "Summarize the video in bullet points.",
)


class YouTubeRagUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.user_id = str(uuid4())
        self.conversation_id = str(uuid4())
        self.video_ready = False
        self.headers = {"X-API-Key": API_KEY} if API_KEY else {}
        self._refresh_video_status()

    def _refresh_video_status(self) -> None:
        with self.client.get(
            f"/videos/{VIDEO_ID}/status",
            name="GET /videos/{video_id}/status",
            headers=self.headers,
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                self.video_ready = False
                return

            try:
                payload = response.json()
            except ValueError:
                response.failure("Status endpoint did not return JSON")
                self.video_ready = False
                return

            video_status = payload.get("status")
            self.video_ready = video_status == "ready"
            if video_status in {"failed", "not_found"}:
                response.failure(
                    f"Video must be initialized before chat testing: {video_status}"
                )
            else:
                response.success()

    @task(1)
    def health(self) -> None:
        with self.client.get(
            "/health",
            name="GET /health",
            catch_response=True,
        ) as response:
            if response.status_code == 200 and response.json().get("status") == "healthy":
                response.success()
            else:
                response.failure(f"Unhealthy response: {response.text[:200]}")

    @task(2)
    def video_status(self) -> None:
        self._refresh_video_status()

    @task(6)
    def chat(self) -> None:
        if not ENABLE_CHAT:
            self._refresh_video_status()
            return
        if not self.video_ready:
            self._refresh_video_status()
            return

        with self.client.post(
            "/chat",
            name="POST /chat",
            headers=self.headers,
            json={
                "video_id": VIDEO_ID,
                "query": random.choice(QUERIES),
                "user_id": self.user_id,
                "conversation_id": self.conversation_id,
            },
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"HTTP {response.status_code}: {response.text[:200]}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("Chat endpoint did not return JSON")
                return
            if payload.get("status") != "success" or not payload.get("response"):
                response.failure(f"Invalid chat response: {payload}")
            else:
                response.success()


@events.quitting.add_listener
def enforce_thresholds(environment, **_) -> None:
    total = environment.stats.total
    p95 = total.get_response_time_percentile(0.95) or 0
    if total.fail_ratio > MAX_FAILURE_RATIO or p95 > MAX_P95_MS:
        environment.process_exit_code = 1
