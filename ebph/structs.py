"""
    ebpH (Extended BPF Process Homeostasis)  A host-based IDS written in eBPF.
    ebpH Copyright (C) 2019-2020  William Findlay
    pH   Copyright (C) 1999-2003 Anil Somayaji and (C) 2008 Mario Van Velzen

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

    Defines several structs and enums for interacting with the BPF program.

    2020-Jul-13  William Findlay  Created this.
"""

import os
import sys
from pprint import pformat
import ctypes as ct
from enum import IntEnum, IntFlag, unique, auto
from typing import List, Dict

from bcc import BPF

from ebph.logger import get_logger
from ebph import defs

logger = get_logger()


def calculate_profile_magic() -> int:
    """
    Calculate the magic number that corresponds to ebpH profiles.
    """
    from hashlib import sha256
    from ebph.version import __version__

    # take x.x part of version
    version = '.'.join(__version__.split('.')[:2]).encode('ascii')

    return int(sha256(version).hexdigest(), 16) & 0xFFFF_FFFF_FFFF_FFFF


@unique
class EBPH_PROFILE_STATUS(IntFlag):
    """
    The status of an ebpH profile.
    Warning: Keep in sync with BPF program.
    """
    TRAINING = 0x1
    FROZEN = 0x2
    NORMAL = 0x4


@unique
class EBPH_SETTINGS(IntEnum):
    """
    The various settings that may be changed within the BPF program.
    Warning: Keep in sync with BPF program.
    """
    MONITORING = 0
    LOG_SEQUENCES = auto()
    NORMAL_WAIT = auto()
    NORMAL_FACTOR = auto()
    NORMAL_FACTOR_DEN = auto()
    ANOMALY_LIMIT = auto()
    TOLERIZE_LIMIT = auto()
    ENFORCING = auto()

@unique
class EBPH_LSM(IntEnum):
    """
    The various LSM programs that ebpH tracks.
    Warning: Keep in sync with BPF program.
    """
    BPRM_CHECK_SECURITY = 0
    TASK_ALLOC = auto()
    TASK_FREE = auto()
    TASK_SETPGID = auto()
    TASK_GETPGID = auto()
    TASK_GETSID = auto()
    TASK_SETNICE = auto()
    TASK_SETIOPRIO = auto()
    TASK_GETIOPRIO = auto()
    TASK_PRLIMIT = auto()
    TASK_SETRLIMIT = auto()
    TASK_SETSCHEDULER = auto()
    TASK_GETSCHEDULER = auto()
    TASK_MOVEMEMORY = auto()
    TASK_KILL = auto()  # TODO: split this into coarse signal categories
    TASK_PRCTL = auto()
    SB_STATFS = auto()
    SB_MOUNT = auto()
    SB_REMOUNT = auto()
    SB_UMOUNT = auto()
    SB_PIVOTROOT = auto()
    MOVE_MOUNT = auto()
    INODE_CREATE = auto()
    INODE_LINK = auto()
    INODE_SYMLINK = auto()
    INODE_MKDIR = auto()
    INODE_RMDIR = auto()
    INODE_MKNOD = auto()
    INODE_RENAME = auto()
    INODE_READLINK = auto()
    INODE_FOLLOW_LINK = auto()
    INODE_PERMISSION = auto()  # TODO: split this into READ, WRITE, APPEND, EXEC
    INODE_SETATTR = auto()
    INODE_GETATTR = auto()
    INODE_SETXATTR = auto()
    INODE_GETXATTR = auto()
    INODE_LISTXATTR = auto()
    INODE_REMOVEXATTR = auto()
    FILE_PERMISSION = auto()  # TODO: split this into READ, WRITE, APPEND, EXEC
    FILE_IOCTL = auto()
    MMAP_ADDR = auto()
    MMAP_FILE = auto()
    FILE_MPROTECT = auto()
    FILE_LOCK = auto()
    FILE_FCNTL = auto()
    FILE_SEND_SIGIOTASK = auto()
    FILE_RECEIVE = auto()
    UNIX_STREAM_CONNECT = auto()
    UNIX_MAY_SEND = auto()
    SOCKET_CREATE = auto()
    SOCKET_SOCKETPAIR = auto()
    SOCKET_BIND = auto()
    SOCKET_CONNECT = auto()
    SOCKET_LISTEN = auto()
    SOCKET_ACCEPT = auto()
    SOCKET_SENDMSG = auto()
    SOCKET_RECVMSG = auto()
    SOCKET_GETSOCKNAME = auto()
    SOCKET_GETPEERNAME = auto()
    SOCKET_GETSOCKOPT = auto()
    SOCKET_SETSOCKOPT = auto()
    SOCKET_SHUTDOWN = auto()
    TUN_DEV_CREATE = auto()
    TUN_DEV_ATTACH = auto()
    KEY_ALLOC = auto()
    KEY_FREE = auto()
    KEY_PERMISSION = auto()  # TODO: maybe split this into operations
    IPC_PERMISSION = auto()
    MSG_QUEUE_ASSOCIATE = auto()
    MSG_QUEUE_MSGCTL = auto()
    MSG_QUEUE_MSGSND = auto()
    MSG_QUEUE_MSGRCV = auto()
    SHM_ASSOCIATE = auto()
    SHM_SHMCTL = auto()
    SHM_SHMAT = auto()
    PTRACE_ACCESS_CHECK = auto()
    PTRACE_TRACEME = auto()
    CAPGET = auto()
    CAPSET = auto()
    CAPABLE = auto()
    QUOTACTL = auto()
    QUOTA_ON = auto()
    SYSLOG = auto()
    SETTIME = auto()
    VM_ENOUGH_MEMORY = auto()
    BPF = auto()
    BPF_MAP = auto()
    BPF_PROG = auto()
    PERF_EVENT_OPEN = auto()
    LSM_MAX = auto()  # This must always be the last entry

    @staticmethod
    def get_name(num: int) -> str:
        try:
            return EBPH_LSM(num).name.lower()
        except ValueError:
            return 'empty'


NUM_LSM = int(EBPH_LSM.LSM_MAX)

class EBPHProfileDataStruct(ct.Structure):
    """
    Represents userspace's view of profile data.
    Warning: Keep in sync with BPF program.
    """
    _fields_ = (
        (
            'flags',
            ct.c_uint8 * ((NUM_LSM * NUM_LSM) & sys.maxsize),
        ),
    )

    def __eq__(self, other):
        try:
            self_len = len(self.flags)
            other_len = len(other.flags)
            assert self_len == other_len
            for i in range(self_len):
                assert self.flags[i] == other.flags[i]
        except Exception:
            return False
        return True


class EBPHProfileStruct(ct.Structure):
    """
    Represents userspace's view of the profile structure and its data.
    Warning: Keep in sync with BPF program.
    """
    _fields_ = (
        ('magic', ct.c_uint64),
        ('profile_key', ct.c_uint64),
        ('status', ct.c_uint8),
        ('anomaly_count', ct.c_uint64),
        ('train_count', ct.c_uint64),
        ('last_mod_count', ct.c_uint64),
        ('sequences', ct.c_uint64),
        ('normal_time', ct.c_uint64),
        ('count', ct.c_uint64),
        ('train', EBPHProfileDataStruct),
        ('test', EBPHProfileDataStruct),
        ('exe', ct.c_char * defs.PATH_MAX),
    )

    def __eq__(self, other: 'EBPHProfileDataStruct') -> bool:
        try:
            assert self.profile_key == other.profile_key
            assert self.status == other.status
            assert self.anomaly_count == other.anomaly_count
            assert self.train_count == other.train_count
            assert self.last_mod_count == other.last_mod_count
            assert self.sequences == other.sequences
            assert self.normal_time == other.normal_time
            assert self.count == other.count
            assert self.exe == other.exe
        except Exception:
            return False
        return True


    def _asdict(self) -> dict:
        return {field[0]: getattr(self, field[0]) for field in self._fields_}

    def __str__(self) -> str:
        return pformat((self.__class__.__name__, self._asdict()))

    @classmethod
    def from_bpf(cls, bpf: BPF, exe: bytes, profile_key: int,) -> 'EBPHProfileStruct':
        """
        Create a new profile structure from the BPF program, its exe name
        (in bytes), and its key.
        """
        profile = EBPHProfileStruct()
        profile.magic = calculate_profile_magic()
        profile.profile_key = profile_key
        profile.exe = exe

        try:
            bpf_profile = bpf['profiles'][ct.c_uint64(profile_key)]
        except (KeyError, IndexError):
            raise KeyError('Profile does not exist in BPF map')

        profile.status = bpf_profile.status
        profile.anomaly_count = bpf_profile.anomaly_count
        profile.train_count = bpf_profile.train_count
        profile.last_mod_count = bpf_profile.last_mod_count
        profile.sequences = bpf_profile.sequences
        profile.normal_time = bpf_profile.normal_time
        profile.count = bpf_profile.count

        try:
            # Look up value
            train = bpf['training_data'][ct.c_uint64(profile_key)]
            # Copy values over
            if not ct.memmove(ct.addressof(profile.train), ct.addressof(train), ct.sizeof(profile.train)):
                raise RuntimeError('Failed to memmove training data!')
        except (KeyError, IndexError):
            pass

        try:
            # Look up value
            test = bpf['testing_data'][ct.c_uint64(profile_key)]
            # Copy values over
            if not ct.memmove(ct.addressof(profile.test), ct.addressof(test), ct.sizeof(profile.test)):
                raise RuntimeError('Failed to memove testing data!')
        except (KeyError, IndexError):
            pass

        return profile

    def load_into_bpf(self, bpf: BPF) -> None:
        """
        Load a profile into the BPF program.
        """
        # Get leaf
        bpf_profile = bpf['profiles'].Leaf()
        # Set values
        bpf_profile.status = self.status
        bpf_profile.anomaly_count = self.anomaly_count
        bpf_profile.train_count = self.train_count
        bpf_profile.last_mod_count = self.last_mod_count
        bpf_profile.sequences = self.sequences
        bpf_profile.normal_time = self.normal_time
        bpf_profile.count = self.count
        # Update map
        bpf['profiles'][ct.c_uint64(self.profile_key)] = bpf_profile

        # Get leaf
        train = bpf['training_data'].Leaf()
        # Copy values over
        if not ct.memmove(ct.addressof(train), ct.addressof(self.train), ct.sizeof(self.train)):
            raise RuntimeError('Failed to memmove training data!')
        # Update map
        bpf['training_data'][ct.c_uint64(self.profile_key)] = train

        # Get leaf
        test = bpf['testing_data'].Leaf()
        # Copy values over
        if not ct.memmove(ct.addressof(test), ct.addressof(self.test), ct.sizeof(self.test)):
            raise RuntimeError('Failed to memmove testing data!')
        # Update map
        bpf['testing_data'][ct.c_uint64(self.profile_key)] = test
