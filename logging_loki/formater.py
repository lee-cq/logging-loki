import socket
from logging import Formatter, LogRecord
from typing import Any, Literal, Mapping

DEFUALT_FIELD_MAX = (
    "filename",
    "funcName",
    "levelname",
    "lineno",
    "module",
    "name",
    "process",
    "pathname",
    "processName",
    "threadName",
)

DEFUALT_FIELD = (
    "levelname",
    "name",
    "module",
    "threadName",
)

DEFUALT_FIELD_MIN = (
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

        self.included_field = included_field if included_field else DEFUALT_FIELD_MIN

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
                **{str(k): str(v) for k, v in record_tags.items()}
            },
            "values": [
                [
                    str(int(record.created * 1_000_000_000)),
                    super().format(record=record),
                    metadata,
                ],
            ],
        }
