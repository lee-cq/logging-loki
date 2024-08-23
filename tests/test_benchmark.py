import json
import logging
import random
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import psutil

from logging_loki.handler import LokiHandler
from logging_loki.formater import DEFAULT_FIELD_MAX


def get_argv(index, default=None):
    try:
        return sys.argv[index]
    except IndexError:
        return default


PUT_TIME = int(get_argv(4, 2))


logger = logging.getLogger("logging-loki.test_benchmark")


def error(times, wait=False):
    if wait:
        time.sleep(random.random() / 100)
    try:
        100 / 0
    except Exception as _e:
        logger.error(f"Error: {_e}", exc_info=_e, extra={"metadata": {"t": times}})


def info(times, wait=False):
    if wait:
        time.sleep(random.random() / 100)
    _log = "".join(
        random.choices(
            "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?",
            k=99,
        )
    )
    logger.info(_log, extra={"matadata": {"t": times}})


def main(size=10_000, h_type="loki", put_time=2, wait_time=0.00001):
    handler = LokiHandler(
        loki_url=os.getenv("LOKI_URL"),
        username=os.getenv("LOKI_USERNAME"),
        password=os.getenv("LOKI_PASSWORD"),
        level="INFO",
        flush_interval=put_time,
        tags={
            "app": "test_benchmark",
        },
        included_field=DEFAULT_FIELD_MAX,
        fmt="[%(asctime)s] - %(module)s:%(lineno)d - %(levelname)s - %(message)s",
    )

    h_std = logging.FileHandler("test_benchmark.log", mode="w")
    h_std.setLevel("INFO")
    h_std.setFormatter(
        logging.Formatter(
            "[%(asctime)s] - %(module)s:%(lineno)d - %(levelname)s - %(message)s"
        )
    )

    if not handler.loki_client.loki_url:
        raise ValueError("LOKI_URL None")
    print(
        "Will Push to ",
        f"Loki: {handler.loki_client.loki_url}" if h_type == "loki" else "File",
    )
    logger.setLevel("INFO")
    logger.addHandler(handler if h_type == "loki" else h_std)

    with ThreadPoolExecutor(100, "logs_") as pool:
        for i in range(size // 2):
            if h_type == "file" and i % 2000 == 0:
                print(f"\r {i * 2} / {size} ({i*2/size:.2f} %)   ", end="")
            time.sleep(wait_time)
            pool.submit(info, i, True)
            pool.submit(error, i, True)


def bench():
    """"""
    bs = (
        # Size     target   gzip  put_time
        (1_000_00, "file", 2),
        (1_000_00, "loki", 2),
    )
    sleep_times = (0.00001, 0.001)

    import multiprocessing

    _rrst_agv = open(f"AA_rest_agv.txt", "a+")
    _rrst = []
    print("\n\n", "=" * 50, file=_rrst_agv)
    print(time.strftime("%Y-%m-%d %H:%M:%S"), file=_rrst_agv, flush=True)
    for sleep_t in sleep_times:
        print(
            f"\nWait Time: {sleep_t}",
            file=_rrst_agv,
        )
        for args in bs:
            p = multiprocessing.Process(
                target=main, args=args, kwargs={"wait_time": sleep_t}
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
            cpus, mems = list(zip(*rst))
            print(
                f"{name} TIME: {len(rst)}s  CPU: [{sum(cpus) / len(cpus):.2f}s]  "
                f"MEM: [{sum(mems) / len(mems) / 1048576:.2f}M  {max(mems) / 1048576:.2f}M]",
                file=_rrst_agv,
                flush=True,
            )

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
    # set -a; . .env ; set +a
    print("start.")

    try:
        bench()
        print(open("AA_rest_agv.txt").read())
    except:
        pass
