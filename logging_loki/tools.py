import os
import time


def debugger_print(*args, **kwargs):
    if os.getenv("LOKI_LOGGING_DEBUG"):
        print(f'[{time.strftime("%Y-%m-%d %H:%M:%S")}]', *args, **kwargs)


def beautify_size(size):
    if size < 1024:
        return f"{size:.2f} B"
    if size < 1024 * 1024:
        return f"{size / 1024 :.2f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024 :.2f} MB"
    if size < 1024**4:
        return f"{size / 1024 **3 :.2f} GB"
    if size < 1024**5:
        return f"{size / 1024 **4 :.2f} TB"


if __name__ == "__main__":
    print(beautify_size(4048210))
