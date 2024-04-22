
import pytest
from grapycal.core.workspace import Workspace
from grapycal.sobjects.editor import Editor
from grapycal.stores import main_store


@pytest.fixture
def setup_workspace():
    workspace = Workspace(port=8766, host="localhost", path="workspace.grapycal")
    workspace.run(run_runner=False)

    # Import test extension, so we can create test nodes
    workspace._extention_manager.import_extension('grapycal_test')

@pytest.fixture
def main_editor() -> Editor:
    return main_store.main_editor

@pytest.fixture
def test_ext():
    import grapycal_test
    return grapycal_test