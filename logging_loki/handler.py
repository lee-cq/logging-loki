import json
import os
import queue
import time
import gzip
from sys import version as py_version
from warnings import warn
from logging import Formatter, Handler
from concurrent.futures import ThreadPoolExecutor

from httpx import Client
import httpx

from logging_loki.version import __version__
from logging_loki.formater import LokiFormatter

DEFUALT_UA = f"logging-loki/{__version__} Python {py_version}"


def debuger_print(*args, **kwargs):
    if os.getenv("LOKI_LOGGING_DEBUG"):
        print(*args, **kwargs)


class LokiHandler(Handler):
    """Loki日志发送"""

    def __init__(
        self,
        loki_url: str,
        username: str = None,
        password: str = None,
        level: int | str = "ERROR",
        gziped: bool = True,
        flush_interval: int = 2,
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
        self.gziped = gziped
        self.flush_interval = flush_interval

        self.buffer = queue.SimpleQueue()
        self.last_flush_time: float = 0
        self.t_pool = ThreadPoolExecutor(5, thread_name_prefix="loki-handler-")
        self.setFormatter(
            LokiFormatter(fmt=fmt, tags=tags, included_field=included_field, fqdn=fqdn)
        )
        self.total_losed_logs = 0
        self.headers = {"Content-Type": "application/json"}
        if self.gziped:
            self.headers.update({"Content-Encoding": "gzip"})

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
        return time.time() - self.last_flush_time > self.flush_interval

    def emit(self, record) -> None:
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
        data = json.dumps({"streams": streams}).encode()
        len_data = len_gz_data = len(data)
        if self.gziped:
            data = gzip.compress(data)
            len_gz_data = len(data)
        gz_info = (
            lambda: f"(gziped size {len_gz_data} , zip rite {(len_data - len_gz_data) / len_data * 100: .2f}%)"
        )

        while retry_times < 3:
            try:
                debuger_print(
                    f"[{time.strftime('%Y-%m-%d %H:%M:%S.')}]LOKI LOGGING flush logs {len(streams)}, "
                    f"data size {len_data} {gz_info() if self.gziped else 'not gziped'}, retry {retry_times}"
                )
                time.sleep(retry_times)

                res = self.client.post(
                    "/loki/api/v1/push",
                    data=data,
                    headers=self.headers,
                )
                debuger_print(f"HTTP STATUS: {res.status_code} - {res.text}")
                if res.is_success:
                    return
                if 400 <= res.status_code <= 499:
                    retry_times = 100
                    continue

            except httpx.HTTPError as _e:
                debuger_print(f"HTTPError {_e}")
            finally:
                retry_times += 1
        else:
            self.total_losed_logs += len(streams)
            raise RuntimeError(
                f"多次推送失败, 舍弃日志数量: {len(streams)} / total: {self.total_losed_logs}"
            )
