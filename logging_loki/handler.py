import io
import json
import os
import queue
import time
import gzip
from sys import version as py_version
from warnings import warn
from logging import Formatter, Handler, LogRecord
from concurrent.futures import ThreadPoolExecutor

from httpx import Client
import httpx

from logging_loki.version import __version__
from logging_loki.formater import LokiFormatter

DEFUALT_UA = f"logging-loki/{__version__} Python {py_version}"


class LokiHandler(Handler):
    """Loki日志发送"""

    def __init__(
        self,
        loki_url: str = None,
        username: str = None,
        password: str = None,
        level: int | str = 0,
        tags: dict = None,
        included_field: tuple | list | set = None,
        fmt: str = None,
        fqdn: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(level)

        self._client = None
        self.client_info = dict(
            base_url=loki_url,
            auth=(username, password) if username else None,
            **kwargs,
        )

        self.loki_tags = tags or {}

        self.buffer = queue.SimpleQueue()
        self.last_flush_time: float = 0
        self.t_pool = ThreadPoolExecutor(5, thread_name_prefix="loki-handler-")
        self.setFormatter(
            LokiFormatter(fmt=fmt, tags=tags, included_field=included_field, fqdn=fqdn)
        )
        self.total_losed_logs = 0

    def setFormatter(self, fmt: Formatter | None) -> None:
        if not isinstance(fmt, LokiFormatter):
            raise TypeError(f"fmt 必须是 LokiFormartter 或其子类 [{type(fmt)}]")

        return super().setFormatter(fmt)

    @property
    def client(self):
        self._client: Client
        if self._client and self._client.is_closed is False:
            return self._client

        self._client = Client(**self.client_info)
        self._client.headers.setdefault("User-Agen", DEFUALT_UA)
        return self._client

    def test_client(self) -> bool:
        return self.client_info["base_url"].startswith("http")

    def should_flush(self, record):
        """检查Buffer是否满了或者日志级别达到flushLevel"""
        return time.time() - self.last_flush_time > 2

    def emit(self, record: LogRecord) -> None:
        """记录一条日志到缓存，并按需生成一个定时器，在定时器结束时将日志实际Push到Loki。

        如果在定时器开始前就已经将日志推送，则会有推送线程取消该定时器。
        """
        if self._closed:
            warn(f"[LokiHandler]{self.get_name()} 已经关闭，日志无法再被记录到Loki.")
            return  # 如果Headler已经关闭, 不再添加日志

        re_text = self.formatter.format(record=record)
        if not (
            isinstance(re_text, dict) and "stream" in re_text and "values" in re_text
        ):
            self.handleError("self.formatter.format 必须时一个Dict")
            return
        self.buffer.put_nowait(re_text)
        if self.should_flush(record):
            self.last_flush_time = time.time()
            self.flush()

    def close(self) -> None:
        super().close()
        self.acquire()
        try:
            self.flush()
            self.t_pool.shutdown(wait=True)
            if self._client:
                self._client.close()
            return
        finally:
            self.release()

    def flush(self) -> None:
        self.acquire()
        try:
            streams = [self.buffer.get_nowait() for _ in range(self.buffer.qsize())]

            if not streams:
                return
            if not self.t_pool._shutdown:
                self.t_pool.submit(self.post_logs, streams)
            else:
                self.post_logs(streams)
        finally:
            self.release()

    def post_logs(self, streams: list, retry_times=0):
        # 超时才应该重传，其他的错误都不应该重传
        gz_streams = gzip.compress(json.dumps({"streams": streams}).encode())
        while retry_times < 3:
            try:
                if os.getenv("LOKI_LOGGING_DEBUG"):
                    print(
                        f"[{time.time()}]LOKI LOGGING flush logs {len(streams)}, "
                        f"data size {len(gz_streams)}, retry {retry_times}"
                    )
                time.sleep(retry_times)
                res = self.client.post(
                    "/loki/api/v1/push",
                    data=gz_streams,
                    headers={
                        "Content-Type": "application/json",
                        "Content-Encoding": "gzip",
                    },
                )
                if res.is_success:
                    return
                print(f"Error: {res.status_code} - {res.text}")
                if 400 <= res.status_code <= 499:
                    retry_times = 100
                    continue

            except httpx.HTTPError:
                pass
            finally:
                retry_times += 1
        else:
            self.total_losed_logs += len(streams)
            raise RuntimeError(
                f"多次推送失败, 舍弃日志数量: {len(streams)} / total: {self.total_losed_logs}"
            )
