from contextlib import contextmanager
from unittest.mock import Mock, patch
from typing import Protocol, runtime_checkable

from grapycal import OutputPort, InputPort
from grapycal.core.typing import PlainType, GType, AnyType
from grapycal.sobjects.controls import NullControl
from grapycal.utils.misc import Action


@contextmanager
def mock_in_out_ports(out_type: GType, in_type: GType):
    server_mock = Mock()
    topic_mock = Mock()
    server_mock.create_topic.return_value = topic_mock
    topic_mock.on_set2 = Action()

    out_port = OutputPort(server=server_mock, id="1", parent_id="p")
    in_port = InputPort(server=server_mock, id="2", parent_id="p")

    out_port.build(datatype=out_type)
    out_port.init()

    # patch out the annoying check, we don't need to add_child anyway
    patcher = patch.object(in_port, 'add_child')
    try:
        patcher.start()
        in_port.build(control_type=NullControl, datatype=in_type)
        in_port.init()

        yield in_port, out_port
    finally:
        patcher.stop()


def test_simple_type_match():
    with mock_in_out_ports(out_type=PlainType(int), in_type=PlainType(int),) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)

def test_simple_type_mismatch():
    with mock_in_out_ports(out_type=PlainType(int), in_type=PlainType(str)) as (in_port, out_port):
        assert not out_port.can_connect_to(in_port)

def test_any_on_input():
    with mock_in_out_ports(out_type=PlainType(int), in_type=AnyType) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)

def test_any_on_output():
    with mock_in_out_ports(out_type=AnyType, in_type=PlainType(int)) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)

def test_any_on_both_in_out():
    with mock_in_out_ports(out_type=AnyType, in_type=AnyType) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)
        assert out_port.can_connect_to(in_port)

def test_nominal_subclass_super_input_accept_child_output():
    class Super:
        pass
    class Child(Super):
        pass

    with mock_in_out_ports(out_type=PlainType(Child), in_type=PlainType(Super)) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)

def test_nominal_subclass_child_input_not_accept_super_output():
    class Super:
        pass
    class Child(Super):
        pass

    with mock_in_out_ports(out_type=PlainType(Super), in_type=PlainType(Child)) as (in_port, out_port):
        assert not out_port.can_connect_to(in_port)

def test_structural_subtype():
    @runtime_checkable
    class Super(Protocol):
        def a(self): ...
        def b(self, arg): ...
    class Child:
        def a(self):
            pass
        def b(self, arg):
            pass

    with mock_in_out_ports(out_type=PlainType(Child), in_type=PlainType(Super)) as (in_port, out_port):
        assert out_port.can_connect_to(in_port)
