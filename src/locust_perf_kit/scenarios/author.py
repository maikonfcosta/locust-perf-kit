"""Authenticated Author scenario: logs in, creates article, favorites, comments."""

import uuid

from locust import TaskSet, task


class AuthorTasks(TaskSet):
    token: str = ""

    def on_start(self) -> None:
        """Authenticate user on spawn."""
        res = self.client.post(
            "/api/users/login",
            json={"user": {"email": "tester@example.com", "password": "password123"}},
            name="[POST] /api/users/login",
        )
        if res.status_code == 200:
            self.token = res.json().get("user", {}).get("token", "")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Token {self.token}"
        return headers

    @task(3)
    def create_article(self) -> None:
        unique_id = uuid.uuid4().hex[:8]
        payload = {
            "article": {
                "title": f"Load Test Article {unique_id}",
                "description": "Automated performance load testing",
                "body": "Article content generated during Locust perf test.",
                "tagList": ["performance", "locust"],
            }
        }
        self.client.post(
            "/api/articles",
            json=payload,
            headers=self._headers(),
            name="[POST] /api/articles",
        )

    @task(2)
    def favorite_article(self) -> None:
        self.client.post(
            "/api/articles/perf-test-slug-1/favorite",
            headers=self._headers(),
            name="[POST] /api/articles/{slug}/favorite",
        )

    @task(1)
    def comment_article(self) -> None:
        payload = {"comment": {"body": "Automated Locust comment under load."}}
        self.client.post(
            "/api/articles/perf-test-slug-1/comments",
            json=payload,
            headers=self._headers(),
            name="[POST] /api/articles/{slug}/comments",
        )
