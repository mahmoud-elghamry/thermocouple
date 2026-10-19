"""Small strict S-expression reader for KiCad board/rule text; stdlib only."""
import json
import re


def parse(text):
    root, stack = [], []
    current = root
    cursor = 0
    for match in re.finditer(r'\s+|\#[^\n]*|"(?:\\.|[^"\\])*"|[()]|[^\s()"]+', text):
        if match.start() != cursor:
            raise ValueError('invalid or unterminated quoted string')
        cursor = match.end()
        token = match.group()
        if token.isspace() or token.startswith('#'):
            continue
        if token == '(':
            node = []
            current.append(node)
            stack.append(current)
            current = node
        elif token == ')':
            if not stack:
                raise ValueError('unexpected closing parenthesis')
            current = stack.pop()
        else:
            current.append(json.loads(token) if token.startswith('"') else token)
    if cursor != len(text):
        raise ValueError('invalid trailing input')
    if stack:
        raise ValueError('unclosed S-expression')
    return root


def children(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


def child(node, key, default=None):
    return next(iter(children(node, key)), default)


def val(node, key, default=''):
    found = child(node, key)
    return found[1] if found and len(found) > 1 else default


def xy(node, key='at', default=(0., 0.)):
    found = child(node, key)
    return tuple(map(float, found[1:3])) if found else default


def points(node):
    return [tuple(map(float, p[1:3])) for p in children(child(node, 'pts', []), 'xy')]
