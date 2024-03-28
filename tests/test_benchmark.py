import logging
import random
import os
import time

from logging_loki.handler import LokiHandler


logger = logging.getLogger("logging-loki.test_benchmark")


def error(times):
    try:
        100 / 0
    except Exception as _e:
        logger.error(f"Error: {_e}", exc_info=_e, extra={"tags": {"t": times}})


def info(times):
    logger.info(
        "".join(
            random.choices(
                "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?",
                k=99,
            )
        ),
        extra={"tags": {"t": times}},
    )


def main():
    handler = LokiHandler(
        level="INFO",
        loki_url=os.getenv("LOKI_URL"),
        username=os.getenv("LOKI_USERNAME"),
        password=os.getenv("LOKI_PASSWORD"),
        tags={"app": "test_benchmark"},
    )

    if not handler.test_client():
        raise ValueError("LOKI_URL None")
    print(f"Will Push to Loki: {handler.client_info['base_url']}")

    logger.addHandler(handler)

    for i in range(1_000_000):
        time.sleep(0.000000001)
        random.choice([error, info])(i)


if __name__ == "__main__":
    print("start.")
    main()
