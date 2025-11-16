# Global store for per-session loggers. Necessary to propagate loggers into other
# scripts that use the session logger (processing.py, utils.py, etc).
SESSION_LOGGERS = {}