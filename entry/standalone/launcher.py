"""
Acts as a parent process to the workspace process (run.py). It handles the SIGINT signal and opens another workspace process when
the user wants to open another workspace.
"""

import os
import signal
import subprocess
import sys
import time

from args import parse_args


def sigint_handler(signum, frame):
    print("SIGINT received, closing server")
    server.terminate()


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))

    workspace_file = None

    args = parse_args()
    if args.file is not None:
        workspace_file = os.path.abspath(args.file)
        argv = sys.argv[1:-1]
    else:
        argv = sys.argv[1:]

    while True:
        # Run the server
        server = subprocess.Popen(
            ["python", os.path.join(here, "run.py")] + argv + [workspace_file]
            if workspace_file is not None
            else [],
        )

        if os.name == "nt":
            # If Windows, capture SIGINT and close the server with SIGTERM because SIGINT is used for interrupting the runner on Windows
            signal.signal(signal.SIGINT, sigint_handler)
        else:
            # If Unix, just wait for the server to finish
            signal.signal(signal.SIGINT, sigint_handler)

        # this while loop is necessary to catch the SIGINT in Windows. Not sure why.
        while server.poll() is None:
            time.sleep(3.14159265359)

        # Wait for the server to finish
        server.wait()

        path = os.path.join(here, "_grapycal_open_another_workspace.txt")
        if os.path.exists(path):
            with open(path) as f:
                workspace_file = f.read().strip()
            os.remove(path)
        else:
            break
