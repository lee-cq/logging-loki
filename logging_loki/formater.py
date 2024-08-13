import socket
from logging import Formatter, LogRecord
from typing import Any, Literal, Mapping

DEFAULT_FIELD_MAX = (
    "asctime",  # 表示人类易读的 LogRecord 生成时间。 默认形式为 '2003-07-08 16:49:45,896' （逗号之后的数字为时间的毫秒部分）。
    "created",  # LogRecord 被创建的时间（即 time.time() 的返回值）。
    "filename",  # 文件名
    "funcName",  # 函数名
    "levelname",  # 日志等级名称 （'DEBUG'，'INFO'，'WARNING'，'ERROR'，'CRITICAL'）
    "levelno",  # 日志等级号
    "lineno",  # 产生日志的行号
    "module",  # 产生日志的模块
    "msecs",  # 创建时间的毫秒部分
    "name",  # Logger的名字
    "pathname",  # 发出日志记录调用的源文件的完整路径名（如果可用）。
    "process",  # 进程ID（如果可用）
    "processName",  # 进程名（如果可用）
    "relativeCreated",  # 以毫秒数表示的 LogRecord 被创建的时间，即相对于 logging 模块被加载时间的差值。
    "thread",  # 线程ID（如果可用）
    "threadName",  # 线程名（如果可用）
    "taskName",  # asyncio.Task 名称（如果可用）。 3.12+
)

DEFAULT_FIELD = (
    "levelname",
    "name",
    "module",
    "threadName",
)

DEFAULT_FIELD_MIN = (
    "levelname",
    "name",
)


def json_s(v):
    if isinstance(v, set):
        return list(v)


class LokiFormatter(Formatter):
    """"""

    def __init__(
        self,
        fmt: str | None = None,
        datefmt: str | None = None,
        style: Literal["%"] | Literal["{"] | Literal["$"] = "%",
        validate: bool = True,
        *,
        tags: dict = None,
        included_field: tuple | list | set = None,
        fqdn: bool = False,
        defaults: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(fmt, datefmt, style, validate, defaults=defaults)

        self.hostname = socket.getfqdn() if fqdn else socket.gethostname()

        assert isinstance(
            tags, dict | None
        ), f"tags 参数必须是dict or None, 而不是{type(tags)}"
        self.tags = tags if tags else dict()

        self.included_field = included_field if included_field else DEFAULT_FIELD_MIN

    def format(self, record: LogRecord) -> dict:
        record_tags = getattr(record, "tags", dict())
        if not isinstance(record_tags, dict):
            record_tags = dict()

        recode_meta = getattr(record, "metadata", dict())
        if not isinstance(recode_meta, dict):
            recode_meta = dict()

        metadata = {
            **{str(k): str(v) for k, v in recode_meta.items()},
            **{
                i: str(record.__dict__[i])
                for i in record.__dict__
                if i in self.included_field
            },
        }
        return {
            "stream": {
                "instance": self.hostname,
                **self.tags,
                **{str(k): str(v) for k, v in record_tags.items()},
            },
            "values": [
                [
                    int(record.created * 1_000_000_000),
                    super().format(record=record),
                    metadata,
                ],
            ],
        }
