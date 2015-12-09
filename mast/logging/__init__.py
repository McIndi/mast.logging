import logging
from functools import wraps
from mast.timestamp import Timestamp
from logging.handlers import TimedRotatingFileHandler
from mast.config import get_configs_dict
import os

mast_home = os.environ["MAST_HOME"] or os.getcwd()

config = get_configs_dict()
config = config["logging.conf"]
level = int(config["logging"]["level"])
unit = config["logging"]["rolling_unit"]
interval = int(config["logging"]["rolling_interval"])
propagate = bool(config["logging"]["propagate"])
backup_count = int(config["logging"]["backup_count"])


filemode = "a"
_format = "; ".join((
    "level=%(levelname)s",
    "datetime=%(asctime)s",
    "process_name=%(processName)s",
    "pid=%(process)d",
    "thread=%(thread)d",
    "message=%(message)s"))


def make_logger(
        name,
        level=level,
        fmt=_format,
        filename=None,
        when=unit,
        interval=interval,
        propagate=propagate,
        backup_count=backup_count):
    _logger = logging.getLogger(name)
    if _logger.handlers:
        if len(_logger.handlers) >= 1:
            return _logger

    _logger.setLevel(level)
    _formatter = logging.Formatter(fmt)

    if not filename:
        _filename = "{}.log".format(name)
        if "mastd" in os.environ:
            _filename = os.path.join(
                mast_home,
                "var",
                "log",
                "mastd",
                _filename)
        else:
            _filename = os.path.join(
                mast_home,
                "var",
                "log",
                _filename)
        filename = _filename
    try:
        _handler = TimedRotatingFileHandler(
            filename,
            when=when,
            interval=interval)
        _handler.setFormatter(_formatter)
        _handler.setLevel(level)
        _logger.addHandler(_handler)
        _logger.propagate = propagate
    except IOError:
        from getpass import getuser
        fname = os.path.basename(filename)
        filename = filename.replace(
            fname,
            "{}-{}-{}".format(
                Timestamp().timestamp,
                getuser(),
                fname))
        _handler = TimedRotatingFileHandler(
            filename,
            when=when,
            interval=interval)
        _handler.setFormatter(_formatter)
        _handler.setLevel(level)
        _logger.addHandler(_handler)
        _logger.propagate = propagate
    return _logger


def _format_args(args):
    return ", ".join(("'" + str(arg) + "'" for arg in args))


def _format_kwargs(kwargs):
    return str(kwargs).replace("{", "").replace("}", "").replace(": ", "=")


def _format_arguments(args, kwargs):
    arguments = ""
    if args:
        arguments += _format_args(args)
    if kwargs:
        if args:
            arguments += ", "
        arguments += _format_kwargs(kwargs)
    return arguments


def _escape(string):
    return string.replace(
        "\n", "").replace(
        "\r", "").replace(
        "'", "&apos;").replace(
        '"', "&quot;")


class logged(object):
    def __init__(self, name="mast"):
        self.name = name

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwargs):
            logger = make_logger(self.name)
            arguments = _format_arguments(args, kwargs)

            logger.info(
                "Attempting to execute {}({})".format(
                    func.__name__, arguments))
            try:
                result = func(*args, **kwargs)
            except:
                logger.exception(
                    "An unhandled exception occurred while "
                    "attempting to execute {}({})".format(
                        func.__name__, arguments))
                raise
            _result = _escape(repr(result))
            msg = "Finished execution of {}({}). Result: {}".format(
                func.__name__,
                arguments,
                _result)
            logger.info(msg)

            return result
        return inner

logger = make_logger("mast")
dp_logger = make_logger("DataPower")
