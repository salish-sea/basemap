# /// script
# requires-python = ">=3.12"
# dependencies = ["remotezip>=0.12", "requests>=2.32"]
# ///
"""Download one file from inside a zip on a web server, without downloading the zip.

    uv run scripts/zip_member.py URL MEMBER OUTPUT

Reads the zip's directory, then downloads only that file's compressed bytes with HTTP
range requests and decompresses them here. GEBCO's zip is 4.2 GB, and the quarter of it
we need is 0.5 GB compressed. Its server is slow and drops a long download every 15
minutes or so, so a dropped download is resumed from the last byte received, never
restarted, and only attempts that get nowhere count against the retries. The compressed
bytes are kept in OUTPUT.<crc>.zpart until they are complete, so even a run that fails
resumes on the next run. The result is checked against the zip's CRC.
"""

import glob
import os
import struct
import sys
import time
import zipfile
import zlib

import remotezip
import requests

ATTEMPTS = 10  # in a row without progress


def retrying(what, fn, progress=lambda: 0):
    failures, mark = 0, progress()
    while True:
        try:
            return fn()
        except Exception as e:  # a dropped connection, or the server's occasional 500
            if progress() > mark:  # a resumed download that got further is not a failure
                failures, mark = 0, progress()
            failures += 1
            print(f"{what}: attempt failed ({failures} in a row): {e}", file=sys.stderr)
            if failures == ATTEMPTS:
                raise
            time.sleep(min(30 * failures, 300))


def get_range(url, start, end):
    # Streamed, so a server that ignores the range and sends the whole zip is caught before
    # any of it is read.
    res = requests.get(url, headers={"Range": f"bytes={start}-{end}"}, timeout=60, stream=True)
    res.raise_for_status()
    if res.status_code != 206 or not res.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
        res.close()
        raise OSError(f"{url} answered {res.status_code} without the range requested, bytes {start}-{end}")
    return res


url, member, output = sys.argv[1:4]


def read_directory():
    with remotezip.RemoteZip(url) as z:
        return z.getinfo(member)


info = retrying("reading the zip's directory", read_directory)
if info.flag_bits & 1:
    raise SystemExit(f"{member} is encrypted")
if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
    raise SystemExit(f"{member} is compressed with method {info.compress_type}, which this can't read")
# Named for the member's checksum, so a partial download from another release of the
# zip is never resumed; any such leftover is deleted.
part = f"{output}.{info.CRC:08x}.zpart"
for stale in glob.glob(glob.escape(output) + ".*.zpart"):
    if stale != part:
        os.remove(stale)

# The compressed bytes follow the member's local header, whose name and extra field can
# differ in length from the directory's copy.
header = retrying("reading the member's header", lambda: get_range(url, info.header_offset, info.header_offset + 29).content)
if header[:4] != b"PK\x03\x04":
    raise SystemExit(f"no local header for {member} at byte {info.header_offset}")
name_len, extra_len = struct.unpack("<HH", header[26:30])
data_start = info.header_offset + 30 + name_len + extra_len
data_end = data_start + info.compress_size - 1


def have():
    return os.path.getsize(part) if os.path.exists(part) else 0


def fetch_rest():
    if have() > info.compress_size:
        os.remove(part)
    if have() == info.compress_size:
        return
    with get_range(url, data_start + have(), data_end) as res, open(part, "ab") as dst:
        for chunk in res.iter_content(1 << 16):  # small, so a drop loses little
            dst.write(chunk[:info.compress_size - dst.tell()])
            if dst.tell() == info.compress_size:
                break
    if have() < info.compress_size:
        raise OSError(f"the server stopped sending at {have()} of {info.compress_size} bytes")


retrying(f"downloading {member}", fetch_rest, have)


def inflate_into(path):
    crc, size = 0, 0
    inflate = zlib.decompressobj(-15) if info.compress_type == zipfile.ZIP_DEFLATED else None
    with open(part, "rb") as src, open(path, "wb") as dst:
        while chunk := src.read(1 << 20):
            data = inflate.decompress(chunk) if inflate else chunk
            crc, size = zlib.crc32(data, crc), size + len(data)
            dst.write(data)
        if inflate:
            data = inflate.flush()
            crc, size = zlib.crc32(data, crc), size + len(data)
            dst.write(data)
    return crc, size


try:
    crc, size = inflate_into(output + ".part")
except zlib.error as e:
    crc, size = None, str(e)
if (crc, size) != (info.CRC, info.file_size):
    os.remove(part)  # so the next run downloads it again rather than trusting it
    os.remove(output + ".part")
    raise SystemExit(f"{member} failed its check ({crc}, {size}); the zip says CRC {info.CRC:08x}, {info.file_size} bytes")
os.replace(output + ".part", output)
os.remove(part)
