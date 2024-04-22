import os


def debugger_print(*args, **kwargs):
    if os.getenv("LOKI_LOGGING_DEBUG"):
        print(*args, **kwargs)


def beautify_size(size):
    if size < 1024:
        return f"{size:.2f} B"
    if size < 1024 * 1024:
        return f"{size / 1024 :.2f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / 1024 / 1024 :.2f} MB"


if __name__ == "__main__":
    print(beautify_size(4048210))
