# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: post_html_reduce.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

import lxml.html
from lxml.etree import _Element

from lib.html_reduce import CleanAnyEmptyHandler, HTMLReduce, BaseRecursiveHandler
from lib.simple_style_parser import SimpleStyleParser


class CleanPostHandler(BaseRecursiveHandler):

    normal_font_size = '3'

    def normalize_attr(el: _Element):

        normal_state = {
            'face': {'Liberation Serif, serif', 'monospace, sans-serif', 'JetBrains Mono, serif'},
            'color': {'#000000', 'black'},
            'size': CleanPostHandler.normal_font_size,
            'bgcolor': "#ffffff",
        }

        for attr, values in el.attrib.items():
            _values = normal_state.get(attr)
            if isinstance(_values, set):
                is_equal = len({values} & _values) > 0
            else:
                is_equal = values == _values

            if is_equal:
                el.attrib.pop(attr)

    def normalize_style(el: _Element):

        normal_state = {
            'background': {'#ffffff', 'white', 'transparent'},
            'color': {'#000000', 'black'},
            'font-weight': 'normal',
            'margin-bottom': '0in',
            'line-height': '100%',
            'font-variant': 'normal',
            'letter-spacing': 'normal',
            'font-style': 'normal',
            'display': 'inline-block',
            'border': 'none',
            'padding': '0in',
            'font-size': '12pt',
        }

        def val_comparer(param, values, _values):
            if isinstance(_values, set):
                return len(set(values) & _values) > 0
            else:
                return values == _values

        attr = el.get('style')
        if attr:
            style = SimpleStyleParser(attr).normalize(normal_state, val_comparer)
            style_str = str(style)
            if style_str:
                if attr != style_str:
                    el.set('style', style_str)
            else:
                el.attrib.pop('style')

    def clean_fontsize_stile(el: _Element):
        if el.tag == 'font':
            atr_style = el.get('style')
            if atr_style:
                atr_size = el.get('size')
                if not atr_size:
                    return

                style = SimpleStyleParser(atr_style)
                if 'font-size' in style:
                    del style['font-size']
                    style_str = str(style)
                    if style_str:
                        if atr_style != style_str:
                            el.set('style', style_str)
                    else:
                        el.attrib.pop('style')

    def drop_normal_span(el: _Element):
        # <span style="background: #ffffff">.....</span> -> move to tail or add to text of parent
        if el.tag in ('span',):
            if not el.get('style'):
                el.drop_tag()

    def drop_normal_font(el: _Element):
        # <font color="#000000">.......</font> -> move to tail or add to text of parent
        if el.tag == 'font':
            if not el.get('style') and not el.attrib:
                el.drop_tag()

    def monospace_font_to_code(el: _Element):
        # <font face="Liberation Mono, monospace">...</font>
        if el.tag == 'font':
            attr = el.get('face')
            if attr and 'monospace' in [val.strip() for val in attr.split(',')]:
                el.tag = 'code'
                el.attrib.clear()
                parent = el.getparent()
                if parent is not None and parent.tag in ('p', 'code'):
                    el.drop_tag()

    def collapse_sibling_code_inside_notpre(el: _Element):

        def get_inner_string(el: _Element):
            res = []
            if el is not None:
                res.append(el.text)
                for e in el:
                    res.append(lxml.html.tostring(e, encoding='unicode'))
                res.append(el.tail)
            return ''.join(filter(None, res))

        if el.tag == 'code':
            parent = el.getparent()
            if parent is None or parent.tag != 'pre':
                prev_el = el.getprevious()
                if prev_el is None or prev_el.tag != 'code':
                    pass
                else:
                    # at first time we always inside first <code>
                    res_str = '<code>{}{}</code>'.format(get_inner_string(prev_el), get_inner_string(el))
                    new_el = lxml.html.fragment_fromstring(res_str, base_url=prev_el.base)
                    parent.replace(prev_el, new_el)
                    parent.remove(el)

    def remove_empty_exclude_void_elements(el: _Element):
        CleanAnyEmptyHandler.remove_empty(el)

    # order is important, first more precise or common
    on_element_func = [
        normalize_attr, normalize_style, clean_fontsize_stile,
        drop_normal_span, drop_normal_font,
        monospace_font_to_code,
        collapse_sibling_code_inside_notpre, remove_empty_exclude_void_elements
    ]


class PostHTMLReduce(HTMLReduce):
    # handlers = [CleanPostHandler(), CleanEmptyBlockHandler()]
    handlers = [CleanPostHandler()]


if __name__ == '__main__':

    import os

    files = ('/home/ox23/PycharmProjects/py-post-parser/work.result/Django/Logging.html',
             '/home/ox23/PycharmProjects/py-post-parser/work.result/Django/Static files.html')

    reducer = PostHTMLReduce()
    for file in files:
        reducer.load(file).reduce_content()
        reducer.write(os.path.join(os.path.dirname(file), '~'+os.path.basename(file)))
