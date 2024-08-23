import logging
import os
import random
import time
import multiprocessing
from concurrent.futures import ThreadPoolExecutor

import psutil

from logging_loki.handler import LokiHandler

ALL_KEYS = "qwertyuiopasdfghjkl;zxcvbnm,./1234567890-=`!@#$%^&*()_+QWERTYUIOP{}ASDFGHJKL:ZXCVBNM<>?"


def randon_str(k):
    return "".join(random.choices(ALL_KEYS, k=k))


def create_handler(
    log_type: str = "file",
    loki_interval: int = 2,  # Loki提交周期
    loki_cache_size: int = 102400,  # LokiClient缓存大小
    loki_cache_count: int = 1000,  # LokiClient缓存条目数量,
):
    """"""
    fmt = "[%(asctime)s] - %(module)s:%(lineno)d - %(levelname)s - %(message)s"
    handler = (
        LokiHandler(
            loki_url=os.getenv("LOKI_URL"),
            username=os.getenv("LOKI_USERNAME"),
            password=os.getenv("LOKI_PASSWORD"),
            level="INFO",
            flush_interval=loki_interval,
            max_cache_size=loki_cache_size,
            max_cache_stream=loki_cache_count,
            tags={"app": "test_benchmark"},
            fmt=fmt,
        )
        if log_type == "loki"
        else logging.FileHandler(
            filename="test_benckmark.log",
            mode="w",
            delay=True,
        )
    )

    if handler.__class__ == "FileHandler":
        handler.setFormatter(logging.Formatter(fmt))

    handler.setLevel("INFO")
    if log_type == "loki" and not handler.loki_client.loki_url:
        raise ValueError("LOKI_URL None")
    print(
        "Will Push to ",
        (
            f"Loki: {handler.loki_client.loki_url}"
            if log_type == "loki"
            else f"File: {handler.baseFilename}"
        ),
    )

    return handler


def runner(
    log_type: str = "file",
    log_counts: int = 100_000,  # 日志条目
    log_interval: float = 0.01,  # 生成周期
    loki_interval: int = 2,  # Loki提交周期
    loki_cache_size: int = 102400,  # LokiClient缓存大小
    loki_cache_count: int = 1000,  # LokiClient缓存条目数量
    **kwargs,
):
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
        logger.info(randon_str(99), extra={"matadata": {"t": times}})

    handler = create_handler(log_type, loki_interval, loki_cache_size, loki_cache_count)

    logger = logging.getLogger("logging-loki.test_benchmark")
    logger.setLevel("INFO")
    logger.addHandler(handler)

    with ThreadPoolExecutor(100, "logs_") as pool:
        for i in range(log_counts // 2):
            if log_type == "file" and i % 2000 == 0:
                print(f"\r{i * 2}/{log_counts} ({i*2/log_counts * 100:.2f} %)", end="")

            time.sleep(log_interval)
            pool.submit(info, i, True)
            pool.submit(error, i, True)


def benchmark(
    log_type: str = "file",
    log_counts: int = 100_000,  # 日志条目
    log_interval: float = 0.01,  # 生成周期
    loki_interval: int = 2,  # Loki提交周期
    loki_cache_size: int = 102400,  # LokiClient缓存大小
    loki_cache_count: int = 1000,  # LokiClient缓存条目数量
):
    """"""
    kwargs = locals().copy()
    name = f"{log_type},c:{log_counts},li:{log_interval},[{loki_interval},{loki_cache_size},{loki_cache_count}]"

    mp = multiprocessing.Process(target=runner, kwargs=kwargs)
    mp.start()

    while mp.pid is None:
        time.sleep(0.001)

    ps = psutil.Process(mp.pid)
    rst = []
    while mp.exitcode is None:
        # 每秒采集CPU和内存信息
        rst.append((ps.cpu_times().user, float(ps.memory_info().rss)))
        time.sleep(1)

    cpus, mems = list(zip(*rst))
    return (
        f"{name:<40} TIME: {len(rst)}s  CPU: [{sum(cpus) / len(cpus):.2f}s]  "
        f"MEM: [{sum(mems) / len(mems) / 1048576:.2f}M  {max(mems) / 1048576:.2f}M]"
    )


def main():
    ls = [
        # log_type: str = "file",
        # log_counts: int = 100_000,  # 日志条目
        # log_interval: float = 0.01,  # 生成周期
        # loki_interval: int = 2,  # Loki提交周期
        # loki_cache_size: int = 102400,  # LokiClient缓存大小
        # loki_cache_count: int = 1000,  # LokiClient缓存条目数量
        #
        ("file", 100_000, 0.00001, 2, 102400, 1000),
        ("loki", 100_000, 0.00001, 2, 102400, 1000),
        ("loki", 100_000, 0.00001, 2, 1024, 1000),
        ("loki", 100_000, 0.00001, 2, 102400, 10),
        #
        ("file", 10_000, 0.001, 2, 102400, 1000),
        ("loki", 10_000, 0.001, 2, 102400, 1000),
        ("loki", 10_000, 0.001, 2, 1024, 1000),
        ("loki", 10_000, 0.001, 2, 102400, 10),
        #
        ("file", 1000, 0.1, 2, 102400, 1000),
        ("loki", 1000, 0.1, 2, 102400, 1000),
        ("loki", 1000, 0.1, 2, 1024, 1000),
        ("loki", 1000, 0.1, 2, 102400, 10),
        #
        ("file", 500, 0.5, 2, 102400, 1000),
        ("loki", 500, 0.5, 2, 102400, 1000),
        ("loki", 500, 0.5, 2, 1024, 1000),
        ("loki", 500, 0.5, 2, 102400, 10),
    ]
    ls_test = [
        ["file", 2, 1, 0, 0, 0],
        ["loki", 2, 1, 2, 10240, 100],
    ]
    rest = "=" * 50
    rest += f"\n{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    for args in ls:
        if args[0] == "file":
            rest += "-" * 50 + "\n"
        rest += benchmark(*args) + "\n"

    print(rest)
    open("AA_rest_agv.txt", "a+").write(rest)


if __name__ == "__main__":
    main()
