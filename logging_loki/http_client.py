import time
import threading
from concurrent.futures import ThreadPoolExecutor
from http.client import HTTPConnection, HTTPSConnection

from logging_loki.tools import debugger_print


class NeedRetryError(Exception):
    """重试"""


class ConnectionPool(ThreadPoolExecutor):

    def __init__(
        self,
        scheme: str,
        host: str,
        max_workers=None,
    ):
        super().__init__(
            max_workers=max_workers,
            thread_name_prefix="logging_loki_client_",
        )
        self.t_lock = threading.Lock()
        self.CONNECTION = (
            HTTPSConnection if scheme.upper() == "HTTPS" else HTTPConnection
        )
        self.connections = []
        self.host = host

    def get_connection(self):
        with self.t_lock:
            if self.connections:
                conn = self.connections.pop()
                # 返回前检查当前连接是否活跃
                return conn
            else:
                debugger_print("New Connection.")
                return self.CONNECTION(self.host)

    def release_connection(self, conn):
        with self.t_lock:
            self.connections.append(conn)

    def request(
        self,
        method,
        url,
        body: str | bytes = None,
        headers={},
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
        if retry == 0:
            debugger_print("多次重试后依旧错误")
            # TODO 保存Body
        try:
            conn = self.get_connection()
            conn.request(method, url, body, headers, encode_chunked=encode_chunked)
            resp = conn.getresponse()
            if 200 <= resp.status <= 299:
                debugger_print(f"[]Push Success.")
                return
            elif 300 <= resp.status <= 399:
                debugger_print("请求已经重定向...")

            elif 400 <= resp.status <= 499:
                debugger_print(f"请求错误: {resp.status}: {resp.read()}")

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

        except Exception as _e:
            print(_e)
        finally:
            self.release_connection(conn)

    def submit_request(
        self,
        method: str,
        url: str,
        body: str | bytes = None,
        headers: dict = {},
        *,
        encode_chunked=False,
    ):
        """在线程池中提交请求"""
        debugger_print()
        self.submit(
            self._request,
            method,
            url,
            body=body,
            headers=headers,
            encode_chunked=encode_chunked,
        )
