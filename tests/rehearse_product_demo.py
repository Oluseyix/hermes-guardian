"""Scripted-input rehearsal of the real 80s demo; never fabricates output.
Run with the installed Hermes Python. Human video recording remains separate.
"""
import argparse
import os
from pathlib import Path
import pty
import re
import select
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from guardian.builder import EXAMPLE, RECIPE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--log',type=Path,required=True)
    args=parser.parse_args()
    master,slave=pty.openpty()
    command=[sys.executable,str(Path(__file__).with_name('product_integration.py')),'--source',str(args.source),'--demo']
    child=subprocess.Popen(command,stdin=slave,stdout=slave,stderr=slave)
    os.close(slave)
    output=b''; sent=set(); deadline=time.monotonic()+150
    try:
        while time.monotonic()<deadline:
            if select.select([master],[],[],0.5)[0]:
                try:chunk=os.read(master,65536)
                except OSError:break
                if not chunk:break
                output+=chunk
                for marker,reply in ((b'Describe permissions:',EXAMPLE), (b'Clarified instruction:',RECIPE), (b'Choice [o/s/a/D]:','o')):
                    if marker in output and marker not in sent:
                        os.write(master,(reply+'\n').encode());sent.add(marker)
                match=re.search(rb'Type exactly: (ACTIVATE [0-9a-f]{64})',output)
                if match and b'Confirmation:' in output and b'Confirmation:' not in sent:
                    os.write(master,match.group(1)+b'\n');sent.add(b'Confirmation:')
            if child.poll() is not None:break
        if child.poll() is None:child.terminate()
        code=child.wait(timeout=10)
    finally:
        os.close(master)
        if child.poll() is None:child.kill();child.wait()
    args.log.write_bytes(output)
    print(output.decode(errors='replace'))
    print('SCRIPTED REHEARSAL EXIT:',code,'ANSWERS:',len(sent))
    if code or len(sent)!=4:raise SystemExit(1)


if __name__=='__main__':main()
