"""
logsetup.py — Shared logging configuration for gann_bot.

Provides get_logger(module_name) which returns a configured logging.Logger that
writes to both gannbot.log (file) and the console (stdout). The log format is:

    [TIMESTAMP] [LEVEL] [MODULE] message

This helper exists so every module logs identically without duplicating the
handler setup. It is not part of the original numbered file list but supports
implementation rules 3 and 4 (all logging to gannbot.log, consistent format).
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import config

_CONFIGURED = False


def _configure_root(log_filename: str = None) -> None:
    """
    Configure the root logger once with a file handler and a console handler.

    Params:
        log_filename (str): optional target log file. Defaults to config.LOG_FILE
            (gannbot_{P}.log) so existing callers are unaffected. A standalone
            process (e.g. chart_report.py) can pass its own file so its output —
            and any third-party library noise routed through the root logger —
            stays out of the bot's log.

    Returns:
        None
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    fmt = logging.Formatter(
        fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    # Rotating file handler — appends to log_filename, defaulting to
    # config.LOG_FILE (logs/gannbot_{P}.log). Rotation caps each log at 10 MB
    # with 5 backups (≤ 50 MB per log) so long-running bots can never grow a
    # log without bound. Ensure the parent dir exists so a logs/ target works
    # on a fresh checkout regardless of launch order.
    _log_path = log_filename or config.LOG_FILE
    os.makedirs(os.path.dirname(_log_path) or ".", exist_ok=True)
    fh = RotatingFileHandler(_log_path, maxBytes=10 * 1024 * 1024,
                             backupCount=5, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Console handler — mirrors everything to stdout
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    _CONFIGURED = True


def get_logger(module_name: str, log_filename: str = None) -> logging.Logger:
    """
    Return a logger for the given module name, configuring handlers on first call.

    Params:
        module_name (str): short module identifier shown in the [MODULE] field.
        log_filename (str): optional log file for the root configuration. Only the
            FIRST get_logger() call in a process configures the root logger, so to
            redirect a standalone process's logs this must be passed on that first
            call. Defaults to config.LOG_FILE (unchanged behaviour).

    Returns:
        logging.Logger: a ready-to-use logger.
    """
    _configure_root(log_filename)
    return logging.getLogger(module_name)
