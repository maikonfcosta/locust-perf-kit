"""Anonymous Reader scenario: reads tags, browses articles feed, reads single article."""

from locust import TaskSet, task


class ReaderTasks(TaskSet):
    @task(3)
    def get_tags(self) -> None:
        self.client.get("/api/tags", name="[GET] /api/tags")

    @task(5)
    def get_articles_feed(self) -> None:
        self.client.get("/api/articles?limit=10&offset=0", name="[GET] /api/articles")

    @task(2)
    def get_single_article(self) -> None:
        self.client.get("/api/articles/perf-test-slug-1", name="[GET] /api/articles/{slug}")
