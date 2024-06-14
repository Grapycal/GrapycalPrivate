import os
import sys
import subprocess
import argparse
import importlib.util

parser = argparse.ArgumentParser()
parser.add_argument(
    "--launch",
    action="store_true",
    help="Launch grapycal after installation",
)
parser.add_argument(
    "--message",
    "-m",
    help="Message to show after installation",
)

orignal_cwd = os.getcwd()

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

# check the version of python command
try:
    output = subprocess.check_output("python --version", shell=True).decode("utf-8")
except subprocess.CalledProcessError:
    print(
        "python --version: Failed to run the command. Please check if Python is installed and the command is exactly `python`, not `python3` or something else."
    )
    sys.exit(1)
version = output.split()[1]
if (version.split(".")[0], version.split(".")[1]) != ("3", "11"):
    print(
        f"python --version: Expected Python 3.11.* but got {version}. Please install Python 3.11 and make sure the command is exactly `python`, not `python3` or something else."
    )
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


args = parser.parse_args()

print("Installing packages...")
pip_install_from_path("topicsync")
pip_install_from_path("objectsync")
pip_install_from_path("backend")
pip_install_from_path("extensions/grapycal_builtin")

# check any other extensions are installed, if so, install them of new version
extensions = os.listdir("extensions")
for ext_name in extensions:
    if ext_name in ["grapycal_builtin"]:
        continue
    if importlib.util.find_spec(ext_name) is None:
        print(f"Extension {ext_name} is not installed. Skipping...")
        continue
    ext_path = os.path.join("extensions", ext_name)
    if not os.path.isdir(ext_path):
        continue
    print(f"Installing extension {ext_name}...")
    pip_install_from_path(ext_path)

os.chdir(orignal_cwd)

if parser.parse_args().message:
    print(parser.parse_args().message)

if parser.parse_args().launch:
    os.execlp("grapycal", "grapycal", "run")
