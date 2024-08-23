import os
import time
import unittest
from pathlib import Path

from logging_loki.loki_client import LokiClient

TEST_DIR = Path(__file__).parent
PROJECT_DIR = TEST_DIR.parent


def load_env():
    def _load(ss: list):
        for s in ss:
            s = s.strip(" ").strip("\t")
            if s.startswith("#") or s == "":
                continue
            k, v = s.split("=", 1)
            os.environ[k] = v
            print("load ENV: ", s)

    if PROJECT_DIR.joinpath(".env").exists():
        _load(PROJECT_DIR.joinpath(".env").read_text().split("\n"))
    if TEST_DIR.joinpath(".env").exists():
        _load(TEST_DIR.joinpath(".env").read_text().split("\n"))
    os.environ["LOKI_LOGGING_DEBUG"] = "TRUE"


class TestLokiClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        load_env()

    def setUp(self) -> None:
        self.lc = LokiClient(
            loki_url=os.getenv("LOKI_URL"),
            username=os.getenv("LOKI_USERNAME"),
            password=os.getenv("LOKI_PASSWORD"),
        )

    def test_push_once(self):
        self.lc.push_once(
            dict(app="test_loki_client", type="push_once"),
            [
                [time.time_ns(), "test push once - 1"],
                [time.time_ns(), "test push once - 2", {"a": "p"}],
            ],
        )

    def test_push_many(self):
        self.lc.push_many(
            [
                [
                    dict(app="test_loki_client", type="push_once"),
                    [
                        [time.time_ns(), "test push once - 1"],
                    ],
                ],
                [
                    dict(app="test_loki_client", type="push_once"),
                    [
                        [time.time_ns(), "test push once - 2", {"a": "p"}],
                    ],
                ],
            ]
        )

    def test_push_wait(self):
        self.lc.push_wait(
            dict(app="test_loki_client", type="push_wait"),
            [[time.time_ns(), "test push once - 1"]],
        )
        self.lc.push_wait(
            dict(app="test_loki_client", type="push_wait"),
            [[time.time_ns(), "test push once - 2", {"a": "p"}]],
        )
