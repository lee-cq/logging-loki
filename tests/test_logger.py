import logging
import os

from logging_loki.handler import LokiHandler
from logging_loki.formater import DEFAULT_FIELD_MAX

logger = logging.getLogger("aa")

handler = LokiHandler(
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    level="DEBUG",
    thread_pool_size=0,
    tags={"service_name": "test_loki_handler"},
    included_field=DEFAULT_FIELD_MAX,
    gzipped=False,
    verify=False,
)
handler_gz = LokiHandler(
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    level="DEBUG",
    thread_pool_size=0,
    tags={"service_name": "test_loki_handler"},
    included_field=DEFAULT_FIELD_MAX,
    gzipped=True,
    verify=False,
)
ch = logging.StreamHandler()
ch.setLevel("DEBUG")

logger.addHandler(handler)
logger.addHandler(handler_gz)
# logger.addHandler(ch)
logger.setLevel("DEBUG")


print("level", handler.level)
logger.info("test ok.")
logger.info("test debug...")
