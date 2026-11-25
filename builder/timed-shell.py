#!/usr/bin/env python3
"""The shell make runs each recipe line with in a build (builder/build.sh): it runs the line
with /bin/sh, as make would, and adds a line of JSON to $BUILD_TIMING saying how long it
took, how much CPU and memory it used, and how it ended:

  {"start": …, "wall": 12.3, "user": 40.1, "sys": 2.0, "maxrss_mb": 900, "status": 0, "cmd": "…"}

`maxrss_mb` is the largest of the line's processes, not their sum. Make runs several lines at
once, so the lines are in the order they finished. Without BUILD_TIMING it only runs the line.
"""

import json
import os
import resource
import subprocess
import sys
import time

if __name__ == "__main__":
    args = ["/bin/sh", *sys.argv[1:]]
    path = os.environ.get("BUILD_TIMING")
    if not path:
        os.execv(args[0], args)
    start = time.time()
    status = subprocess.call(args)
    wall = time.time() - start
    used = resource.getrusage(resource.RUSAGE_CHILDREN)
    cmd = sys.argv[-1] if len(sys.argv) > 1 else ""
    line = json.dumps({
        "start": round(start, 3), "wall": round(wall, 2), "user": round(used.ru_utime, 2),
        "sys": round(used.ru_stime, 2), "maxrss_mb": used.ru_maxrss // 1024, "status": status, "cmd": cmd,
    }) + "\n"
    # One write to a file opened for appending, so lines from steps that end together don't mix.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)
    # A line killed by a signal ends as a shell's would, with 128 and the signal's number.
    sys.exit(128 - status if status < 0 else status)
