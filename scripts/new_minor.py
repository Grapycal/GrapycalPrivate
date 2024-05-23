#!python
import subprocess
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


def new_minor():
    old_version = get_current_version()
    major, minor, _ = old_version.split(".")
    new_version = f"{major}.{int(minor) + 1}.0"
    new_version_without_patch = f"{major}.{int(minor) + 1}"

    response = input(f"Creating a new minor release {new_version}. Continue? [Y/n] ")
    if response.lower() != "y" and response != "":
        print("Aborting")
        return

    # this trick avoids merge conflicts when merging the release branch back into main, if needed

    bump_and_commit(old_version, new_version)
    cmd(f"git branch release/{new_version_without_patch}")
    bump_and_commit(new_version, new_version + "+dev")
    cmd("git checkout release")


if __name__ == "__main__":
    new_minor()
