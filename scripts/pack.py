import os
import shutil
import subprocess
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path
from typing import List

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


class Pyarmor(Module):
    def __init__(
        self,
        parent: Module | None = None,
        src: Path | str = ".",
        subfolder: Path | str = ".",
        expire_date: str | None = None,
    ):
        super().__init__(parent, src, subfolder)
        self.expire_date = expire_date

    def run(self, src: Path, dst: Path):
        command = f"pyarmor gen --recursive -i {src} -O {dst}"
        if self.expire_date:
            command += f" -e {self.expire_date} "
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
        expire_date: str | None = None,
    ):
        super().__init__(parent, src, subfolder)
        self.src_dir = Path(src_dir)
        self.expire_date = expire_date

    def run(self, src: Path, dst: Path):
        return [
            Pyarmor(self, self.src_dir, self.src_dir.parent, self.expire_date)(),
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
        expire_date: str | None = None,
        name: str = "grapycal",
    ):
        super().__init__(parent, src, subfolder)
        self.expire_date = expire_date
        self.name = name

    def run(self, src: Path, dst: Path):
        pack = Combine(
            self,
            PackPythonPackage(
                self,
                "backend",
                "backend",
                src_dir="src/grapycal",
                expire_date=self.expire_date,
            )(),
            PackPythonPackage(
                self,
                "submodules/topicsync",
                "topicsync",
                src_dir="src/topicsync",
                expire_date=self.expire_date,
            )(),
            PackPythonPackage(
                self,
                "submodules/objectsync",
                "objectsync",
                src_dir="src/objectsync",
                expire_date=self.expire_date,
            )(),
            PackPythonPackage(
                self,
                "extensions/grapycal_builtin",
                "grapycal_builtin",
                src_dir="grapycal_builtin",
                expire_date=self.expire_date,
            )(),
            PackPythonPackage(
                self,
                "extensions/grapycal_torch",
                "grapycal_torch",
                src_dir="grapycal_torch",
                expire_date=self.expire_date,
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


build_name = "grapycal-0.11.3-240503-linux"
# cmd("pyarmor cfg nts=pool.ntp.org")  # set the time server
cmd("pyarmor cfg nts=local")
run_pipeline(
    PackGrapycal(expire_date="2024-11-01", name=build_name),
    dst="packaging/dist/" + build_name,
)
