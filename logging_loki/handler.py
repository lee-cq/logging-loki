from warnings import warn
from logging import Formatter, Handler

from logging_loki.loki_client import LokiClient
from logging_loki.formater import LokiFormatter

try:
    import orjson as json
except ImportError:
    import json


class LokiHandler(Handler):
    """Loki日志发送"""

    def __init__(
        self,
        loki_url: str,
        username: str = None,
        password: str = None,
        level: int | str = "ERROR",
        gzipped: bool = True,  # 上传的BODY是否进行GZIP压缩
        flush_interval: int = 2,  # 将缓存刷写到Loki的时间频率， 默认2秒
        flush_size: int = 10000,  # 将缓存中允许的最大值
        thread_pool_size: int = 3,  # 刷写线程池大小，如果为0，将使用同步上传
        verify: bool = True,  # SSL 验证
        tags: dict = None,  # 使用的TAG
        included_field: tuple | list | set = None,  # 包含的logging字段，默认全部字段
        fmt: str = None,  # message的格式，默认simple
        fqdn: bool = False,  # 主机名是否是FQDN格式
        **kwargs,
    ) -> None:
        super().__init__(level)

        self.loki_tags = tags or {}
        self.loki_client = LokiClient(
            loki_url=loki_url,
            username=username,
            password=password,
            gzipped=gzipped,
            flush_interval=flush_interval,
            flush_size=flush_size,
            thread_pool_size=thread_pool_size,
            verify=verify,
            **kwargs,
        )
        self.setFormatter(
            LokiFormatter(fmt=fmt, tags=tags, included_field=included_field, fqdn=fqdn)
        )

    def setFormatter(self, fmt: Formatter | None) -> None:
        if not isinstance(fmt, LokiFormatter):
            raise TypeError(f"fmt 必须是 LokiFormater 或其子类 [{type(fmt)}]")

        return super().setFormatter(fmt)

    @staticmethod
    def is_stream(stream) -> bool:
        return isinstance(stream, dict) and "stream" in stream and "values" in stream

    def emit(self, record) -> None:
        """记录一条日志到缓存，并按需生成一个定时器，在定时器结束时将日志实际Push到Loki。

        如果在定时器开始前就已经将日志推送，则会有推送线程取消该定时器。
        """
        # noinspection PyUnresolvedReferences
        if self._closed:
            warn(f"[LokiHandler]{self.get_name()} 已经关闭，日志无法再被记录到Loki.")
            return  # 如果Handler已经关闭, 不再添加日志

        stream = self.formatter.format(record=record)
        if not self.is_stream(stream):
            self.handleError(record)  # "self.formatter.format 必须返回一个Dict"
            return

        self.loki_client.push_wait(stream["stream"], stream["values"])

    def close(self) -> None:
        super().close()
        self.loki_client.close()
        # BUG 程序无法正常退出
