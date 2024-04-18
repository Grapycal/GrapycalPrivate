'''
run_server.py can run the server already, but it can't be ctrl+c'd because the keyboard interrupt is handled by the runner.
To fix this, we need to capture the SIGINT in this script and close the server with SIGTERM instead of SIGINT.
'''

import signal
import subprocess
import os, sys
import time

def sigint_handler(signum, frame):
    print("SIGINT received, closing server")
    server.terminate()

if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    # Run the server
    server = subprocess.Popen(['python', os.path.join(here, 'run.py')] + sys.argv[1:])
    # Capture SIGINT and close the server with SIGTERM
    signal.signal(signal.SIGINT, sigint_handler)

    # this while loop is necessary to catch the SIGINT in Windows. Not sure why.
    while server.poll() is None:
        time.sleep(3.14159265359)

    # Wait for the server to finish
    server.wait()