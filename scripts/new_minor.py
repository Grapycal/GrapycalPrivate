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
    current_version = get_current_version()
    major, minor, _ = current_version.split(".")

    release_branch_name = f"release/v{major}.{minor}"
    release_version = f"{major}.{int(minor)}.0"
    release_tag = f"v{release_version}"

    new_main_branch_version = f"{major}.{int(minor) + 1}.0+dev"  # next minor version

    response = input(f"Creating a new minor release {release_tag}. Continue? [Y/n] ")
    if response.lower() != "y" and response != "":
        print("Aborting")
        return

    # this trick avoids merge conflicts when merging the release branch back into main, if needed

    cmd(f"git branch {release_branch_name}")
    bump_and_commit(current_version, new_main_branch_version)

    cmd(f"git checkout {release_branch_name}")
    # bump_and_commit(current_version, release_version)
    cmd(f"git push -u origin {release_branch_name}")


if __name__ == "__main__":
    new_minor()
