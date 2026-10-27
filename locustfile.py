"""Locust main test file defining workload scenarios and 80/20 user weights."""

from typing import ClassVar

from locust import HttpUser, between

from locust_perf_kit.scenarios.author import AuthorTasks
from locust_perf_kit.scenarios.reader import ReaderTasks


class AnonymousReaderUser(HttpUser):
    """Anonymous reader user browsing tags and articles feed (80% weight)."""

    weight = 8
    wait_time = between(0.1, 0.5)
    tasks: ClassVar = [ReaderTasks]


class AuthenticatedAuthorUser(HttpUser):
    """Authenticated author creating articles and commenting (20% weight)."""

    weight = 2
    wait_time = between(0.2, 0.8)
    tasks: ClassVar = [AuthorTasks]

