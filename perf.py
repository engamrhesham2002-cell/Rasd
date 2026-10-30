# Rasd - قياس أداء العمليات الحرجة (سجل دوّار صغير)
import functools
import logging
import time
from logging.handlers import RotatingFileHandler

perf_logger = logging.getLogger('rasd.perf')


def configure(log_path, level=logging.INFO):
    """يهيئ سجل الأداء مرة واحدة دون تكرار الـ handlers."""
    if perf_logger.handlers:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s', '%Y-%m-%d %H:%M:%S'
    ))
    perf_logger.addHandler(handler)
    perf_logger.setLevel(level)
    perf_logger.propagate = False


def timed_method(label):
    """يقيس زمن أي method ويسجله في rasd.log."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - started) * 1000
                project = ''
                if args and hasattr(args[0], 'project'):
                    project = getattr(args[0], 'project', '') or ''
                perf_logger.info(
                    '%s | %.1f ms | project=%s', label, elapsed_ms, project
                )
        return wrapper
    return decorator
