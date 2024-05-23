#!python

import subprocess
import sys


def cmd(command: str):
    ret = subprocess.run(  # forward the stdout and stderr to the parent process
        command,
        shell=True,
    )
    if ret.returncode != 0:
        raise Exception(f"Command failed: {command}")


class Scanner:
    def __init__(self, string) -> None:
        self.string: str = string
        self.index = 0

    def find_next(self, substr):
        index = self.string.find(substr, self.index)
        if index == -1:
            return None, None
        self.index = index + len(substr)
        return index, index + len(substr)


version_number_locations = [
    "backend/pyproject.toml|version =",
    "backend/src/grapycal/__init__.py|__version__ =",
    'electron/package.json|"version":',
    "electron/main.js|applicationVersion:",
    'electron/package.json|"version":',
    'electron/package-lock.json|"version":',
    'electron/package-lock.json|      "version":',
    'frontend/package.json|"version":',
    'frontend/package-lock.json|"version":',
    'frontend/package-lock.json|      "version":',
    "frontend/src/version.ts|export const LIB_VERSION",
]


def bump_version_number_in_file(file, prefix, new_version):
    with open(file, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        scanner = Scanner(line)
        p1, p2 = scanner.find_next(prefix)
        if p1 is None:
            continue
        lq1, lq2 = scanner.find_next('"')
        if lq1 is not None:
            rq1, rq2 = scanner.find_next('"')
            assert rq1 is not None, f"Could not find closing quote in {file}"
            lines[i] = line[:lq1] + f'"{new_version}"' + line[rq2:]
            break
        else:
            lq1, lq2 = scanner.find_next("'")
            assert lq1 is not None
            rq1, rq2 = scanner.find_next("'")
            assert rq1 is not None, f"Could not find closing quote in {file}"
            lines[i] = line[:lq1] + f"'{new_version}'" + line[rq2:]
            break
    else:
        raise Exception(f"Could not find version number in {file}")

    with open(file, "w") as f:
        f.writelines(lines)


def bump(new_version):
    for file_prefix in version_number_locations:
        file, prefix = file_prefix.split("|")
        bump_version_number_in_file(file, prefix, new_version)


def bump_and_commit(old_version, new_version):
    bump(new_version)
    cmd("git add .")
    cmd(f'git commit -m "bump: {old_version} -> {new_version}"')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: bump.py <version>")
        sys.exit(1)

    new_version = sys.argv[1]
    bump(new_version)
