import logging

from hub_platform.events.context import get_correlation_id


class CorrelationIdLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True
