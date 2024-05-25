# pyright: reportUnusedExpression=false
import argparse
import datetime
import json
import os
import shutil
import subprocess
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import dotenv

import toml

dotenv.load_dotenv()

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


class StepResult:
    def __init__(self, dir: Path):
        self.dir = dir

    def __mul__(self, other: "Step") -> "StepResult":
        """
        Apply the step to the result
        """
        return other(self.dir)

    def __add__(self, other: "StepResult") -> "StepResult":
        """
        Merge the result with another step result
        """
        iprint(f"Merging {self.dir} and {other.dir}")
        # first create a new folder
        dst = TMP_ROOT / f"__Add_{Step.count[StepResult]}/"
        Step.count[StepResult] += 1
        shutil.copytree(self.dir, dst)
        # then copy the other result into the new folder
        for f in other.dir.iterdir():
            if f.is_dir():
                shutil.copytree(f, dst / f.name)
            else:
                shutil.copy(f, dst / f.name)
        return StepResult(dst)


class Step:
    count = defaultdict(int)

    def _gen_tmp_dst(self) -> Path:
        tmp_dst = TMP_ROOT / f"{self.__class__.__name__}_{self.count[self.__class__]}"
        self.count[self.__class__] += 1
        return tmp_dst

    def __call__(self, src: str | Path) -> StepResult:
        """
        Put stuffs into dst
        """
        if isinstance(src, str):
            src = Path(src)

        tmp_dir = self._gen_tmp_dst()

        if not tmp_dir.exists():
            tmp_dir.mkdir(parents=True, exist_ok=True)

        with iprint.indent():
            iprint(f"Running {self.__class__.__name__} {src} -> {tmp_dir}")
            self.run(src, tmp_dir)

        return StepResult(tmp_dir)

    def run(self, src: Path, dst: Path) -> None:
        raise NotImplementedError


def From(src) -> StepResult:
    """
    Read from a source folder. Usually a pipeline starts with this.
    """
    return StepResult(src)


class To(Step):
    """
    Output the content to a real destination folder.
    Usually the last step in a pipeline.
    """

    def __init__(self, dst: str | Path):
        self.dst = dst

    def __call__(self, src: str | Path) -> StepResult:
        iprint(f"Running To: {src} -> {self.dst}")
        if isinstance(src, str):
            src = Path(src)
        dst = self.dst
        if isinstance(dst, str):
            dst = Path(dst)
        if not dst.exists():
            dst.mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_dir():
                shutil.copytree(f, dst / f.name)
            else:
                shutil.copy(f, dst / f.name)
        return StepResult(dst)


class ToRelative(Step):
    """
    Put all content into a subfolder. For example:

    ### before:
    ```
    a.txt
    b.txt
    ```
    ### after:
    ```
    subfolder/
        a.txt
        b.txt
    ```
    """

    def __init__(self, subfolder: str | Path):
        self.subfolder = subfolder

    def run(self, src: Path, dst: Path):
        if not (dst / self.subfolder).exists():
            (dst / self.subfolder).mkdir(parents=True, exist_ok=True)
        for f in src.iterdir():
            if f.is_dir():
                iprint(f"copying {f} to {dst / self.subfolder / f.name}")
                shutil.copytree(f, dst / self.subfolder / f.name)
            else:
                iprint(f"copying {f} to {dst / self.subfolder}")
                shutil.copy(f, dst / self.subfolder / f.name)


@dataclass
class PyarmorConfig:
    expire_date: str | None = None
    platform: str | None = None
    prefix: str | None = None
    no_runtime: bool = False

    def copyWith(
        self,
        expire_date: str | None = None,
        platform: str | None = None,
        prefix: str | None = None,
        no_runtime: bool | None = None,
    ):
        return PyarmorConfig(
            expire_date=expire_date if expire_date else self.expire_date,
            platform=platform if platform else self.platform,
            prefix=prefix if prefix else self.prefix,
            no_runtime=no_runtime if no_runtime != None else self.no_runtime,
        )


class Select(Step):
    """
    Select a single file or folder from the source folder.
    """

    def __init__(self, name: str):
        self.name = name

    def run(self, src: Path, dst: Path):
        if (src / self.name).is_dir():
            shutil.copytree(src / self.name, dst / self.name)
        else:
            shutil.copy(src / self.name, dst / self.name)


class Pyarmor(Step):
    def __init__(
        self,
        config: PyarmorConfig | None = None,
    ):
        if config is None:
            config = PyarmorConfig()
        self.config = config

    def run(self, src: Path, dst: Path):
        # the actual src is the child of the src folder
        src = src.iterdir().__next__()
        command = f"pyarmor gen --recursive -i {src} -O {dst}"
        if self.config.prefix:
            command += f" --prefix {self.config.prefix}"
        if self.config.expire_date:
            command += f" -e {self.config.expire_date} "
        if self.config.platform:
            command += f" --platform {self.config.platform} "
        command += " > ../pyarmor.log 2>&1"

        cmd(command)

        if self.config.no_runtime:
            iprint("no_runtime: True")
            runtime_path = dst / "grapycal"
            iprint(f"removing: {runtime_path}")
            shutil.rmtree(runtime_path)
        else:
            iprint("no_runtime: False")

        # do not obfuscate entry folder
        if (dst / src.name / "entry").exists():
            shutil.rmtree(dst / src.name / "entry")
            shutil.copytree(src / "entry", dst / src.name / "entry")


class PackPythonPackage(Step):
    def __init__(
        self,
        edition: str,
        package_src_dir: Path | str = ".",
        pyarmor_config: PyarmorConfig | None = None,
    ):
        self.edition = edition
        self.package_src_dir = Path(package_src_dir)
        self.pyarmor_config = pyarmor_config

    def run(self, src: Path, dst: Path):
        x = From(src / self.package_src_dir.parent) * Select(self.package_src_dir.name)
        if self.edition in ["demo", "full"]:
            x *= AddLicenseCheckCode()
        x * Pyarmor(self.pyarmor_config) * To(dst / self.package_src_dir.parent)

        From(src) * Select("pyproject.toml") * To(dst)


class PackFrontend(Step):
    def run(self, src: Path, dst: Path):
        python = shutil.which("python")
        if not python:
            raise Exception("Python not found")
        cmd(f"{python} scripts/build_frontend.py")
        From("frontend/dist") * To(dst)


class PackGrapycal(Step):
    def __init__(
        self,
        edition: str,
        name: str = "grapycal",
        pyarmor_config: PyarmorConfig | None = None,
    ):
        self.edition = edition
        self.name = name
        self.pyarmor_config = pyarmor_config

    def run(self, src: Path, dst: Path):
        (
            From(src / "backend")
            * PackPythonPackage(
                edition=self.edition,
                package_src_dir="src/grapycal",
                pyarmor_config=self.pyarmor_config.copyWith(no_runtime=False),
            )
            * ToRelative("backend")
            + From(src / "submodules/topicsync")
            * PackPythonPackage(
                edition=self.edition,
                package_src_dir="src/topicsync",
                pyarmor_config=self.pyarmor_config.copyWith(prefix="grapycal"),
            )
            * ToRelative("topicsync")
            + From(src / "submodules/objectsync")
            * PackPythonPackage(
                edition=self.edition,
                package_src_dir="src/objectsync",
                pyarmor_config=self.pyarmor_config.copyWith(prefix="grapycal"),
            )
            * ToRelative("objectsync")
            + From(src / "extensions/grapycal_builtin")
            * PackPythonPackage(
                edition=self.edition,
                package_src_dir="grapycal_builtin",
                pyarmor_config=self.pyarmor_config.copyWith(prefix="grapycal"),
            )
            * ToRelative("grapycal_builtin")
            + From(src / "extensions/grapycal_torch")
            * PackPythonPackage(
                edition=self.edition,
                package_src_dir="grapycal_torch",
                pyarmor_config=self.pyarmor_config.copyWith(prefix="grapycal"),
            )
            * ToRelative("grapycal_torch")
            + From(src / "frontend") * PackFrontend() * ToRelative("frontend")
            + From(src / "packaging/template")
        ) * To(dst)

        if self.edition in ["cloud"]:
            From(src) * Select("lab.Dockerfile") * To(dst)

        json.dump(
            {
                "build_name": build_name,
                "version": version,
                "expire_date": expire_date,
                "platform": platform,
                "nts": nts,
            },
            open(dst / "build_info.json", "w"),
        )


class Zip(Step):
    def __init__(
        self,
        name: str = "archive",
    ):
        self.name = name

    def run(self, src: Path, dst: Path):
        shutil.make_archive(str(dst / self.name), "zip", src)


def insert_code_into_lines(lines, idx, code, indent):
    """
    Insert code into the lines at the given index
    """
    added_lines = code.split("\n")
    for i, line in enumerate(added_lines):
        added_lines[i] = " " * indent + line + "\n"
    lines = lines[:idx] + added_lines + lines[idx:]
    return lines


SIGNATURE_E = int(os.environ["SIGNATURE_E"])
SIGNATURE_N = int(os.environ["SIGNATURE_N"])

# TODO add more obfuscation maybe
check_license_code = f"""
try:
    import psutil

    import os
    import datetime
    import pathlib

    license_path = pathlib.Path(os.environ["GRAPYCAL_ROOT"]) / "license.json"
    from hashlib import sha512
    import json

    try:
        license = json.loads(open(license_path).read())
    except Exception:
        print("License not found or corrupted")
        exit(3)
    signature = int(license["signature"])
    license_data = license["license_data"]
    hash = int.from_bytes(
        sha512(json.dumps(license_data, sort_keys=True).encode()).digest(), "big"
    )

    hashFromSignature = pow(signature, {SIGNATURE_E}, {SIGNATURE_N - 45623} + 45623)
    if hash != hashFromSignature:
        print("Invalid license")
        exit(4)

    current_timestamp = int(datetime.datetime.now().timestamp())
    if license_data["expire_time"] < current_timestamp:
        print("License expired")
        exit(5)

    def get_ip_addresses(family):
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == family:
                    yield (interface, snic.address)

    try:
        macs = dict(get_ip_addresses(psutil.AF_LINK))
    except Exception:
        print("Error while getting mac addresses")
        exit(6)
    if len(macs) == 0:
        print("Error while getting mac addresses")
        exit(6)

    if set(license_data["mac_addresses"]) & set(macs.values()) == set():
        print("Invalid license")
        exit(4)

except Exception:
    print("Error while checking license")
    exit(1)

del license_path, sha512, license, signature, license_data, hash, hashFromSignature
"""


class AddLicenseCheckCode(Step):
    """
    Replaces the # ===CHECK_LICENSE=== # markers in the source code with the actual license check code
    """

    # TODO check mac address and time

    def run(self, src: Path, dst: Path):
        # copy src to dst to avoid modifying the original files
        From(src) * To(dst)
        # iterate over all .py files in the directory
        for f in dst.rglob("*.py"):
            with open(f, "r", encoding="utf-8") as file:
                print(f"Adding license check code to {f}")
                lines = file.readlines()

            # find the line with the license check code
            i = 0
            while i < len(lines):
                if "# ===CHECK_LICENSE=== #" in lines[i]:
                    indent = len(lines[i]) - len(lines[i].lstrip())
                    lines[i] = ""
                    # insert the license check code
                    lines = insert_code_into_lines(lines, i, check_license_code, indent)
                i += 1

            # write the modified lines back to the file
            with open(f, "w", encoding="utf-8") as file:
                file.writelines(lines)


# argument parsing

parser = argparse.ArgumentParser()
parser.add_argument("--nts", default="local")
parser.add_argument("--expire_date", default=None)
parser.add_argument("--expire_days", default=None, type=int)  # 6 months
parser.add_argument("--build_name", default=None)
parser.add_argument("--folder_name", default=None)
parser.add_argument("--edition", default="full", choices=["demo", "full", "cloud"])
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
    default="linux.x86_64",
)

args = parser.parse_args()

nts = args.nts

expire_days = args.expire_days or (90 if args.edition == "demo" else 100000)

expire_date = args.expire_date or (
    (datetime.datetime.now() + datetime.timedelta(days=expire_days)).strftime(
        "%Y-%m-%d"
    )
)
platform = args.platform
build_name = "+" + args.build_name if args.build_name else ""

version = toml.load("backend/pyproject.toml")["tool"]["poetry"]["version"]
build_name = f"grapycal-{version}{build_name}-{platform}"

if args.folder_name:
    folder_name = args.folder_name
else:
    folder_name = build_name

# end of argument parsing

# prepare running the pipeline

cmd(f"pyarmor cfg nts={nts}")

dst = Path("packaging/dist/" + folder_name)
if TMP_ROOT.exists():
    shutil.rmtree(TMP_ROOT)

if dst.exists():
    response = input(f"Destination {dst} already exists. Delete? [y/N]")
    if response.lower() != "y":
        exit(1)
    shutil.rmtree(dst)

# run the pipeline

From(".") * PackGrapycal(
    edition=args.edition,
    name=build_name,
    pyarmor_config=PyarmorConfig(
        expire_date=expire_date, platform=platform, no_runtime=True
    ),
) * To(dst / build_name) * Zip(name=build_name) * To(dst)


shutil.rmtree(TMP_ROOT)
