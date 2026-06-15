import logging

logger = logging.getLogger("healer")


class HealerBase:
    def _log(self, msg, level="info"):
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"[{self.__class__.__name__}] {msg}")

    def _stats_summary(self):
        return ""
