from grapycal import Extension, command, CommandCtx, GRID
from grapycal_builtin import EvalNode, MultiplicationNode, PrintNode
import random

class GrapycalOwo(Extension):

    @command('Make multiplication problem')
    def make_multiplication_problem(self, ctx: CommandCtx):
        x, y = ctx.mouse_pos
        
        a = random.randint(1, 10)
        b = random.randint(1, 10)
    
        a_node = self.create_node(EvalNode, [x, y])
        b_node = self.create_node(EvalNode, [x, y + GRID*6])
        mul_node = self.create_node(MultiplicationNode, [x + GRID*5, y + GRID*3])
        print_node = self.create_node(PrintNode, [x  + GRID*10, y + GRID*3])
    
        a_node.expr_control.set(str(a))
        b_node.expr_control.set(str(b))
    
        self.create_edge(a_node.out_port, mul_node.get_in_port('items'))
        self.create_edge(b_node.out_port, mul_node.get_in_port('items'))
        self.create_edge(mul_node.get_out_port('product'), print_node.get_in_port(''))
