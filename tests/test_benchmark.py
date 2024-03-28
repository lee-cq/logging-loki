import logging
import random
import os
import sys
import time

from logging_loki.handler import LokiHandler

def get_argv(index, defualt=None):
    try:
        return sys.argv[index]
    except IndexError:
        return defualt

SIZE = int(get_argv(1, 1_000))
H_TYPE = get_argv(2, "loki")
GZIP = bool(get_argv(3, 'true').lower() in ['t', 'true', '1'])
PUT_TIME = int(get_argv(4, 2))


logger = logging.getLogger("logging-loki.test_benchmark")


def error(times):
    try:
        100 / 0
    except Exception as _e:
        logger.error(f"Error: {_e}", exc_info=_e, extra={"tags": {"t": times}})


def info(times):
    _log= "".join(
            random.choices(
                "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?",
                k=99,
            )
        )
    logger.info(
        _log,
        extra={"tags": {"t": times}}
    )


def main():
    handler = LokiHandler(
        level="INFO",
        loki_url=os.getenv("LOKI_URL"),
        username=os.getenv("LOKI_USERNAME"),
        password=os.getenv("LOKI_PASSWORD"),
        tags={"app": "test_benchmark"},
        gziped=GZIP,
    )
    h_std = logging.StreamHandler()
    h_std.setLevel("INFO")
    h_std.setFormatter(
        logging.Formatter(
            "[%(asctime)s] - %(module)s:%(lineno)d - %(levelname)s - %(message)s"
        )
    )

    if not handler.test_client():
        raise ValueError("LOKI_URL None")
    print(f"Will Push to Loki: {handler.client_info['base_url']}")
    logger.setLevel("INFO")
    logger.addHandler(handler if H_TYPE == 'loki' else h_std)
    # logger.addHandler(h_std)

    for i in range(SIZE):
        time.sleep(0.000000001)
        # random.choice([error, info])(i)
        info(i)


if __name__ == "__main__":
    print("start.")
    main()
