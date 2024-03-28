import os
import random
import time
from logging_loki.handler import LokiHandler


handler = LokiHandler(
    level="DEBUG",
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    tags={"app": "test_loki_headler"},
)

streams = [
    {
        "stream": {
            "app": "test1",
            "instencs": "test-ff",
            "test": "ess",
            "it": i // 100,
        },
        "values": [
            [
                str(int(time.time() * 1_000_000_000)),
                f"i={i}"
                + "".join(
                    random.choices(
                        "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?",
                        k=99,
                    )
                ),
                {"i": str(i)},
            ]
            
        ],
    }for i in range(57000)
]

# print(streams)


handler.post_logs(streams=streams, retry_times=2)
