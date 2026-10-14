# /// script
# requires-python = ">=3.12"
# dependencies = ["remotezip>=0.12"]
# ///
"""Download one file from inside a zip on a web server, without downloading the zip.

    uv run scripts/zip_member.py URL MEMBER OUTPUT

Reads the zip's directory and then only that file's bytes, with HTTP range requests.
GEBCO's zip is 4.2 GB and its server is slow and sometimes drops a long download; the
quarter of it we need is 0.5 GB compressed. A dropped transfer is retried from the start
of the file, a few times.
"""

import os
import shutil
import sys
import time

import remotezip

url, member, output = sys.argv[1:4]
for attempt in range(1, 6):
    try:
        with remotezip.RemoteZip(url) as z, z.open(member) as src, open(output + ".part", "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        os.replace(output + ".part", output)
        break
    except Exception as e:  # a dropped connection, or a corrupt read that fails its CRC
        print(f"attempt {attempt} failed: {e}", file=sys.stderr)
        if attempt == 5:
            raise
        time.sleep(30 * attempt)
