"""
We try to support Windows so we can't use bash scripts.
"""

import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

# 1. Check python 3.11 is installed
print("Checking python 3.11 is installed...")
try:
    assert sys.version_info >= (3, 11)
    assert sys.version_info < (3, 12)
except AssertionError:
    print("Python 3.11 is required. Please install it.")
    sys.exit(1)

# check if pip is installed
if os.system("pip --version") != 0:
    print("pip is not installed. Please install it.")
    sys.exit(1)

# 2. Install packages
"""
"""


def pip_install_from_path(path):
    if os.system(f"pip install -e {path}") != 0:
        print(f"Failed to install {path}")
        sys.exit(1)

# required by update process
def pip_install_requests():
    if os.system(f"pip install requests") != 0:
        print(f"Failed to install requests")
        sys.exit(1)

print("Installing packages...")
pip_install_requests()
pip_install_from_path("topicsync")
pip_install_from_path("objectsync")
pip_install_from_path("backend")
pip_install_from_path("grapycal_builtin")
pip_install_from_path("grapycal_torch")


print("Installation complete. Run `python main.py` to start the server.")
