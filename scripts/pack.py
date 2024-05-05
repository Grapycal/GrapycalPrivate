import argparse
import os
import shutil
import subprocess
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import List

import toml

TMP_ROOT = Path("packaging/dist/tmp")


class IndentedPrint:
    def __init__(self, indent_length: int = 2):
        self.indent_length = indent_length
        self.current_indent = 0

    @contextmanager
    def indent(self):
        self.current_indent += self.indent_length
        yield
        self.current_indent -= self.indent_length

    def __call__(self, *args, **kwargs):
        print(" " * self.current_indent, *args, **kwargs)


iprint = IndentedPrint()


def cmd(command: str):
    iprint(f"> {command}")
    ret = subprocess.run(  # forward the stdout and stderr to the parent process
        command,
        shell=True,
    )
    if ret.returncode != 0:
        raise Exception(f"Command failed: {command}")


def pascale_to_snake(name: str) -> str:
    res = "".join([c if c.islower() else f"_{c.lower()}" for c in name])
    return res[1:] if res[0] == "_" else res


def run_pipeline(module: "Module", dst: Path | str):
    dst = Path(dst)
    if TMP_ROOT.exists():
        shutil.rmtree(TMP_ROOT)

    if dst.exists():
        response = input(f"Destination {dst} already exists. Delete? [y/N]")
        if response.lower() != "y":
            return
        shutil.rmtree(dst)

    child_dst = (
        TMP_ROOT / f"{module.__class__.__name__}_{Module.count[module.__class__]}"
    )
    Module.count[module.__class__] += 1
    child_dst.mkdir(parents=True, exist_ok=True)
    module._run(module.src, child_dst / module.subfolder)
    shutil.move(child_dst, dst)

    print("=" * 20)
    print(f"The result is in {dst}")
    shutil.rmtree(TMP_ROOT)


class Module:
    count = defaultdict(int)

    def __init__(
        self,
        parent: "Module|None" = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
    ):
        self.parent = parent
        self.src = Path(src)
        self.subfolder = Path(subfolder)

    def _run_child(self, child: "Module"):
        child_dst = (
            TMP_ROOT / f"{child.__class__.__name__}_{self.count[child.__class__]}"
        )
        self.count[child.__class__] += 1
        (child_dst / child.subfolder).mkdir(parents=True, exist_ok=True)
        child._run(self.src / child.src, child_dst / child.subfolder)
        return child_dst

    def __call__(self):
        return self.parent._run_child(self)

    def _run(self, src, dst: Path):
        """
        Put stuffs into dst
        """
        with iprint.indent():
            iprint(f"Running {self.__class__.__name__} {src} -> {dst}")
            results = self.run(src, dst)  # This could make some self._run_child calls
            if results is not None:
                for result in results:
                    for item in os.listdir(result):
                        iprint(f"Moving {result / item} -> {dst}")
                        shutil.move(result / item, dst)

    def run(self, src: Path, dst: Path) -> List[Path] | None:
        raise NotImplementedError


class Sequential(Module):
    def __init__(self, *modules):
        self.modules = modules

    def run(self, src: Path, dst: Path):
        for module in self.modules:
            src = module(src, dst)
        return src


class Combine(Module):
    def __init__(self, parent: Module | None = None, *paths):
        super().__init__(parent)
        self.paths = paths

    def run(self, src: Path, dst: Path):
        return self.paths


@dataclass
class PyarmorConfig:
    expire_date: str | None = None
    platform: str | None = None


class Pyarmor(Module):
    def __init__(
        self,
        parent: Module | None = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
        config: PyarmorConfig | None = None,
    ):
        super().__init__(parent, src, subfolder)
        if config is None:
            config = PyarmorConfig()
        self.config = config

    def run(self, src: Path, dst: Path):
        command = f"pyarmor gen --recursive -i {src} -O {dst}"
        if self.config.expire_date:
            command += f" -e {self.config.expire_date} "
        if self.config.platform:
            command += f" --platform {self.config.platform}"
        command += f"> {dst / 'pyarmor.log'} 2>&1"
        cmd(command)
        os.remove(dst / "pyarmor.log")


class Copy(Module):
    def run(self, src: Path, dst: Path):
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy(src, dst)


class PackPythonPackage(Module):
    def __init__(
        self,
        parent: Module | None = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
        src_dir: Path | str = ".",
        pyarmor_config: PyarmorConfig | None = None,
    ):
        super().__init__(parent, src, subfolder)
        self.src_dir = Path(src_dir)
        self.pyarmor_config = pyarmor_config

    def run(self, src: Path, dst: Path):
        return [
            Pyarmor(
                self, self.src_dir, self.src_dir.parent, config=self.pyarmor_config
            )(),
            Copy(self, "pyproject.toml")(),
        ]


class PackFrontend(Module):
    def run(self, src: Path, dst: Path):
        python = shutil.which("python")
        if not python:
            raise Exception("Python not found")
        cmd(f"{python} scripts/build_frontend.py")
        return [Copy(self, "frontend/dist")()]


class PackGrapycal(Module):
    def __init__(
        self,
        parent: Module | None = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
        name: str = "grapycal",
        pyarmor_config: PyarmorConfig | None = None,
    ):
        super().__init__(parent, src, subfolder)
        self.name = name
        self.pyarmor_config = pyarmor_config

    def run(self, src: Path, dst: Path):
        pack = Combine(
            self,
            PackPythonPackage(
                self,
                "backend",
                "backend",
                src_dir="src/grapycal",
                pyarmor_config=self.pyarmor_config,
            )(),
            PackPythonPackage(
                self,
                "submodules/topicsync",
                "topicsync",
                src_dir="src/topicsync",
                pyarmor_config=self.pyarmor_config,
            )(),
            PackPythonPackage(
                self,
                "submodules/objectsync",
                "objectsync",
                src_dir="src/objectsync",
                pyarmor_config=self.pyarmor_config,
            )(),
            PackPythonPackage(
                self,
                "extensions/grapycal_builtin",
                "grapycal_builtin",
                src_dir="grapycal_builtin",
                pyarmor_config=self.pyarmor_config,
            )(),
            PackPythonPackage(
                self,
                "extensions/grapycal_torch",
                "grapycal_torch",
                src_dir="grapycal_torch",
                pyarmor_config=self.pyarmor_config,
            )(),
            PackFrontend(self, subfolder="frontend")(),
            Copy(self, "entry/standalone", "entry")(),
            Copy(self, "packaging/template")(),
        )()
        return [Zip(self, pack, name=self.name)()]


class Zip(Module):
    def __init__(
        self,
        parent: Module | None = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
        name: str = "archive",
    ):
        super().__init__(parent, src, subfolder)
        self.name = name

    def run(self, src: Path, dst: Path):
        shutil.make_archive(str(dst / self.name), "zip", src)
        copied = Copy(self, subfolder=self.name)()
        return [copied]


parser = argparse.ArgumentParser()
parser.add_argument("--nts", default="local")
parser.add_argument("--expire_date", default=None)
parser.add_argument("--name", required=True)
parser.add_argument(
    "--platform",
    choices=[
        "windows.x86",
        "windows.x86_64",
        "linux.x86",
        "linux.x86_64",
        "linux.arm",
        "linux.armv6",
        "linux.armv7",
        "linux.aarch32",
        "linux.aarch64",
        "linux.ppc64",
        "darwin.x86_64",
        "darwin.aarch64",
    ],
    required=True,
)

args = parser.parse_args()

nts = args.nts
expire_date = args.expire_date
platform = args.platform
name = args.name

version = toml.load("backend/pyproject.toml")["tool"]["poetry"]["version"]
build_name = f"grapycal-{version}-{name}-{platform}"
cmd(f"pyarmor cfg nts={nts}")
run_pipeline(
    PackGrapycal(
        name=build_name,
        pyarmor_config=PyarmorConfig(expire_date=expire_date, platform=platform),
    ),
    dst="packaging/dist/" + build_name,
)

# create a symlink to the latest build
if Path("packaging/dist/latest").exists():
    os.remove("packaging/dist/latest")
os.symlink(build_name, "packaging/dist/latest")
