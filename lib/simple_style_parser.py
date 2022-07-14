# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: simple_style_parser.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

import re


class SimpleStyleParser:
    """
        https://developer.mozilla.org/en-US/docs/Web/CSS/Syntax
        No checking .....
        Just emulate (simple emulation) the dict object for Style string
        for example if style string is

    """

    DECLARATION_BLOCK_ENCLOSURES = ('{', '}')
    DECLARATION_SEPARATOR = ';'
    PARAMETER_VALUE_SEPARATOR = ':'

    DEFAULT_PARAMETER_VALUE_HANDLER_NAME = 'default'

    PARAMETER_VALUE_PARSE_HANDLERS = {
        DEFAULT_PARAMETER_VALUE_HANDLER_NAME: lambda value: str(value).split(),
        'font-family': lambda value: [val.strip().strip('\'"') for val in str(value).split(',')]
    }

    PARAMETER_VALUE_UNPARSE_HANDLERS = {
        DEFAULT_PARAMETER_VALUE_HANDLER_NAME: lambda values: ' '.join(values),
        'font-family': lambda values: ', '.join((
            '"'+values[0]+'"' if len(values[:1]) > 0 else '', *values[1:]
        ))
    }

    def __init__(self, style: str = None) -> None:
        self.__declarations = {}
        if style:
            self.parse(style)
        super().__init__()

    def _parse_value(self, param, value):
        handler = self.PARAMETER_VALUE_PARSE_HANDLERS.get(param)
        if handler is None:
            handler = self.PARAMETER_VALUE_PARSE_HANDLERS[self.DEFAULT_PARAMETER_VALUE_HANDLER_NAME]
        return handler(value)

    def _unparse_value(self, param, values):
        handler = self.PARAMETER_VALUE_UNPARSE_HANDLERS.get(param)
        if handler is None:
            handler = self.PARAMETER_VALUE_UNPARSE_HANDLERS[self.DEFAULT_PARAMETER_VALUE_HANDLER_NAME]
        return handler(values)

    def parse(self, style: str):
        self.__declarations = {}
        style = str(style).strip().strip(''.join(self.DECLARATION_BLOCK_ENCLOSURES)).strip()
        decls_gen = (decl.strip() for decl in style.split(self.DECLARATION_SEPARATOR) if decl.strip())
        for decl in decls_gen:
            param, value = decl.split(self.PARAMETER_VALUE_SEPARATOR)
            self.__declarations[param] = self._parse_value(param, value)
        return self

    def normalize(self, normal_state: dict, values_comp=None):
        """
            @normal_state: dict It is dictionary that treat values as normal
            @values_comp: Callable It is function that takes 3 arguments 'param_name', 'values' from current instance
            and '_values' - normalized values from normal_state dictionary for comparison.

            For example, if object had an initial style string -
            'font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt'
            It will transformed into internal structure
            {'font-family': ['Noto Sans Mono CJK SC', 'monospace'], 'font-size': ['10pt']}
            Values for 'normal_state' will transformed also
            Hence, for comparison the values will use, by default, list.__eq__ function with
            ignore 'param_name' parameter. But if need custom comparison a 'values_comp' argument can be callable
            that will have 'param_name' for adaptive comparison.
        """

        def _default_comparer(param, values, _values):
            return type(values).__eq__(values, _values)

        for nparam, nvalues in normal_state.items():
            _nvalues = nvalues
            if isinstance(_nvalues, str):
                _nvalues = self._parse_value(nparam, _nvalues)

            values = self.__declarations.get(nparam)
            if values_comp is None:
                values_comp = _default_comparer
            if values and values_comp(nparam, values, _nvalues):
                self.__declarations.pop(nparam)

        return self

    # below are stubs for simple emulation of dict object
    def __getitem__(self, item):
        return self.__declarations[item]

    def __setitem__(self, item, value):
        if isinstance(value, str):
            value = [value]
        self.__declarations[item] = value

    def __delitem__(self, item):
        del self.__declarations[item]

    def __iter__(self):
        for item in self.__declarations:
            return item

    def __contains__(self, item):
        return item in self.__declarations

    def __str__(self):
        res = []
        for param, values in self.__declarations.items():
            res.append('{0}{1}{2}'.format(
                param,
                self.PARAMETER_VALUE_SEPARATOR+' ',
                self._unparse_value(param, values)
            ))

        return (self.DECLARATION_SEPARATOR+' ').join(res)

    def get(self, key, default=None):
        return self.__declarations.get(key, default)

    def keys(self):
        return self.__declarations.keys()

    def items(self):
        return self.__declarations.items()

    def values(self):
        return self.__declarations.values()


class SimpleRuleSetsParser:
    """
        for example <style> contains

        pre.western { font-family: "Liberation Mono", monospace; font-size: 10pt }
        pre.cjk { font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt }
        pre.ctl { font-family: "Liberation Mono", monospace; font-size: 10pt }
        h3 { margin-top: 0.1in; margin-bottom: 0.08in; background: transparent; page-break-after: avoid }
        h3.western { font-family: "Liberation Serif", serif; font-size: 14pt; font-weight: bold }
        h3.cjk { font-family: "Noto Serif CJK SC"; font-size: 14pt; font-weight: bold }
        h3.ctl { font-family: "FreeSans"; font-size: 14pt; font-weight: bold }
        code.western { font-family: "Liberation Mono", monospace }

        It will parsed into dictionary
            'pre.western' -> SimpleStyleParser('{ font-family: "Liberation Mono", monospace; font-size: 10pt }')
            ......
            'code.western' -> SimpleStyleParser('{ font-family: "Liberation Mono", monospace }')
    """

    def __init__(self, rules: str = None) -> None:
        self.__rulesets = None
        self.parse(rules)
        super().__init__()

    @property
    def rulesets(self):
        return self.__rulesets

    def parse(self, rules: str):
        self.__rulesets = {}
        pattern = r'(\{0}.*?\{1})'.format(
            SimpleStyleParser.DECLARATION_BLOCK_ENCLOSURES[0],
            SimpleStyleParser.DECLARATION_BLOCK_ENCLOSURES[1]
        )
        parts = re.split(pattern, rules, flags=re.S)
        parts_len = len(parts)
        for i in range(parts_len):
            if i % 2:
                continue
            rule, decl = (parts[i].strip(), '')
            if i + 1 < parts_len:
                decl = parts[i+1].strip()
            if decl:
                self.__rulesets[rule] = SimpleStyleParser(decl)
        return self


if __name__ == '__main__':
    style = SimpleStyleParser('{ font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt }')
    assert_error_font_family_str = "style['font-family'] is {}".format(style['font-family']) + \
                                   " font-family should be ['Noto Sans Mono CJK SC', 'monospace']"
    assert_error_font_size_str = '"font-size" should be [\'10pt\']:'

    assert style['font-family'] == ['Noto Sans Mono CJK SC', 'monospace'], assert_error_font_family_str
    assert style['font-size'] == ['10pt'], "'font-size' should be ['10pt']"

    style = SimpleStyleParser('font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt ')
    assert style['font-family'] == ['Noto Sans Mono CJK SC', 'monospace'], assert_error_font_family_str
    assert style['font-size'] == ['10pt'], assert_error_font_size_str

    style = SimpleStyleParser()
    style.parse('{ font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt')
    assert style['font-family'] == ['Noto Sans Mono CJK SC', 'monospace'], assert_error_font_family_str
    assert style['font-size'] == ['10pt'], assert_error_font_size_str
    assert str(style) == 'font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt'
    style.normalize({'font-size': '10pt', 'font-family': 'Noto Sans Mono CJK SC, monospace'})
    assert str(style) == ''
    style.parse('{ font-family: "Noto Sans Mono CJK SC", monospace; font-size: 10pt')
    style.normalize({'font-size': '10pt', 'font-family': ['Noto Sans Mono CJK SC', 'monospace']})
    assert str(style) == ''

    styles = '''          p { 
                margin-bottom: 0.1in; 
                line-height: 120%; 
                background: transparent 
            }
                pre { background: transparent }
           pre.western { font-family: "Liberation Mono", monospace; font-size: 10pt }
    '''

    rules = SimpleRuleSetsParser(styles)
    assert rules.rulesets['p']['margin-bottom'] == ['0.1in'], \
        "Should be rules.rulesets['p']['margin-bottom'] == ['0.1in']"
    assert rules.rulesets['p']['line-height'] == ['120%'], \
        "Should be rules.rulesets['p']['line-height'] == ['120%']"
    assert rules.rulesets['p']['background'] == ['transparent'], \
        "Should be rules.rulesets['p']['background'] == ['transparent']"
    assert rules.rulesets['pre']['background'] == ['transparent'], \
        "Should be rules.rulesets['pre']['background'] == ['transparent']"
    assert rules.rulesets['pre.western']['font-family'] == ['Liberation Mono', 'monospace'], \
        "Should be rules.rulesets['pre.western']['font-family'] == ['Liberation Mono', 'monospace']"
    assert rules.rulesets['pre.western']['font-size'] == ['10pt'], \
        "Should be rules.rulesets['pre.western']['font-size'] == ['10pt']"
