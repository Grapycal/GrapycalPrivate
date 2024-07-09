import math
from grapycal import func, Node, param


class MathBaseNode(Node):
    category = "function/math"
    shape = "round"


class AddNode(MathBaseNode):
    label = "+"

    @func(create_trigger_port=False)
    def output(self, a=0, b=0):
        return a + b


class SubtractNode(MathBaseNode):
    label = "-"

    @func(create_trigger_port=False)
    def output(self, a=0, b=0):
        return a - b


class MultiplyNode(MathBaseNode):
    label = "*"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a * b


class DivideNode(MathBaseNode):
    label = "/"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a / b


class PowerNode(MathBaseNode):
    label = "**"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a**b


class ModulusNode(MathBaseNode):
    label = "%"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a % b


class FloorDivideNode(MathBaseNode):
    label = "//"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a // b


class AbsNode(MathBaseNode):
    @func(create_trigger_port=False)
    def output(self, a=1):
        return abs(a)


class RoundNode(MathBaseNode):
    label = "round"
    shape = "normal"

    @param()
    def param(self, digits: int | None = 0):
        self.digits = digits

    @func(create_trigger_port=False)
    def output(self, a=1):
        return round(a, self.digits)


class CeilNode(MathBaseNode):
    label = "⌈ ⌉"

    @func(create_trigger_port=False)
    def output(self, a=1):
        return math.ceil(a)


class FloorNode(MathBaseNode):
    label = "⌊ ⌋"

    @func(create_trigger_port=False)
    def output(self, a=1):
        return math.floor(a)


class GreaterThanNode(MathBaseNode):
    label = ">"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a > b


class GreaterThanEqualNode(MathBaseNode):
    label = ">="

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a >= b


class LessThanNode(MathBaseNode):
    label = "<"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a < b


class LessThanEqualNode(MathBaseNode):
    label = "<="

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a <= b


class EqualNode(MathBaseNode):
    label = "=="

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a == b


class NotEqualNode(MathBaseNode):
    label = "!="

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a != b


class AndNode(MathBaseNode):
    label = "and"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a and b


class OrNode(MathBaseNode):
    label = "or"

    @func(create_trigger_port=False)
    def output(self, a=1, b=2):
        return a or b


class NotNode(MathBaseNode):
    label = "not"

    @func(create_trigger_port=False)
    def output(self, a=1):
        return not a


del MathBaseNode
