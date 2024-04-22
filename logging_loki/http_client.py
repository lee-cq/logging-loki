from functools import cached_property
from http.client import HTTPConnection, HTTPException, HTTPSConnection
import threading
import time

from logging_loki.tools import debugger_print


class HttpClient:
    """Loki 的 HTTP 请求客户端。

    包含请求, 连接池, 错误重试
    """

    def __init__(self, base_url, headers, context=None) -> None:
        self.base_url = base_url
        self.headers = headers
        self.context = context

    @cached_property
    def split_url(self) -> tuple[str, str, str]:
        """协议, host, url"""
        _c = self.base_url.split("/", maxsplit=3)
        return _c[0], _c[2], "/" + _c[3]

    def get_client(self) -> HTTPConnection | HTTPSConnection:
        if self.split_url[0].lower() == "https:":
            return HTTPSConnection(self.split_url[1], context=self.context)
        else:
            return HTTPConnection(self.split_url[1])

    _cached_client = None

    def cached_client(self):
        if self._cache_client and self._cached_client.closed() == False:
            return self._cached_client
        _c = self.get_client()
        self._cached_client = _c
        return _c

    def _post(self, data: str | bytes) -> int:
        print("_post")
        with threading.Lock():
            try:
                h = self.get_client()
                h.putrequest("POST", self.split_url[2])
                for hdr, value in self.headers.items():
                    h.putheader(hdr, value)
                h.endheaders(data)
                res = h.getresponse()
                debugger_print(f"LokiHandler HTTP {res.status}: {res.read()}")
                if 200 <= res.status <= 299:
                    return 200
                return False
            except HTTPException as _e:
                debugger_print(f"LokiHandler HTTPClient Error: {_e}")
                return -1
            except Exception as _e:
                debugger_print(_e)
                return -2

    def post(self, data) -> bool:
        retry_times = 0
        while retry_times < 3:
            try:
                time.sleep(retry_times)
                res: int = self._post(data=data)
                if res == 200:
                    return True
                if 400 <= res <= 499:
                    return False
            finally:
                retry_times += 1
        return False
