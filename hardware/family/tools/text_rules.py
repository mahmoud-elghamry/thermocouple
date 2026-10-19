"""Interpret this family's .pro classes and .dru clearance conditions, no eval.

Supports &&, ||, !, ==, !=, Type/NetClass/NetName and memberOfFootprint /
intersectsCourtyard. Later matching rules override earlier rules, symmetrically.
Unknown conditions/clearance constructs fail; non-clearance constraints are
listed as outside this check's scope rather than used as clearance rules.
"""
import fnmatch
import re
from text_sexp import parse, children, child, val


class Condition:
    def __init__(self, text):
        pattern = r"\s+|'(?:\\.|[^'\\])*'|&&|\|\||==|!=|[!().,]|[A-Za-z_][A-Za-z_0-9]*"
        matches = list(re.finditer(pattern, text))
        if ''.join(m.group() for m in matches) != text:
            raise ValueError(f'unsupported rule condition: {text}')
        self.tokens = [m.group() for m in matches if not m.group().isspace()]
        self.i = 0
        self.tree = self.expr() if self.tokens else ('true',)
        if self.i != len(self.tokens):
            raise ValueError(f'unconsumed rule condition: {text}')

    def eat(self, value):
        if self.i < len(self.tokens) and self.tokens[self.i] == value:
            self.i += 1
            return True
        return False

    def pop(self):
        if self.i >= len(self.tokens):
            raise ValueError('incomplete rule condition')
        value = self.tokens[self.i]
        self.i += 1
        return value

    def expect(self, value):
        if not self.eat(value):
            raise ValueError(f'expected {value!r} in rule condition')

    def expr(self):
        result = self.term()
        while self.eat('||'):
            result = ('or', result, self.term())
        return result

    def term(self):
        result = self.atom()
        while self.eat('&&'):
            result = ('and', result, self.atom())
        return result

    def atom(self):
        if self.eat('!'):
            return ('not', self.atom())
        if self.eat('('):
            result = self.expr()
            self.expect(')')
            return result
        side = self.pop()
        if side not in ('A', 'B'):
            raise ValueError('rule item must be A or B')
        self.expect('.')
        prop = self.pop()
        if self.eat('('):
            if prop not in ('memberOfFootprint', 'intersectsCourtyard'):
                raise ValueError(f'unsupported rule method {prop}')
            arg = self.pop()
            self.expect(')')
            if not arg.startswith("'"):
                raise ValueError('rule argument must be quoted')
            return 'call', side, prop, arg[1:-1]
        op, value = self.pop(), self.pop()
        if prop not in ('Type', 'NetClass', 'NetName') or op not in ('==', '!=') or not value.startswith("'"):
            raise ValueError(f'unsupported rule comparison {prop} {op} {value}')
        return op, side, prop, value[1:-1]

    def __call__(self, a, b, rules):
        def run(t):
            if t[0] == 'true': return True
            if t[0] == 'or': return run(t[1]) or run(t[2])
            if t[0] == 'and': return run(t[1]) and run(t[2])
            if t[0] == 'not': return not run(t[1])
            item = a if t[1] == 'A' else b
            if t[0] == 'call':
                return item.ref == t[3] if t[2] == 'memberOfFootprint' else t[3] in item.courts
            actual = {'Type': item.kind, 'NetName': item.net, 'NetClass': rules.netclass(item.net)}[t[2]]
            matches = fnmatch.fnmatchcase(actual, t[3])
            return matches if t[0] == '==' else not matches
        return run(self.tree)


class Rules:
    def __init__(self, project, text):
        settings = project.get('net_settings', {})
        self.classes = {c['name']: c for c in settings.get('classes', [])}
        if 'Default' not in self.classes:
            raise ValueError('project lacks Default netclass')
        self.patterns = settings.get('netclass_patterns', [])
        self.assignments = settings.get('netclass_assignments') or {}
        self.board_rules = project.get('board', {}).get('design_settings', {}).get('rules', {})
        self.rules, self.ignored, self.courtyards = [], [], set()
        self._classes, self._clearances = {}, {}
        for node in parse(text):
            if not isinstance(node, list) or node[0] != 'rule':
                continue
            condition = val(node, 'condition')
            self.courtyards.update(re.findall(r"intersectsCourtyard\('([^']+)'\)", condition))
            for constraint in children(node, 'constraint'):
                if constraint[1] != 'clearance':
                    self.ignored.append(dict(rule=node[1], constraint=constraint[1]))
                    continue
                if child(node, 'layer') or child(node, 'severity'):
                    raise ValueError('layer/severity-qualified clearance rules unsupported')
                number = str(val(constraint, 'min'))
                if not re.fullmatch(r'\d*\.?\d+(?:mm)?', number):
                    raise ValueError(f'unsupported clearance minimum: {number}')
                self.rules.append((node[1], float(number.removesuffix('mm')), Condition(condition)))
        self.maximum = max([c.get('clearance', 0) for c in self.classes.values()]
                           + [v for _, v, _ in self.rules] + [self.board_rules.get('min_clearance', 0)])

    def netclass(self, net):
        if not net:
            return ''  # Unnetted copper has no class in a .dru condition.
        if net not in self._classes:
            names = [p['netclass'] for p in self.patterns if fnmatch.fnmatchcase(net, p['pattern'])]
            assigned = self.assignments.get(net, [])
            names.extend([assigned] if isinstance(assigned, str) else assigned)
            self._classes[net] = min(names, key=lambda n: self.classes[n].get('priority', 999999)) if names else 'Default'
        return self._classes[net]

    def clearance(self, a, b):
        def signature(i):
            return i.net, i.kind, i.ref, i.courts
        key = signature(a), signature(b)
        if key not in self._clearances:
            value = max(self.classes.get(self.netclass(a.net),self.classes['Default']).get('clearance', 0),
                        self.classes.get(self.netclass(b.net),self.classes['Default']).get('clearance', 0))
            source = 'netclass'
            for name, minimum, condition in self.rules:
                if condition(a, b, self) or condition(b, a, self):
                    value, source = minimum, name
            minimum = self.board_rules.get('min_clearance', 0)
            if value < minimum:
                value, source = minimum, 'board_min_clearance'
            self._clearances[key] = value, source
        return self._clearances[key]
