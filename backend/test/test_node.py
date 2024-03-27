import pytest
from utils import setup_workspace, main_editor, test_ext

def test_node_creation(setup_workspace,main_editor):
    '''
    Nodes can be created in the editor when the user drags a node from the sidebar to the editor.
    '''
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    assert len(main_editor.get_children()) == 1
    assert main_editor.get_children()[0] == n1

def test_node_deletion(setup_workspace,main_editor):
    '''
    Nodes can be deleted from the editor when the user selects a node and presses the delete key.
    '''
    n1 = main_editor.create_node('grapycal_test.Test1Node')
    assert len(main_editor.get_children()) == 1

    main_editor._delete([n1.get_id()])
    assert len(main_editor.get_children()) == 0

    # The node is not in the SObject tree anymore. It is in the destroyed state.
    assert n1.is_destroyed()

    # Although we have its reference, we cannot access its attributes anymore. (normally we should not have its reference at all after deletion)
    with pytest.raises(Exception):
        n1.int_topic.set(325)

def test_node_creation_undo_redo(setup_workspace,main_editor):
    '''
    Node creation can be undone and redone on ctrl+z and ctrl+y respectively.
    '''
    n1 = main_editor.create_node('grapycal_test.Test1Node')

    main_editor._server._undo()
    assert len(main_editor.get_children()) == 0

    main_editor._server._redo()
    # Although the node is added back to the editor, the restored node is not the same instance as the original node
    assert len(main_editor.get_children()) == 1
    n1_restored = main_editor.get_children()[0]
    assert n1_restored != n1
    
def test_node_deletion_undo_redo(setup_workspace,main_editor):
    '''
    Node deletion can be undone and redone on ctrl+z and ctrl+y respectively.
    '''
    
    n1 = main_editor.create_node('grapycal_test.Test1Node')

    # Set some attribute values
    n1.int_topic.set(325)
    n1.string_topic.set('hello')
    n1.translation.set('-4,3')

    # Delete the node
    main_editor._delete([n1.get_id()])
    
    # Undo the deletion
    main_editor._server._undo()

    # Although the node is added back to the editor, the restored node is not the same instance as the original node
    assert len(main_editor.get_children()) == 1

    n1_restored = main_editor.get_children()[0]
    assert n1 != n1_restored

    # The attribute values of the restored node is the same as the original node.
    # This is because ObjectSync automatically restores all the attributes when the SObject is restored.
    # This is a important feature of ObjectSync.
    assert n1_restored.int_topic.get() == n1.int_topic.get()
    assert n1_restored.string_topic.get() == n1.string_topic.get()
    assert n1_restored.translation.get() == n1.translation.get()

    # Redo the deletion. The node should be deleted again.
    main_editor._server._redo()
    assert len(main_editor.get_children()) == 0