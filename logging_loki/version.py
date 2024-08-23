"""
0.0.1 - 基本功能完成
    1. LokiHandler 能够向Loki提交数据
    2. LokiFormatter 能够格式化数据

    # 当前Benchmark结果:
        1. 在5 tags 状态下，支持稳定的每2s 7000+ 日志推送(极限状态可以到30000左右数据量，平均每条日志150字节)。
        2. CPU占用率为 logging.StreamHandler 的2-3倍, 内存占用率为其 2 倍。

0.1.1 - 
    1. LokiHandler 添加额外的控制参数:
        gzipped 是否进行Gzip压缩, 默认: True
        flush_interval 刷写到Loki的时间间隔, 默认: 2s

0.1.2 - 
    1. 添加metadata字段以区分tags
    2. 完善测试输出

0.1.3 -
    1. 抽离loki_client, 并使client同时支持requests and httpx.

    ==================================================
    2024-04-22 20:54:37  stream 分别压缩并合并

    Wait Time: 1e-05
    100000_file_True_1 TIME: 52s  CPU: [5.74s]  MEM: [18.27M  18.29M]
    100000_loki_True_1 TIME: 34s  CPU: [7.37s]  MEM: [37.87M  42.05M]
    100000_loki_False_1 TIME: 30s  CPU: [4.89s]  MEM: [46.85M  55.74M]

    Wait Time: 0.001
    100000_file_True_1 TIME: 122s  CPU: [8.66s]  MEM: [18.34M  18.35M]
    100000_loki_True_1 TIME: 116s  CPU: [15.19s]  MEM: [26.14M  27.10M]
    100000_loki_False_1 TIME: 103s  CPU: [9.37s]  MEM: [29.51M  31.23M]

0.2.0 -
    1. 使用BytesIO代替原有的队列

    ==================================================
    2024-04-24 21:42:39  使用IO缓冲，单线程

    Wait Time: 0.00001
    100000_file_True_1 TIME: 54s  CPU: [6.21s]  MEM: [24.56M  24.67M]
    100000_loki_True_1 TIME: 34s  CPU: [6.77s]  MEM: [30.75M  32.21M]
    100000_loki_False_1 TIME: 32s  CPU: [5.43s]  MEM: [43.12M  55.90M]

    Wait Time: 0.001
    100000_file_True_1 TIME: 126s  CPU: [9.41s]  MEM: [24.57M  24.62M]
    100000_loki_True_1 TIME: 124s  CPU: [14.97s]  MEM: [27.42M  29.68M]
    100000_loki_False_1 TIME: 115s  CPU: [11.14s]  MEM: [34.21M  38.79M]


    ==================================================
    2024-04-24 21:57:37  使用IO缓冲，100线程并行

    Wait Time: 0.00001
    100000_file_True_1 TIME: 77s  CPU: [16.35s]  MEM: [182.50M  218.13M]
    100000_loki_True_1 TIME: 126s  CPU: [24.83s]  MEM: [225.25M  245.96M]
    100000_loki_False_1 TIME: 110s  CPU: [20.62s]  MEM: [252.73M  305.50M]

    Wait Time: 0.001
    100000_file_True_1 TIME: 83s  CPU: [17.97s]  MEM: [72.15M  94.03M]
    100000_loki_True_1 TIME: 88s  CPU: [26.36s]  MEM: [78.98M  98.88M]
    100000_loki_False_1 TIME: 74s  CPU: [20.30s]  MEM: [79.70M  109.54M]

TODO 优化CPU和内存占用, 分片压缩CPU占用高，否则内存占用高。
TODO 减少外部依赖（弃用HTTPX，使用原生的HTTP方案）

0.3.1
    1. 不依赖第三方的HTTP客户端
    2. README添加用法
    3. LokiHandler & LokiFormatter 支持自定义metadata字段


"""

__version__ = "0.3.1"
