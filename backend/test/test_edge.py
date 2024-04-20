import pytest
from utils import setup_workspace, main_editor

def test_edge_creation(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    n2 = main_editor.create_node('grapycal_test.Test1Node')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    assert e.tail.get() == p1
    assert e.head.get() == p2

    # Nodes and edges are children of the editor
    assert set(main_editor.get_children()) == {n1, n2, e}
    
def test_max_edges(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    n2 = main_editor.create_node('grapycal_test.Test1Node')
    p1 = n1.add_out_port('out', max_edges=2)
    p2 = n2.add_in_port('in')

    e1 = main_editor.create_edge(p1, p2)
    e2 = main_editor.create_edge(p1, p2)

    with pytest.raises(Exception):
        e3 = main_editor.create_edge(p1, p2)

def test_edge_deletion(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    n2 = main_editor.create_node('grapycal_test.Test1Node')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    main_editor._delete([e.get_id()])

    assert p1.edges == []
    assert p2.edges == []

def test_edge_deletion_on_node_deletion(setup_workspace,main_editor):
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    n2 = main_editor.create_node('grapycal_test.Test1Node')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    e = main_editor.create_edge(p1, p2)

    # Delete one of the nodes
    main_editor._delete([n1.get_id()])

    # The edge should be deleted as well because one of the nodes it is connected to is deleted
    assert p1.edges == []
    assert p2.edges == []

def test_edge_move(setup_workspace,main_editor):
    '''
    An edge's head or tail can be moved to another port dynamically.
    It happens when the user drags the edge to another port.
    '''
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    n2 = main_editor.create_node('grapycal_test.Test1Node')
    n3 = main_editor.create_node('grapycal_test.Test1Node')
    p1 = n1.add_out_port('out')
    p2 = n2.add_in_port('in')
    p3 = n3.add_in_port('in')

    # Create an edge between p1 and p2
    e = main_editor.create_edge(p1, p2)

    assert p1.edges == [e]
    assert p2.edges == [e]
    assert p3.edges == []

    # Move the edge's head from p2 to p3
    e.head.set(p3)

    assert p1.edges == [e]
    assert p2.edges == []
    assert p3.edges == [e]
    