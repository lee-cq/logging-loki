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
