
from grapycal.core.workspace import Workspace
from grapycal.stores import main_store

def test_node():
    workspace = Workspace(port=8766, host="localhost", path="workspace.grapycal", workspace_id=0)
    workspace.run(False)
    
    from grapycal_builtin.interaction.execNode import ExecNode
    n1 = main_store.main_editor.create_node(ExecNode)
    n2 = main_store.main_editor.create_node(ExecNode)
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_store.main_editor.create_edge(p1, p2)

    assert e.tail.get() == p1
    assert e.head.get() == p2
    
   