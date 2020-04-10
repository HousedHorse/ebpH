#!/usr/bin/env python3

import os, sys
from distutils.core import setup

setup(name='ebpH',
      version='0.6.1',
      description='Extended BPF Process Homeostasis: Host-based anomaly detection in eBPF',
      author='William Findlay',
      author_email='william.findlay@carleton.ca',
      url='https://github.com/willfindlay/ebpH',
      packages=['ebpH'],
     )
