"""
This module provides two major objects:

1. __make_logger__: A function which will return a `logging.Logger`
instance which is configured with a
`logging.handlers.TimedRotatingFileHandler` handler. See [The functions documentation](#make_logger)
for more details
2. __logged__: A decorator which will log the execution of a function
including the arguments passed in along with the return value. See
[the decorators documentation](#logged) for more details.

Usage:

    :::python
    from mast.logging import make_logger, logged

    logger = make_logger("my_module")
    logger.info("Informational message")

    @logged("my_module.function_1")
    def function_1(args):
        do_something(args)

    function_1("some_value")
"""


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
    "'level'='%(levelname)s'",
    "'datetime'='%(asctime)s'",
    "'process_name'='%(processName)s'",
    "'pid'='%(process)d'",
    "'thread'='%(thread)d'",
    "'module'='%(module)s'",
    "'line'='%(lineno)d'",
    "'message'='%(message)s'"))


def make_logger(
        name,
        level=level,
        fmt=_format,
        filename=None,
        when=unit,
        interval=interval,
        propagate=propagate,
        backup_count=backup_count):
    """
    Returns an instance of logging.Logger configured with
    a [logging.handlers.TimedRotatingFileHandler](https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler)
    handler.

    Arguments passed to this function determine the format,
    level, filename, time unit, interval, backup count and
    whether to propagate messages to parent loggers (defined
    by dot seperated heirarchy ie in `mast.datapower`,
    `datapower` is a logger with a parent logger of mast).

    Parameters:

    * __name__ - Required. the name of the logger instance. This follows
    conventions mentioned [here](https://docs.python.org/2/library/logging.html#logger-objects)
    * __level__ - The logging level to listen for. Accepts an `int` or
    one of the logging modules convenience constants defined
    [here](https://docs.python.org/2/library/logging.html#logging-levels)
    * __fmt__ - The format of the log message, see
    [here](https://docs.python.org/2/library/logging.html#formatter-objects)
    and [here](https://docs.python.org/2/library/logging.html#logrecord-attributes)
    for more details
    * __filename__ - The filename to log to. Defaults to the name of the logger
    appended with `.log` in the `$MAST_HOME/var/log` directory or
    `$MAST_HOME/var/log/mastd` directory if running as `mastd`
    * __when__ - The time unit to use for rolling over the log file
    as detailed [here](https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler)
    * __interval__ - The number of time units to wait before rolling the
    log files as detailed [here](https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler)
    * __propagate__ - Whether to propagate log messages up the ancestry chain
    (ie. if you have a logger `mast.datapower`, and propagate is set to
    `False` messages sent to the this logger will not be propagated to the
    `mast` logger). See [here](https://docs.python.org/2/library/logging.html#logging.Logger.propagate)
    for more details.
    * __backup_count__ - The number of "rolled" log files to keep, see
    [here](https://docs.python.org/2/library/logging.handlers.html#timedrotatingfilehandler)
    for more details.

    Usage:

    To use this function in your scripts, you would import it and call this
    function like this:

        :::python
        from mast.logging import make_logger

        logger = make_logger("my_module")
        logger.info("informational message")
        logger.debug("debug message")
    """
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
    """
    This is a decorator which will accept an optional parameter,
    name, and make a logger with `mast.logging.make_logger` and
    log the execution of the decorated function including arguments
    passed in to the function and the return value.

    Parameters:

    * __name__ - The name of the logger to create or use, this also
    dictates the log filename.

    Usage:

        :::python
        from mast.logging import logged

        @logged("my_module")
        def function(arg1, arg2=None):
            do_something(arg1, arg2)

        function("value_1", "value_2")
    """
    def __init__(self, name="mast"):
        """
        __Initialization__: for internal use only.
        """
        self.name = name

    def __call__(self, func):
        """
        Called when this decorator is used to decorate a function
        or method. This is for internal use, you shouldn't need to
        call this in your code.
        """
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
