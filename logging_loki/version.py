
"""
0.0.1 - 基本功能完成
    1. LokiHandler 能够向Loki提交数据
    2. LokiFormatter 能够格式化数据

    # 当前Benchmark结果:
        1. 在5 tags 状态下，支持稳定的每2s 7000+ 日志推送(极限状态可以到30000左右数据量，平均每条日志150字节)。
        2. CPU占用率为 logging.StreamHandler 的2-3倍, 内存占用率为其 2 倍。

0.1.1 - 
    1. LokiHandler 添加额外的控制参数:
        gzipd 是否进行Gzip压缩, 默认: True
        flush_interval 刷写到Loki的时间间隔, 默认: 2s



TODO 优化CPU和内存占用
TODO 减少外部依赖（弃用HTTPX，使用原生的HTTP方案）
"""

__version__ = "0.1.0"
