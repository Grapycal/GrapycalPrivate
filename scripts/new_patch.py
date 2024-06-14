#!python
import subprocess
import sys
from bump import bump_and_commit


def cmd(command: str):
    ret = subprocess.run(  # forward the stdout and stderr to the parent process
        command,
        shell=True,
    )
    if ret.returncode != 0:
        raise Exception(f"Command failed: {command}")


def get_current_version():
    with open("backend/pyproject.toml", "r") as f:
        for line in f:
            if "version" in line:
                return line.split("=")[1].strip().strip('"')
    raise Exception("Could not find version number in backend/pyproject.toml")


def new_patch():
    old_version = get_current_version()
    new_version = sys.argv[1]
    bump_and_commit(old_version, new_version)
    cmd(f"git tag v{new_version}")
    cmd("git push")
    cmd(f"git push origin v{new_version}")


if __name__ == "__main__":
    assert len(sys.argv) == 2, "Usage: new_patch.py <new_version>"
    new_patch()
