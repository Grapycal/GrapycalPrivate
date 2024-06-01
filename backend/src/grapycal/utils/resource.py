import pathlib
from grapycal.stores import main_store
from urllib.parse import urljoin

import requests

RESOURCE_SERVER = "https://resource.grapycal.com/"


def get_resource(path: str):
    if not hasattr(main_store, "settings"):
        raise Exception("only call get_remote_resource after the workspace is set up")
    local_cache_path = (
        pathlib.Path(main_store.settings.data_path.get()) / "gr_resource" / path
    )
    remote_url = urljoin(RESOURCE_SERVER, path)

    if not local_cache_path.exists():
        local_cache_path.parent.mkdir(parents=True, exist_ok=True)

        with open(local_cache_path, "wb") as f:
            f.write(requests.get(remote_url).content)

    return local_cache_path
