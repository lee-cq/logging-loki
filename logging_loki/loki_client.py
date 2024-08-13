"""
Loki Client for Python

负责处理Loki上传相关事宜
"""

import os
import base64
import threading
import time
import typing
import socket
from sys import version as py_version
from urllib.parse import urlparse
from http.client import HTTPConnection, HTTPSConnection
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import snappy

from logging_loki import loki_push_pb2
from logging_loki.tools import debugger_print, beautify_size
from logging_loki.version import __version__


DEFAULT_UA = f"logging-loki/{__version__} Python {py_version}"


def all_thread_ids() -> set:
    return {t.ident for t in threading.enumerate()}


class NeedRetryError(Exception):
    """"""


class LokiClient(ThreadPoolExecutor):
    """向Loki Push 数据 使用 /loki/api/v1/push

    3中运行模式：
        1. 立即push一条数据  -- push_once
        2. 立即push多条数据  -- push_many
        3. 收到一条数据，并在合适的适合push服务器 -- push_wait
    """

    def __init__(
        self,
        loki_url: str,
        username: str = None,
        password: str = None,
        flush_interval: int = 2,  # 将缓存刷写到Loki的时间频率， 默认2秒
        max_cache_size: int = 102400,  # 缓存中的条目允许的内存占用的最大值
        max_cache_stream: int = 1000,  # 最多缓存的条目
        thread_pool_size: int = 3,  # 刷写线程池大小，如果为0，将使用同步上传
        ssl_verify: bool = True,
        ua: str = DEFAULT_UA,
        tags: dict = None,  # 使用的TAG
        **kwargs,
    ):
        super().__init__(
            max(thread_pool_size, 1),
            thread_name_prefix="loki-push",
        )
        self.loki_url = urlparse(loki_url)
        self.headers = {
            "User-Agent": ua,
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
        }
        if username:
            self.set_auth(username, password)

        self.__closed = False
        self.p_lock = threading.Lock()
        self.push_request = loki_push_pb2.PushRequest()
        self.connections = defaultdict(
            lambda: (
                HTTPSConnection
                if self.loki_url.scheme.upper() == "HTTPS"
                else HTTPConnection
            )(self.loki_url.netloc)
        )

        self.last_flush = 0
        self.max_cache_size = max_cache_size
        self.max_cache_stream = max_cache_stream
        self.flush_interval = flush_interval
        self.pool_size = thread_pool_size
        self.ssl_verify = ssl_verify
        self.labels = tags or {}

    def close(self):
        self.__closed = True
        with self.p_lock:
            self.flush()
            self.shutdown(wait=True)

    def __exit__(self):
        self.close()

    def set_auth(self, username: str, password: str = ""):
        b64 = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.headers["Authorization"] = f"Basic {b64}"

    @staticmethod
    def label_to_string(labels: dict):
        items = [f'{k}="{v}"' for k, v in labels.items()]
        return f"{{ {', '.join(items)} }}"

    def push_many(self, streams: list[dict, list[list]]):
        [self.push_wait(d, l) for d, l in streams]
        self.flush()

    def push_once(self, labels, lines):
        self.push_wait(labels, lines)
        self.flush()

    def push_wait(
        self,
        labels: dict,
        lines: list[list[loki_push_pb2.Timestamp, str, typing.Optional[dict]]],
    ):
        """"""
        if self.__closed:
            raise RuntimeError()

        stream = loki_push_pb2.StreamAdapter(labels=self.label_to_string(labels))

        for line in lines:
            debugger_print("> Push Line:", line)
            stream.entries.append(
                loki_push_pb2.EntryAdapter(
                    timestamp=loki_push_pb2.Timestamp(
                        seconds=line[0] // 1_000_000_000,
                        nanos=line[0] % 1_000_000_000,
                    ),
                    line=line[1],
                    structuredMetadata=(
                        line[2] if len(line) >= 3 and line[2] is not None else dict()
                    ),
                )
            )

        with self.p_lock:
            self.push_request.streams.append(stream)
        if self.shoud_flush():
            self.last_flush = time.time()
            self.flush()

    def shoud_flush(self) -> bool:
        """判定需要刷写的条件"""
        return (
            self.push_request.ByteSize() > self.max_cache_size
            or len(self.push_request.streams) > self.max_cache_stream
            or time.time() - self.last_flush > self.flush_interval
        )

    def flush(self):
        """提交"""
        with self.p_lock:
            _push_size = self.push_request.ByteSize()
            if _push_size == 0:
                return
            debugger_print("> Push Data: ", self.push_request.SerializeToString())
            count_request = len(self.push_request.streams)
            push_req_data: bytes = snappy.compress(
                self.push_request.SerializeToString()
            )
            self.push_request.Clear()

        if os.getenv("LOKI_LOGGING_DEBUG", "").upper() == "TRUE":
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S.')}]LOKI LOGGING flush logs {count_request}, "
                f"data size {beautify_size(len(push_req_data))}"
            )

        self.api_push(push_req_data, headers=self.headers)

    def _request(
        self,
        method,
        url,
        body: str | bytes = None,
        headers: dict = None,
        *,
        encode_chunked=False,
        retry=3,
    ):
        """
        连接错误 - 关闭并重建错误，丢弃现有连接，将新连接放入池，递归
        500错误  - 1s后重试，1s后递归
        400错误  - 警告，并存储当前body到文件

        body: json 或 protobuf
        """
        headers = {} if headers is None else headers
        [headers.setdefault(k, v) for k, v in self.headers.items()]

        if retry == 0:
            debugger_print("多次重试后依旧错误")
            # TODO 保存Body
            return
        try:
            conn = self.connections[threading.get_ident()]
            debugger_print("> URI:", url)
            debugger_print("> HEADER: ", headers)
            debugger_print("> BODY: ", body)
            conn.request(method, url, body, headers, encode_chunked=encode_chunked)
            resp = conn.getresponse()
            if 200 <= resp.status <= 299:
                debugger_print(f"[]Push Success.")
                return
            elif 300 <= resp.status <= 399:
                debugger_print("请求已经重定向...")

            elif 400 <= resp.status <= 499:
                debugger_print(f"请求错误: {resp.status}: {resp.read().decode()}")

            elif 500 <= resp.status <= 599:
                debugger_print("服务器错误， 1s后重试")
                raise NeedRetryError()
            else:
                debugger_print(f"未知状态码: {resp.status}: {resp.read()}")

            # print(resp.status, resp.read().decode())
        except NeedRetryError:
            time.sleep(1)
            self._request(
                method,
                url,
                body,
                headers,
                encode_chunked=encode_chunked,
                retry=retry - 1,
            )
        except (socket.gaierror, ConnectionRefusedError):
            del self.connections[threading.get_ident()]
            self._request(
                method,
                url,
                body,
                headers,
                encode_chunked=encode_chunked,
                retry=retry - 1,
            )

        except Exception as _e:
            print("ClassName:", _e.__class__(), "Message:", _e)

        finally:
            # Clear 关闭的线程的连接
            for _i in self.connections.keys() - all_thread_ids():
                del self.connections[_i]

    def request(
        self,
        method: str,
        url: str,
        body: str | bytes = None,
        headers: dict = None,
        *,
        encode_chunked=False,
    ):
        """在线程池中提交请求"""
        if self.pool_size > 0 and not self._shutdown:
            self.submit(
                self._request,
                method,
                url,
                body=body,
                headers=headers,
                encode_chunked=encode_chunked,
            )
        else:
            self._request(method, url, body, headers, encode_chunked=encode_chunked)

    def api_push(self, body, headers: dict = None, encode_chunked=False):
        return self.request(
            "POST",
            "/loki/api/v1/push",
            body,
            headers,
            encode_chunked=encode_chunked,
        )


if __name__ == "__main__":
    import os
    import time

    lc = LokiClient(
        loki_url=os.getenv("LOKI_URL"),
        username=os.getenv("LOKI_USERNAME"),
        password=os.getenv("LOKI_PASSWORD"),
    )

    lc.push_once(
        dict(app="test_loki_client"),
        [
            [time.time_ns(), "test push once - 1"],
            [time.time_ns(), "test push once - 2", {"a": "p"}],
        ],
    )
