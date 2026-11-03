#!/usr/bin/env python3
"""Exercise the production queue with fake MTProto, clock and storage adapters.

Requires a C++20 compiler; does not require Qt or contact Telegram. This checks
queue behavior, not compatibility with the real Qt/MTProto types or a full build.
"""
from pathlib import Path
import os
import subprocess
import tempfile

here = Path(__file__).resolve().parent
root = here.parents[2]
source = (root / 'Telegram/SourceFiles/export/export_api_wrap.cpp').read_text()
start = source.index('void ApiWrap::transcribeNextMessage()')
end = source.index('void ApiWrap::hydrateMessageDone(', start)
harness = (here / 'worker.cpp.in').read_text()
assert harness.count('// PRODUCTION_METHODS') == 1
harness = harness.replace('// PRODUCTION_METHODS', source[start:end])
with tempfile.TemporaryDirectory(prefix='telegram-transcription-test-') as tmp:
    cpp = Path(tmp) / 'worker.cpp'
    binary = Path(tmp) / 'worker'
    cpp.write_text(harness)
    subprocess.run([
        os.environ.get('CXX', 'clang++'), '-std=c++20', '-Wall', '-Wextra',
        '-Werror', '-Wno-deprecated-this-capture', '-Wno-sign-compare',
        '-I', str(root / 'Telegram/SourceFiles'), str(cpp), '-o', str(binary),
    ], check=True)
    subprocess.run([str(binary)], check=True)
