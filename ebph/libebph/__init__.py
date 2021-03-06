import os
from bcc import USDT
import ctypes as ct
from ctypes.util import find_library
from typing import get_type_hints, List, Any

from ebph import defs
from ebph.logger import get_logger

logger = get_logger()

libebph = ct.CDLL(defs.LIBEBPH, use_errno=True)

usdt_context = USDT(pid=os.getpid())

def command(func):
    """
    A decorator that allows a function to provide an interface into a libebph
    command of the same name. Types are determined using Python type hints.
    """
    name = func.__name__
    th = get_type_hints(func)
    argtypes = [v for k, v in th.items() if k != 'return']
    try:
        restype = th['return']
    except KeyError:
        restype = None
    @staticmethod
    def wrapper(*args, **kwargs):
        return getattr(libebph, name)(*args, **kwargs)
    getattr(libebph, name).argtypes = argtypes
    getattr(libebph, name).restype = restype
    logger.info(f'Registering USDT probe {name} -> command_{name}...')
    logger.debug(f'name={name}, argtypes={argtypes}, restype={restype}')
    usdt_context.enable_probe_or_bail(name, 'command_' + name)
    return wrapper

class Lib:
    """
    Exports libebph commands, inferring ctypes argtypes and restypes
    using Python type hints. All @command methods are static methods.
    """
    usdt_context = usdt_context

    @command
    def set_setting(key: ct.c_int, value: ct.c_uint64) -> ct.c_int:
        pass

    @command
    def normalize_profile(profile_key: ct.c_uint64) -> ct.c_int:
        pass

    @command
    def normalize_process(pid: ct.c_uint32) -> ct.c_int:
        pass

    @command
    def sensitize_profile(profile_key: ct.c_uint64) -> ct.c_int:
        pass

    @command
    def sensitize_process(pid: ct.c_uint32) -> ct.c_int:
        pass

    @command
    def tolerize_profile(profile_key: ct.c_uint64) -> ct.c_int:
        pass

    @command
    def tolerize_process(pid: ct.c_uint32) -> ct.c_int:
        pass

    @command
    def bootstrap_process(profile_key: ct.c_uint64, pid: ct.c_uint32, tgid: ct.c_uint32, pathname: ct.c_char_p) -> ct.c_int:
        pass

