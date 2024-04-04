from types import BuiltinFunctionType, FunctionType, ModuleType
from typing import Any, Callable, Dict, Generator, Literal, Sized, Tuple
import inspect
import ast
import pkgutil

def get_longest_attr_expr(code:str):
    for i in range(len(code)):
        sub_code = code[i:]
        try:
            tree = ast.parse(sub_code)
        except SyntaxError:
            continue
        if hasattr(tree.body[0],'value'):
            return tree.body[0].value
def unindent(code:str):
    lines = code.split('\n')
    indent = len(lines[0]) - len(lines[0].lstrip())
    return '\n'.join([line[indent:] for line in lines])
def get_annotation_in_init(cls:type,attr:str):
    for stmt in ast.parse(unindent(inspect.getsource(cls.__init__))).body[0].body:
        if isinstance(stmt, ast.AnnAssign):
            if stmt.target.attr == attr:
                if isinstance(stmt.annotation, ast.Name):
                    return stmt.annotation.id

class TypeInfo:
    def __init__(self, name:str):
        self.name = name

def get_attrs_in_init(cls:type) -> Generator[Tuple[str,str], None, None]:
    print(f"Getting attributes for {cls}, {type(cls)}")
    for stmt in ast.parse(unindent(inspect.getsource(cls.__init__))).body[0].body:
        if isinstance(stmt, ast.AnnAssign|ast.Assign):
            attr_type = TypeInfo(stmt.annotation.__qualname__ if isinstance(stmt, ast.AnnAssign) else '')
            for target in stmt.targets:
                if isinstance(target, ast.Attribute):
                    yield target.attr, attr_type

def resolve_expr(expr:ast.expr,vars:Dict[str,object]) -> Tuple[Literal["type"], type]|Tuple[Literal["object"], object]|Tuple[None, None]:
    print(f"Resolving expression: {ast.unparse(expr)}")
    if isinstance(expr, ast.Attribute):
        t, base = resolve_expr(expr.value, vars)
        if t is None or base is None:
            return None, None
        if t == "object":
            # get the attribute from the object
            return "object", getattr(base, expr.attr)
        else:# t == "type"
            # if the attibute is a method, return the method
            if hasattr(base, expr.attr):
                return "object", getattr(base, expr.attr)
            else: 
                if hasattr(base, '__init__'):
                    annotation = get_annotation_in_init(base, expr.attr)
                    if annotation is not None:
                        return "type", eval(annotation, vars)
                print(f"Attribute {expr.attr} not found in {base}")
                return None, None
    elif isinstance(expr, ast.Name):
        return "object", eval(expr.id, vars)
    elif isinstance(expr, ast.Call):
        t, base = resolve_expr(expr.func, vars)
        if t is None:
            return None, None
        if t == "object":
            # if t is class, its result is an object of that class
            if isinstance(base, type):
                return "type", base
            return "type", eval(base.__annotations__['return'], vars)
        else:
            if isinstance(base, type): # a call of a type returns object of that type
                return "type", base
            else:
                print(f"Unsupported call: {base}")
                return None, None
    else:# TODO: handle other cases
        print(f"Unsupported expression type: {expr}")
        return None, None


def _get_attr_suggestions(code:str,module_vars:Dict[str,object]) -> list[Tuple[str,Any]]:
    if '.' in code:
        code, uncompleted_identifier = code.rsplit('.', 1)
    else:
        uncompleted_identifier = code
        code = ""
        
    if code == "":
        return [(name,value) for name, value in module_vars.items() if name.startswith(uncompleted_identifier)]+\
            [(name,value) for name, value in __builtins__.items() if name.startswith(uncompleted_identifier)]
    
    expr = get_longest_attr_expr(code)

    if expr is None:
        return []
    t, base = resolve_expr(expr,module_vars)
    print(f"Resolved expression: {t}, {base}")
    if t is None:
        return []
        
    
    if t == "object":
        suggestions = [(name,getattr(base,name)) for name in dir(base) if name.startswith(uncompleted_identifier)]
    else:
        suggestions = [attr for attr in get_attrs_in_init(base) if attr[0].startswith(uncompleted_identifier)]+\
            [(name,value) for name, value in base.__dict__.items() if name.startswith(uncompleted_identifier)]
            
    return suggestions
def get_last_identifier(code:str):
    # get last identifier
    for i in range(len(code)-1,-1,-1):
        if not code[i].isidentifier():
            break
        else:
            i -= 1
    last_identifier = code[i+1:]
    return last_identifier

def get_type_full_name(t:type):
    return f"{t.__module__}.{t.__qualname__}"

def get_info_str(value:Any):
    if isinstance(value, TypeInfo): # The value is typeinfo when we can't get the object, but we can get the type name
        return value.name
    if isinstance(value, type):
        return f"class {get_type_full_name(value)}"
    elif isinstance(value, ModuleType):
        return f"module {value.__name__}"
    elif isinstance(value, FunctionType) or isinstance(value, BuiltinFunctionType):
        try:
            signature = inspect.signature(value)
            return f"function {signature}"
        except ValueError:
            pass
    elif get_type_full_name(type(value)) == 'torch.Tensor':
        return f"torch.Tensor {list(value.shape)}"
    elif get_type_full_name(type(value)) == 'numpy.ndarray':
        return f"numpy.ndarray {list(value.shape)}"
    elif isinstance(value, Sized):
        return f"{type(value).__qualname__} [{len(value)}]"
    return f"{type(value).__qualname__}"

def get_autocomplete_suggestions(code:str,vars:Dict[str,object]):
    res = []

    # if start with import, suggest modules
    if code.strip().startswith('import ') or code.strip().startswith('from '):
        last_module_name = get_last_identifier(code)
        print(f"last_module_name: {last_module_name}")
        for pkg in pkgutil.iter_modules():
            if  pkg.name.startswith(last_module_name):
                res.append({
                    "label": pkg.name,
                    "type": "module",
                    "info": f"module {pkg.name}"
                })
        return res
    try:
        attr_suggestions = _get_attr_suggestions(code, vars)
    except Exception as e:
        import traceback
        traceback.print_exc()
        attr_suggestions = []
    for name, value in attr_suggestions:
        boost = 0
        if name.startswith('__'):
            boost = -50
        if name.startswith('_'):
            boost = -10
        res.append({
            "label": name,
            "type": "variable",
            "info": get_info_str(value),
            "boost": boost
        })
    return res