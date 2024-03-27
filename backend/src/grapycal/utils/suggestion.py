import sys
from types import ModuleType
import re
from typing import Sequence
import importlib


def check_if_module_is_imported(module_name: str | ModuleType) -> bool:
    return module_name in sys.modules


def check_context(string):
    pattern = r"^[a-zA-Z0-9]+(\.[a-zA-Z0-9]*)*$"
    return bool(re.match(pattern, string))


def parse_context(text: str) -> Sequence[str]:
    if text.endswith("."):
        _context = text.strip().split(".")[:-1]
        text = text[:-1]
    else:
        _context = text.strip().split(".")

    return _context[0], text


def get_original_module(alias):
    return sys.modules[alias]


def get_autocomplete_suggestions(text: str) -> list[dict[str, str]]:
    if not check_context(text):
        return []

    root_module, module = parse_context(text)

    if not check_if_module_is_imported(root_module):
        return []

    module = importlib.import_module(module)

    suggestions: list[dict[str, str]] = []
    for key, value in module.__dict__.items():
        suggestions.append({"key": key, "type": type(value).__name__})

    return suggestions
