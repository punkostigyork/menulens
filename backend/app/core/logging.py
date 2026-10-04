import logging


class RedactQueryFilter(logging.Filter):
    """Keep access status/path logs without storing location or other query values."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple) and len(record.args) == 5:
            args = list(record.args)
            args[2] = str(args[2]).split("?", 1)[0]
            record.args = tuple(args)
        return True


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    access = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, RedactQueryFilter) for f in access.filters):
        access.addFilter(RedactQueryFilter())
