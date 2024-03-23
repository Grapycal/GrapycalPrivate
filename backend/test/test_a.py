
from grapycal.core.workspace import Workspace
from grapycal.stores import main_store
import pytest

def setup_workspace():
    workspace = Workspace(port=8766, host="localhost", path="workspace.grapycal", workspace_id=0)
    workspace.run(run_runner=False)

def test_edge_creation():
    setup_workspace()
    n1 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_store.main_editor.create_edge(p1, p2)

    assert e.tail.get() == p1
    assert e.head.get() == p2
    
def test_max_edges():
    setup_workspace()
    n1 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out', max_edges=2)
    p2 = n2.add_in_port('in')

    e1 = main_store.main_editor.create_edge(p1, p2)
    e2 = main_store.main_editor.create_edge(p1, p2)

    with pytest.raises(Exception):
        e3 = main_store.main_editor.create_edge(p1, p2)

def test_edge_deletion():
    setup_workspace()
    n1 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_store.main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_store.main_editor.create_edge(p1, p2)

    main_store.main_editor._delete([e.get_id()])

    assert p1.edges == []
    assert p2.edges == []