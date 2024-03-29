import json
import logging
import random
import os
import sys
import time

import psutil

from logging_loki.handler import LokiHandler


def get_argv(index, defualt=None):
    try:
        return sys.argv[index]
    except IndexError:
        return defualt


# SIZE = int(get_argv(1, 1_000))
# H_TYPE = get_argv(2, "loki")
# GZIP = bool(get_argv(3, "true").lower() in ["t", "true", "1"])
PUT_TIME = int(get_argv(4, 2))


logger = logging.getLogger("logging-loki.test_benchmark")


def error(times):
    try:
        100 / 0
    except Exception as _e:
        logger.error(f"Error: {_e}", exc_info=_e, extra={"tags": {"t": times}})


def info(times):
    _log = "".join(
        random.choices(
            "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?",
            k=99,
        )
    )
    logger.info(_log, extra={"tags": {"t": times}})


def main(size=10_000, h_type="loki", gziped=True, put_time=2):
    handler = LokiHandler(
        level="INFO",
        loki_url=os.getenv("LOKI_URL"),
        username=os.getenv("LOKI_USERNAME"),
        password=os.getenv("LOKI_PASSWORD"),
        tags={"app": "test_benchmark", "gziped": "true"},
        gziped=gziped,
        flush_interval=put_time,
        fmt="[%(asctime)s] - %(module)s:%(lineno)d - %(levelname)s - %(message)s",
    )

    h_std = logging.FileHandler("test_benchmark.log", mode="w")
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
    logger.addHandler(handler if h_type == "loki" else h_std)

    for i in range(size // 2):
        time.sleep(0.000000001)
        # random.choice([error, info])(i)
        info(i)
        error(i)


def bench():
    """"""
    bs = (
        # (1_000_000, "file", True, 1),
        (1_000_000, "loki", True, 1),
        (1_000_000, "loki", False, 1),
        
    )

    import multiprocessing

    _rrst = []
    for args in bs:
        p = multiprocessing.Process(
            target=main,
            args=args,
        )
        p.start()
        while p.pid is None:
            time.sleep(0.001)
        _p = psutil.Process(p.pid)
        rst = []
        while p.exitcode is None:
            rst.append((_p.cpu_times().user, float(_p.memory_info().rss)))
            time.sleep(1)
        _rrst.append(rst)
        name = "_".join(str(_) for _ in args)
        json.dump(rst, open(name + ".json", "w"))
        with open(name + ".txt", "w") as f:
            [print(x, y, file=f) for x, y in rst]

    _m_len = max(len(_) for _ in _rrst)
    _rrst = [l.append((0, 0)) for l in _rrst for _ in range(_m_len - len(l))]

    rrrst = []
    for i in range(_m_len):
        __time = []
        for j in range(len(_rrst)):
            __time.extend(_rrst[j][i])
        rrrst.append(__time)
    json.dump(rst, open("all_data.json", "w"))


if __name__ == "__main__":
    print("start.")

    bench()
