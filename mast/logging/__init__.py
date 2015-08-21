import logging
from functools import wraps
from logging.handlers import TimedRotatingFileHandler
from mast.config import get_configs_dict
from mast.timestamp import Timestamp
import os

mast_home = os.environ["MAST_HOME"] or os.getcwd()

config = get_configs_dict()
config = config["logging.conf"]

level = int(config["logging"]["level"])
filename = config['logging']['file']
dp_filename = filename.replace("mast", "DataPower")
filename = os.path.join(mast_home, filename)
dp_filename = os.path.join(mast_home, dp_filename)
filemode = "a"
_format = "level=%(levelname)s; datetime=%(asctime)s; process_name=%(processName)s; pid=%(process)d; thread=%(thread)d; message=%(message)s"


def make_logger(
        name,
        level=level,
        fmt=_format,
        filename=None,
        when="D",
        interval=1,
        propagate=False):
    logger = logging.getLogger("mast")
    logger.addHandler(logging.NullHandler())
    logger.info("received request for logger {}".format(name))

    _logger = logging.getLogger(name)
    if _logger.handlers:
        if name != "mast" or len(_logger.handlers) > 1:
            return _logger

    _logger.setLevel(level)
    _formatter = logging.Formatter(fmt)

    if not filename:
        logger.debug(
            "filename not provided for logger {}, generating...".format(name))
        _filename = "{}.log".format(name)
        _filename = os.path.join(
            mast_home,
            "var",
            "log",
            _filename)
        filename = _filename
        logger.debug("filename generated {}".format(filename))
    _handler = TimedRotatingFileHandler(filename, when=when, interval=interval)
    _handler.setFormatter(_formatter)
    _handler.setLevel(level)
    _logger.addHandler(_handler)
    _logger.propagate = propagate
    logger.debug("Finished building logger {}".format(name))
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
            msg = "Attempting to execute {}({})".format(func.__name__, arguments)            
            logger.info(msg)
            try:
                result = func(*args, **kwargs)
            except:
                logger.exception(
                    "An unhandled exception occurred while attempting to execute {}({})".format(
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

