import pytest
from utils import setup_workspace, main_editor

def test_edge_creation(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    assert e.tail.get() == p1
    assert e.head.get() == p2
    
def test_max_edges(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out', max_edges=2)
    p2 = n2.add_in_port('in')

    e1 = main_editor.create_edge(p1, p2)
    e2 = main_editor.create_edge(p1, p2)

    with pytest.raises(Exception):
        e3 = main_editor.create_edge(p1, p2)

def test_edge_deletion(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    main_editor._delete([e.get_id()])

    assert p1.edges == []
    assert p2.edges == []

def test_edge_deletion_on_node_deletion(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_builtin.ExecNode')
    n2 = main_editor.create_node('grapycal_builtin.ExecNode')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    # Delete one of the nodes
    main_editor._delete([n1.get_id()])

    # The edge should be deleted as well because one of the nodes it is connected to is deleted
    assert p1.edges == []
    assert p2.edges == []