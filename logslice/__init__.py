"""logslice — Fast time-bounded log file slicing.

Extracts lines from large log files whose timestamps fall within
a user-specified [start, end] range using binary search where
possible, without loading the entire file into memory.
"""

__version__ = "0.1.0"
__author__ = "logslice contributors"
