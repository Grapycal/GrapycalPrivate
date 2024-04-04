from typing import Dict, Literal, Tuple
import inspect
import ast

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
    print(f"Getting annotation for {attr} in {cls}, {type(cls)}")
    for stmt in ast.parse(unindent(inspect.getsource(cls.__init__))).body[0].body:
        if isinstance(stmt, ast.AnnAssign):
            if stmt.target.attr == attr:
                if isinstance(stmt.annotation, ast.Name):
                    return stmt.annotation.id

def get_attrs_in_init(cls:type):
    print(f"Getting attributes for {cls}, {type(cls)}")
    for stmt in ast.parse(unindent(inspect.getsource(cls.__init__))).body[0].body:
        if isinstance(stmt, ast.AnnAssign|ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Attribute):
                    yield target.attr

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
        

def _get_attr_suggestions(code:str,vars:Dict[str,object]):
    if '.' in code:
        code, uncompleted_identifier = code.rsplit('.', 1)
    else:
        uncompleted_identifier = code
        code = ""
        
    if code == "":
        print(uncompleted_identifier)
        return [attr for attr in vars if attr.startswith(uncompleted_identifier)]
    
    expr = get_longest_attr_expr(code)

    if expr is None:
        return []
    t, base = resolve_expr(expr,vars)
    if t is None:
        return []
    
    print(f"Base: {base}")
    if t == "object":
        suggestions = [attr for attr in dir(base) if attr.startswith(uncompleted_identifier)]
    else:
        suggestions = [attr for attr in get_attrs_in_init(base) if attr.startswith(uncompleted_identifier)]+\
            [attr for attr in dir(base) if attr.startswith(uncompleted_identifier)]
            
    return suggestions

def get_autocomplete_suggestions(code:str,vars:Dict[str,object]):
    res = []
    try:
        attr_suggestions = _get_attr_suggestions(code, vars)
    except Exception as e:
        attr_suggestions = []
    for label in attr_suggestions:
        res.append({
            "label": label,
            "type": "variable",
        })
    return res