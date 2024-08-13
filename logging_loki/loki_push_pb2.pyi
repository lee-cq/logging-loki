from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Timestamp(_message.Message):
    __slots__ = ("seconds", "nanos")
    SECONDS_FIELD_NUMBER: _ClassVar[int]
    NANOS_FIELD_NUMBER: _ClassVar[int]
    seconds: int
    nanos: int
    def __init__(self, seconds: _Optional[int] = ..., nanos: _Optional[int] = ...) -> None: ...

class PushRequest(_message.Message):
    __slots__ = ("streams",)
    STREAMS_FIELD_NUMBER: _ClassVar[int]
    streams: _containers.RepeatedCompositeFieldContainer[StreamAdapter]
    def __init__(self, streams: _Optional[_Iterable[_Union[StreamAdapter, _Mapping]]] = ...) -> None: ...

class StreamAdapter(_message.Message):
    __slots__ = ("labels", "entries", "hash")
    LABELS_FIELD_NUMBER: _ClassVar[int]
    ENTRIES_FIELD_NUMBER: _ClassVar[int]
    HASH_FIELD_NUMBER: _ClassVar[int]
    labels: str
    entries: _containers.RepeatedCompositeFieldContainer[EntryAdapter]
    hash: int
    def __init__(self, labels: _Optional[str] = ..., entries: _Optional[_Iterable[_Union[EntryAdapter, _Mapping]]] = ..., hash: _Optional[int] = ...) -> None: ...

class EntryAdapter(_message.Message):
    __slots__ = ("timestamp", "line", "structuredMetadata")
    class StructuredMetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    STRUCTUREDMETADATA_FIELD_NUMBER: _ClassVar[int]
    timestamp: Timestamp
    line: str
    structuredMetadata: _containers.ScalarMap[str, str]
    def __init__(self, timestamp: _Optional[_Union[Timestamp, _Mapping]] = ..., line: _Optional[str] = ..., structuredMetadata: _Optional[_Mapping[str, str]] = ...) -> None: ...
