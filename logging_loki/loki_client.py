"""
Loki Client for Python

负责处理Loki上传相关事宜
"""

import abc
import gzip
import io
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from sys import version as py_version

from logging_loki.tools import debugger_print, beautify_size
from logging_loki.version import __version__

try:
    from requests import Session as Client
except ImportError:
    try:
        from httpx import Client as Client
    except ImportError:
        raise ImportError("You need to install requests or httpx to use LokiClient")

DEFAULT_UA = f"logging-loki/{__version__} Python {py_version}"


class MetaBuffer(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def write(self, data):
        raise NotImplemented

    def stop(self):
        pass

    @abc.abstractmethod
    def get_streams(self):
        raise NotImplemented

    @abc.abstractmethod
    def streams_count(self):
        raise NotImplemented

    @abc.abstractmethod
    def streams_size(self):
        raise NotImplemented


class StreamsBytesIO(io.BytesIO, MetaBuffer):

    def __init__(self):
        super().__init__()
        self.write_size = 0
        self.write_times = 0
        super().write(b'{"streams":[')

    def write(self, __buffer):
        self.write_size += super().write(__buffer)
        self.write_times += 1

    def stop(self):
        super().write(b"]}")

    def get_streams(self):
        _val = self.getvalue()
        self.close()
        return _val

    def streams_count(self):
        return self.write_times

    def streams_size(self):
        return self.write_size


class StreamsGzip(gzip.GzipFile, MetaBuffer):

    def __init__(self, compresslevel=9):
        self.buf = io.BytesIO()
        self.write_times = 0
        self.write_size = 0
        super().__init__(fileobj=self.buf, mode="wb", compresslevel=compresslevel)
        super().write(b'{"streams":[')

    def write(self, data):
        self.write_size += super().write(data)
        self.write_times += 1

    def stop(self):
        super().write(b"]}")
        self.flush()

    def get_streams(self):
        _val = self.buf.getvalue()
        self.close()
        self.buf.close()
        return _val

    def streams_size(self):
        return self.write_size

    def streams_count(self):
        return self.write_times


class LokiClient(Client):

    def __init__(
        self,
        loki_url: str,
        username: str = None,
        password: str = None,
        gzipped: bool = True,  # 上传的BODY是否进行GZIP压缩
        flush_interval: int = 2,  # 将缓存刷写到Loki的时间频率， 默认2秒
        flush_size: int = 10000,  # 将缓存中允许的最大值
        thread_pool_size: int = 3,  # 刷写线程池大小，如果为0，将使用同步上传
        verify: bool = True,
        ua: str = DEFAULT_UA,
        tags: dict = None,  # 使用的TAG
        **kwargs,
    ):
        try:
            super().__init__(verify=verify, **kwargs)
        except TypeError:
            super().__init__()

        if flush_interval < 0 or flush_size < 0 or thread_pool_size < 0:
            raise ValueError()

        self._is_closed = False
        self.loki_url = loki_url
        self.gzipped = gzipped
        self.flush_interval = flush_interval
        self.flush_size = flush_size
        self.thread_pool_size = thread_pool_size
        self.verify = verify
        self.tags = tags or {}
        self.headers = {
            "User-Agent": ua,
            "Content-Type": "application/json",
        }
        if gzipped:
            self.headers.update({"Content-Encoding": "gzip"})
        if kwargs.get("headers"):
            if isinstance(kwargs["headers"], dict):
                self.headers.update(kwargs.pop("headers"))
            else:
                raise ValueError()

        if username:
            self.auth = (username, password)

        self.total_lost_logs = 0
        self.last_flush_time: float = 0
        self.lock = threading.RLock()
        self.buffer = self.new_buffer()
        if thread_pool_size > 0:
            self.t_pool = ThreadPoolExecutor(
                thread_pool_size,
                thread_name_prefix="loki-uploader-",
            )

    def is_closed(self) -> bool:
        if hasattr(Client, "is_closed"):
            self._is_closed = getattr(Client, "is_closed")()
        return self._is_closed

    def close(self) -> None:
        self._is_closed = True
        with self.lock:
            if self.buffer.streams_count() == 0:
                return
            self.buffer.write(b"{}")
            self.flush()
            if self.thread_pool_size > 0:
                self.t_pool.shutdown(wait=True)

    def new_buffer(self) -> MetaBuffer:
        return StreamsGzip() if self.gzipped else StreamsBytesIO()

    def should_flush(self):
        """检查Buffer是否满了或者日志级别达到flushLevel"""
        return (
            time.time() - self.last_flush_time > self.flush_interval
            or self.buffer.streams_count() > self.flush_size
            or self.buffer.streams_size() > 2048_000
        )

    def put_stream(self, data: bytes | str):
        """向队列中添加数据"""
        if self._is_closed:
            raise Exception("LokiClient is closed")  # TODO
        if isinstance(data, str):
            data = data.encode("utf-8")
        with self.lock:
            if self.should_flush():
                self.buffer.write(data)
                self.flush()
                self.last_flush_time = time.time()
            else:
                self.buffer.write(data + b",")

    def flush(self):
        if self.buffer.streams_count() == 0:
            return
        stopped_buffer = self.buffer
        self.buffer = self.new_buffer()
        stopped_buffer.stop()

        if self.thread_pool_size > 0 and not self.t_pool._shutdown:
            self.t_pool.submit(self.post_streams, stopped_buffer)
        else:
            self.post_streams(stopped_buffer)

    def post_streams(self, stopped_buffer) -> bool:
        """"""
        post_streams = stopped_buffer.get_streams()
        retry = 0
        while retry < 1:
            time.sleep(retry)
            debugger_print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S.')}]LOKI LOGGING flush logs {stopped_buffer.streams_count()}, "
                f"data size {beautify_size(stopped_buffer.streams_size())} [{'Gzipped' if self.gzipped else 'NonGzipped'}], "
                f"retry {retry}"
            )
            try:
                if Client.__name__ == "Session":
                    # noinspection PyTypeChecker
                    res = self.post(self.loki_url, data=post_streams)
                else:
                    res = self.post(self.loki_url, content=post_streams)

                debugger_print(f"HTTP STATUS: {res.status_code} - {res.text}")
                if 200 <= res.status_code < 300:
                    return True
                if res.status_code == 400:
                    debugger_print(
                        "BODY:",
                        gzip.decompress(post_streams) if self.gzipped else post_streams,
                    )

            except Exception as _e:
                debugger_print(f"HTTPError {_e}")

            finally:
                retry += 1

        self.total_lost_logs += stopped_buffer.streams_count()
        raise RuntimeError(
            f"多次推送失败, 舍弃日志数量: "
            f"{stopped_buffer.streams_count()} / total: {self.total_lost_logs}"
        )
