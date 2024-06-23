import pathlib
from grapycal.stores import main_store
from urllib.parse import urljoin

import requests

RESOURCE_SERVER = "https://resource.grapycal.com/"


def get_resource(path: str, is_dir: bool = False) -> pathlib.Path:
    if not hasattr(main_store, "settings"):
        raise Exception("only call get_resource after the workspace is set up")
    local_path = (
        pathlib.Path(main_store.settings.data_path.get()) / "gr_resource" / path
    )
    remote_url = urljoin(RESOURCE_SERVER, path)
    if is_dir:
        download_path = local_path.with_suffix(".zip")
        remote_url = remote_url + ".zip"
    else:
        download_path = local_path

    if not local_path.exists():
        download_path.parent.mkdir(parents=True, exist_ok=True)

        with open(download_path, "wb") as f:
            print(f"Downloading {remote_url} to {download_path}")
            response = requests.get(remote_url, allow_redirects=False)
            print(response.status_code)
            if response.status_code != 200:
                raise Exception(
                    f"Failed to download {remote_url}: {response.status_code}"
                )
            f.write(response.content)

        if is_dir:
            import zipfile

            try:
                with zipfile.ZipFile(download_path, "r") as zip_ref:
                    zip_ref.extractall(download_path.parent)
            except Exception as e:
                download_path.unlink()
                raise Exception(
                    f"Failed to extract {download_path}: {e}. Maybe the file is corrupted. Please try again."
                )

    return local_path
