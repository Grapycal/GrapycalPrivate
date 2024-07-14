import argparse
from datetime import datetime
import json
import os
import pathlib
import subprocess
import threading
import time
from typing import Callable
import webbrowser
import psutil
import zipfile
from io import BytesIO
from pathlib import Path
import sys
import termcolor

CWD = os.getcwd()
HERE = pathlib.Path(__file__).parent
GRAPYCAL_ROOT = HERE.parent.parent.parent
os.environ["GRAPYCAL_ROOT"] = str(GRAPYCAL_ROOT)


class CmdSelector:
    def __init__(self, args, prefix=""):
        self.args = args
        self.prefix = prefix

    def select(
        self,
        mapping: dict[str | None, Callable[[], None] | Callable[["CmdSelector"], None]],
    ):
        if len(self.args) == 0 and None in mapping:
            return mapping[None]()  # type: ignore

        if len(self.args) > 0:
            cmd = self.args[0]
            if cmd in mapping:
                # if the function do not receive any argument, do not pass anything
                if mapping[cmd].__code__.co_argcount == 0:
                    return mapping[cmd]()  # type: ignore
                else:
                    return mapping[cmd](
                        CmdSelector(self.args[1:], self.prefix + " " + cmd)
                    )  # type: ignore

        keys = [
            key is not None and key or "" for key in mapping.keys()
        ]  # replace None with ""
        if len(self.args) > 0:
            print(f"Unknown command: {self.prefix} {self.args[0]}")
        print("Usage:")
        for key in keys:
            doc = mapping[key].__doc__
            if doc is None:
                doc = ""
            else:
                doc = ": " + doc.strip()
            print(f"  {self.prefix} {key} {doc}")

    def current(self):
        return self.args[0]

    def has_current(self):
        return len(self.args) > 0

    def next(self):
        return self.args[1]

    def has_next(self):
        return len(self.args) > 1


def pip_install_from_path(path):
    if os.system(f"pip install -e {path}") != 0:
        print(f"Failed to install {path}")
        sys.exit(1)


def input_colored(prompt):
    return input(termcolor.colored(prompt, "green"))


def update_if_needed():
    import requests

    RESOURCE_SERVER = "https://resource.grapycal.com"

    # login first
    try:
        session = requests.Session()
        session.post(
            f"{RESOURCE_SERVER}/token",
            data={"password": "demo:@J%^INTERACTIVITYcounts2hqw45"},
        )
    except Exception:
        print("Failed to check for updates. No internet connection.")
        return

    def build_info():
        current_version = ""
        platform = ""
        with open(GRAPYCAL_ROOT / "build_info.json") as build_info_file:
            build_info = json.load(build_info_file)
            current_version = build_info["version"]
            platform = build_info["platform"]

        return current_version, platform

    def version_url_to_version(url):
        return url.split("/")[-1].split("+")[0]

    def version_url_to_full_build_name(url):
        return url.split("/")[-1]

    def check_update():
        latest_url = f"{RESOURCE_SERVER}/latest/releases/demo"
        latest_version_url = session.get(latest_url).text.strip('" ')
        latest_version = version_url_to_version(latest_version_url)

        current_version, platform = build_info()

        # there will be a grapycal prefix in latest version
        if f"grapycal-{current_version}" == latest_version:
            return None

        print(
            f"Current version: grapycal-{current_version}, latest version: {latest_version}"
        )

        return f"{latest_version_url}-{platform}"

    def ask_update():
        while True:
            ans = input_colored(
                "Grapycal update available, download and install? (y/n) "
            )
            match ans:
                case "y" | "Y":
                    return True
                case "n" | "N":
                    return False
                case _:
                    print("Please input y or n")

    def download(url: str):
        response = session.get(url)
        return zipfile.ZipFile(
            BytesIO(response.content), compression=zipfile.ZIP_DEFLATED
        )

    def install(extract_path: Path):
        # notice that after the installer, PATH of grapycal is changed
        _, platform = build_info()
        if "windows" in platform:
            # in windows,
            os.execl(
                sys.executable,
                sys.executable,
                extract_path / "install.py",
                "--message",
                f'"Grapycal updated to {version_url_to_version(extract_path.name)}. Please start Grapycal with `grapycal run` command"',
            )
        else:
            os.execl(
                sys.executable, sys.executable, extract_path / "install.py", "--launch"
            )

    if download_url := check_update():
        need_update = ask_update()

        if need_update:
            print(f"Downloading {download_url}...")
            update_url = f"{RESOURCE_SERVER}/{download_url}.zip"
            pack_zip = download(update_url)

            new_grapycal_name = version_url_to_full_build_name(download_url)
            grapycal_parent = GRAPYCAL_ROOT.parent
            extract_path = grapycal_parent / new_grapycal_name
            print(f"Extracting to {extract_path}...")
            pack_zip.extractall(extract_path)

            # copy the license file
            if (GRAPYCAL_ROOT / "license.json").exists():
                Path(extract_path / "license.json").write_text(
                    (GRAPYCAL_ROOT / "license.json").read_text()
                )
            print("Installing...")
            install(extract_path)


def license_file_exists():
    return Path(GRAPYCAL_ROOT / "license.json").exists()


def license_file_valid():
    license_path = GRAPYCAL_ROOT / "license.json"
    license = json.loads(open(license_path).read())
    if license["license_data"]["expire_time"] < int(datetime.now().timestamp()):
        return False
    return True


def acquire_license():
    import requests

    # serial = input_colored("Please enter your serial number: ")
    serial = "2501dc76b11a43e3b2421803f4f1f660"  # demo serial number. no need to input

    def get_ip_addresses(family):
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == family:
                    yield snic.address

    macs = list(get_ip_addresses(psutil.AF_LINK))

    if len(macs) == 0:
        print("No MAC address found, please connect to a network to acquire license.")
        sys.exit(1)

    # do not accept too many mac addresses, otherwise the license would be abused
    macs = macs[:10]
    response = requests.post(
        "https://license.grapycal.com/license",
        json={"serial_number": serial, "mac_addresses": macs, "user_name": "demo"},
    )

    if response.status_code == 200:
        response = response.json()

        # Not need to print remaining uses for demo license
        # print(
        #     "License acquired successfully. Remaining uses: ",
        #     response["remaining_uses"],
        # )

        with open(GRAPYCAL_ROOT / "license.json", "w") as f:
            json.dump(response["license"], f)
    elif response.status_code == 403:
        print(
            "Invalid serial number. Maybe it has been used too many times, or it's invalid. If you believe this is an error, please contact us at grapycal@gmail.com"
        )
        sys.exit(1)
    else:  # error
        print(
            "Failed to acquire license, please try again.",
            response.status_code,
            response.text,
        )
        sys.exit(1)


def print_welcome(port):
    with open(GRAPYCAL_ROOT / "build_info.json") as build_info_file:
        build_info = json.load(build_info_file)
        version = build_info["version"]
    print(
        termcolor.colored(
            r"""
         ______                                  __
        / ____/________ _____  __  ___________ _/ /
       / / __/ ___/ __ `/ __ \/ / / / ___/ __ `/ /
      / /_/ / /  / /_/ / /_/ / /_/ / /__/ /_/ / /
      \____/_/   \__,_/ .___/\__, /\___/\__,_/_/
                     /_/    /____/
                                    """,
            "red",
        )
        + termcolor.colored("v" + version, "white")
    )

    print(
        "\nWelcome to Grapycal. Please go to "
        + termcolor.colored(f"http://localhost:{port}", "green")
        + " with Chrome to access the frontend.\n"
    )
    print("=" * 50)


def show_license_info():
    license_path = GRAPYCAL_ROOT / "license.json"
    license = json.loads(open(license_path).read())
    exp = datetime.fromtimestamp(license["license_data"]["expire_time"]).strftime(
        "%Y-%m-%d"
    )
    print(f"Current license is valid until {exp}.")


def run(cmds: CmdSelector):
    """
    Run Grapycal
    """

    parser = argparse.ArgumentParser(prog=cmds.prefix)
    parser.add_argument(
        "--port", type=int, default=7943, help="Port Grapycal will listen to"
    )
    parser.add_argument(
        "--host", type=str, default="localhost", help="Host Grapycal will listen to"
    )

    args = parser.parse_args(cmds.args)

    print("Checking for updates...")

    # if updated, this function will not return back
    update_if_needed()

    if not license_file_exists():
        print("License not found. Acquiring license...")
        acquire_license()

    if not license_file_valid():
        print("License expired. Acquiring new license...")
        acquire_license()

    show_license_info()

    def open_browser():
        time.sleep(4)
        webbrowser.open(f"http://localhost:{args.port}")

    threading.Thread(target=open_browser).start()

    while True:
        print_welcome(args.port)
        command = f'python {HERE/"entry/launcher.py"} --frontend-path {GRAPYCAL_ROOT/"frontend"} --port {args.port} --cwd {CWD} --host {args.host}'
        print(f"Running command: {command}")
        core_return_code = os.system(command)

        if core_return_code in [3, 4, 5]:
            acquire_license()
        else:
            break


def dev():
    """
    Development mode. Debug use only.
    """
    # python scripts/build_frontend.py
    os.system(f"python {GRAPYCAL_ROOT/'scripts/build_frontend.py'}")
    try:
        os.system(
            f'python {HERE/"entry/launcher.py"} --extensions-path {GRAPYCAL_ROOT/"extensions"} --frontend-path {GRAPYCAL_ROOT/"frontend/dist"} --port 7943 --cwd {CWD}'
        )
    except KeyboardInterrupt:
        pass


def ext(cmds: CmdSelector):
    """
    Extension management
    """

    def install_ext():
        if not cmds.has_next():
            print("Please specify the extension name.")
            available_exts = os.listdir(GRAPYCAL_ROOT / "extensions")
            print("Available extensions:")
            for ext in available_exts:
                if ext.startswith("grapycal_"):
                    print(f"  {ext[9:]}")
            return
        ext_name = cmds.next()
        if not ext_name.startswith("grapycal_"):
            ext_name = "grapycal_" + ext_name
        ext_name = ext_name.replace("-", "_")
        # check its dependency extensions are installed
        # read the extension's pyproject.toml
        ext_path = GRAPYCAL_ROOT / "extensions" / ext_name
        if not ext_path.exists():
            print(f"Extension {ext_name} not found.")
            return
        if (ext_path / "pyproject.toml").exists():
            with open(ext_path / "pyproject.toml") as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith("grapycal-"):
                        dep = line.split("=")[0].strip()
                        if (
                            subprocess.run(
                                f"pip show {dep}",
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                            ).returncode
                            != 0
                        ):
                            short_dep = dep[9:]
                            print(
                                f"Befor installing {ext_name}, please install {dep.replace('-','_')} first: `{termcolor.colored(f'grapycal ext install {short_dep}', 'green')}`"
                            )
                            return
                        else:
                            print(f"Dependency {dep} installed.")

        print(f"Installing extension {ext_name}...")
        pip_install_from_path(GRAPYCAL_ROOT / "extensions" / ext_name)
        print(f"Extension {ext_name} installed.")

    def uninstall_ext():
        if not cmds.has_next():
            print("Please specify the extension name.")
            return
        ext_name = cmds.next()
        if not ext_name.startswith("grapycal_"):
            ext_name = "grapycal_" + ext_name
        print(f"Uninstalling extension {ext_name}...")
        os.system(f"pip uninstall -y {ext_name}")
        print(f"Extension {ext_name} uninstalled.")

    cmds.select(
        {
            "install": install_ext,
            "uninstall": uninstall_ext,
        }
    )


def main():
    cmds = CmdSelector(sys.argv[1:], "grapycal")
    cmds.select(
        {
            "run": run,
            "ext": ext,
        }
        | (
            {"dev": dev} if not Path(GRAPYCAL_ROOT / "build_info.json").exists() else {}
        )  # hide dev command if it's a release build
    )
