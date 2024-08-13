# logging-loki
Python logging handler for Loki.

# 用法

`pip install logging-loki`

##  直接使用
```python
from logging_loki import LokiHandler

handler = LokiHandler(
    loki_url=os.getenv("LOKI_URL"),
    username=os.getenv("LOKI_USERNAME"),
    password=os.getenv("LOKI_PASSWORD"),
    level="DEBUG",
    thread_pool_size=0,
    tags={"service_name": "test_loki_handler"},
    included_field=DEFAULT_FIELD_MAX,
    gzipped=False,
    verify=False,
)

logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel("DEBUG")

logger.info("test ok.")
logger.debug("test debug...")
```
## 使用配置字典

```python
import logging.config
import logging

config_dict = {
    "version": 1,
    "handlers": {
        "loki": {
            "class": "logging_loki.LokiHandler",
            "loki_url": "http://localhost:3100/loki/api/v1/push",
            "username": "test",
            "password": "test",
            "thread_pool_size": 5,
            "tags": {"service_name": "test_loki_handler"},
            "gzipped": True,  # 传输时使用Gzip压缩
            "verify": False,  # SSL验证
        }
    },
    "root": {
        "level": "DEBUG",
        "handers": ["loki"],
    },
}

logging.config.dictConfig(config_dict)
logger = logging.getLogger()

logger.info("test info ok.")

```


# Benchmark

> Push Logs to Grafana Cloud, Free plan.
> Driver is Github Codespaces 2C4G.

MAX push logs 57000 per post, per 3s. 

Use More Member but faster.


## 1_000_00 logs (Error and Info )
1. FileHandler:
    Run Time: 22s
    Use Cpus: 9.32s
    Mem size: 18.75M MAX: 18.83M

2. LokiHandler No gzip; flush logs per 2s
    Run Time: 14s
    Use Cpus: 8.42s
    Mem size: Agv: 72.00M Max: 102.88M  (2.79, 4.39)倍

3. LokiHandler gzipped; flush logs per 2s
    Run Time: 13s
    Use Cpus: 8.42s
    Mem size: Agv: 65.59M Max: 93.68M (2.45, 3.8)

## Size 1_000_000 (Error and Info)

1. FileHandler
    Run Time: 224
    Use Cpus: 89.99s
    Mem Size: Agv: 18.91M   Max: 18.91M


2. LokiHandler No Gzip; flush logs per 2s
    Run Time: 119s
    Use Cpus: 80.06s
    Mem Size: Agv: 82.06 M  Max: 116.64M (3.26, 5.1)

3. LokiHandler Gzip; flush logs per 2s
    Run Time: 119s
    Use Cpus: 91.69
    Mem Size: Agv: 76.31 M Max: 89.48 (3.0, 3.7)

4. LokiHandler No Gzip; flush logs per 1s
    Run Time: 114s
    Use Cpus: 77.73	
    Mem Size: Agv: 57.22M  Max: 71.77  (2.0, 2.77)

5. LokiHandler Gzip; flush logs per 1s
    Run Time: 122s
    Use Cpus: 92.45
    Mem Size: Agv: 58.89M  MAX: 70.44  (2.1, 2.71)