#! /usr/bin/env python3

# ebpH --  Monitor syscall sequences and detect anomalies
# Copyright 2019 Anil Somayaji (soma@scs.carleton.ca) and
# William Findlay (williamfindlay@cmail.carleton.ca)
#
# Based on Sasha Goldshtein's syscount
#  https://github.com/iovisor/bcc/blob/master/tools/syscount.py
#  Copyright 2017, Sasha Goldshtein.
# And on Anil Somayaji's pH
#  http://people.scs.carleton.ca/~mvvelzen/pH/pH.html
#  Copyright 2003 Anil Somayaji
#
# USAGE: ebpH.py <COMMAND>
#
# Licensed under MIT License

from time import sleep, strftime
import argparse
import textwrap
import errno
import itertools
import sys
import signal
import os
from bcc import BPF
from bcc.utils import printb
from bcc.syscall import syscall_name, syscalls
import ctypes as ct
from pprint import pprint

# signal handler
def signal_ignore(signal, frame):
    print()

def handle_errno(errstr):
    try:
        return abs(int(errstr))
    except ValueError:
        pass

    try:
        return getattr(errno, errstr)
    except AttributeError:
        raise argparse.ArgumentTypeError("couldn't map %s to an errno" % errstr)

def print_sequences(seqlen):
    # fetch BPF hashmap
    seq_hash = bpf["seq"]

    # print system time
    print()
    print("[%s]" % strftime("%H:%M:%S %p"))

    # print sequence for each inspected process
    for p, s in seq_hash.items():
        pid = p.value >> 32
        names = map(syscall_name, s.seq);
        calls = map(str, s.seq);

        # separator
        print()
        print("----------------------------------------------------------")
        print()

        # print the process and the sequence length
        print("%-8s %-8s" % ("PID","COUNT"))
        print("%-8s %-8s" % (pid, s.count));

        # list of sequences by "Call Name(Call Number),"
        print()
        print('Sequence:')
        arr = []
        for i,(call,name) in enumerate(zip(calls,names)):
            if i >= seqlen or i >= s.count:
                break;
            arr.append(f"{name.decode('utf-8')}({call})");
        print(textwrap.fill(", ".join(arr)))
        print()
    # clear the BPF hashmap
    seq_hash.clear()

# main control flow
if __name__ == "__main__":
    commands = ["start", "stop"]

    parser = argparse.ArgumentParser(description="Monitor system call sequences and detect anomalies.")
    #parser.add_argument("command", metavar="COMMAND", type=str.lower, choices=commands,
    #                    help="Command to run. Possible commands are %s." % ', '.join(commands))
    # TODO: implement this functionality (or perhaps remove it since it's only useful for testing)
    parser.add_argument("-p", "--pid", type=int, default=-1,
                        help="trace only the specified pid")
    parser.add_argument("-s", "--seqlen", type=int, default=8,
                        help="print call sequences of max length <seqlen>")
    # TODO: implement this functionality
    parser.add_argument("-l", "--lap", dest="lap", action="store_const", const=1, default=0,
                        help="use lookahead pairs instead of syscall sequences")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="write to a log file specified by <output>")
    args = parser.parse_args()

    # TODO: daemonize the process
    # TODO: use command to control daemonized process
    #command = args.command

    # read BPF embedded C from bpf.c
    with open("./bpf.c", "r") as f:
        text = f.read()

    # sub in args
    text = text.replace("ARG_SEQLEN", str(args.seqlen))
    text = text.replace("ARG_PID", str(args.pid))
    text = text.replace("ARG_LAP", str(args.lap))

    print(args)

    # compile ebpf code
    bpf = BPF(text=text)

    print("Tracing syscall sequences of length %s... Ctrl+C to quit." % args.seqlen)
    exiting = 0
    while True:
        # update the hashmap of sequences
        try:
            sleep(1)
        except KeyboardInterrupt: # handle exiting gracefully
            exiting = 1
            signal.signal(signal.SIGINT, signal_ignore)

        # exit control flow
        if exiting:
            # maybe redirect output
            if args.output is not None:
                sys.stdout = open(args.output,"w+")

            print_sequences(args.seqlen)

            # reset stdout
            if args.output is not None:
                sys.stdout.close()
                sys.stdout = sys.__stdout__

            print()
            print("Detaching...")
            exit()
