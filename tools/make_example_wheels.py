#!/usr/bin/env python3
"""Build the two demo wheels in examples/in without pip or any build backend.

A wheel is just a zip with a METADATA/WHEEL/RECORD trio, so we can emit one
with the standard library. Run from the repository root:

    python3 tools/make_example_wheels.py
"""
import base64
import hashlib
import os
import sys
import zipfile

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "in")

V1 = '''"""demo_lib 1.0.0"""

def helper():
    return "helper-v1"

def parse_version(text):
    return text + ".0"

def classify(token):
    return "ok" if token else "empty"

def format_size(n):
    return "%d B" % n
'''

V2 = '''"""demo_lib 2.0.0"""

def parse_version(text):
    return int(text.split(".")[0])

def classify(token):
    if not token:
        raise ValueError("empty token")
    return "ok"

def format_size(n):
    return "%d byte" % n
'''


def wheel(name, version, source, path):
    dist = "%s-%s.dist-info" % (name, version)
    files = {"demo_lib/__init__.py": source.encode()}
    meta = (
        "Metadata-Version: 2.1\nName: %s\nVersion: %s\nSummary: demo wheel\n"
        "Requires-Python: >=3.8\n" % (name, version)
    ).encode()
    files["%s/METADATA" % dist] = meta
    files["%s/WHEEL" % dist] = (
        "Wheel-Version: 1.0\nGenerator: make_example_wheels\nRoot-Is-Purelib: true\nTag: py3-none-any\n"
    ).encode()
    files["%s/top_level.txt" % dist] = b"demo_lib\n"

    def digest(data):
        return "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()

    record = "".join("%s,%s,%d\n" % (n, digest(d), len(d)) for n, d in sorted(files.items()))
    record += "%s/RECORD,,\n" % dist
    files["%s/RECORD" % dist] = record.encode()
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for n, d in sorted(files.items()):
            info = zipfile.ZipInfo(n, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, d)
    return path


def main():
    os.makedirs(OUT, exist_ok=True)
    a = wheel("demo-lib", "1.0.0", V1, os.path.join(OUT, "demo_lib-1.0.0-py3-none-any.whl"))
    b = wheel("demo-lib", "2.0.0", V2, os.path.join(OUT, "demo_lib-2.0.0-py3-none-any.whl"))
    for p in (a, b):
        print("%s  %d bytes" % (p, os.path.getsize(p)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
