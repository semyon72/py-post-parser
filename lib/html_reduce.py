# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: html_reduce.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from lxml.etree import _Element
import lxml.html


class BaseRecursiveHandler:
    on_element_func = []

    def __init__(self, el: _Element = None) -> None:
        self.__start_element = None
        self.start_element = el
        super().__init__()

    @property
    def start_element(self):
        return self.__start_element

    @start_element.setter
    def start_element(self, el: _Element):
        self.__start_element = el

    def process_funcs(self, e: _Element):
        for func in self.on_element_func:
            func(e)
            if e.getparent() is None:
                # if no parent then element was removed
                break

    def reverse_walk(self, element: _Element):
        for child in element:
            self.reverse_walk(child)

        self.process_funcs(element)

    def walk(self, element: _Element):
        self.process_funcs(element)

        if element.getparent() is not None:
            for child in element:
                self.walk(child)

    def process(self):
        if self.__start_element is not None:
            self.reverse_walk(self.__start_element)


class CleanAnyEmptyHandler(BaseRecursiveHandler):

    # https://developer.mozilla.org/ru/docs/Glossary/Empty_element
    void_elements = ('area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'keygen',
                     'link', 'meta', 'param', 'source', 'track', 'wbr')

    def remove_empty(el: _Element):
        if el.tag in CleanAnyEmptyHandler.void_elements:
            return

        full_text_list = ((el.text if el.text else '') + (el.tail if el.tail else '')).strip()
        if not full_text_list and len(el) == 0:
            parent = el.getparent()
            parent.remove(el)

    on_element_func = [remove_empty]


class CleanEmptyBlockHandler(BaseRecursiveHandler):

    block_tags = ('address', 'article', 'aside', 'blockquote', 'details', 'dialog', 'dd', 'div', 'dl', 'dt',
                  'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'header', 'hgroup', 'hr', 'li', 'main', 'nav', 'ol', 'p', 'pre', 'section', 'table', 'ul')

    def remove_empty_blocks(el: _Element):
        if el.tag in CleanEmptyBlockHandler.block_tags:
            content = el.text_content().strip()
            if not content:
                parent = el.getparent()
                parent.remove(el)

    # order is important, first more precise or common
    on_element_func = [remove_empty_blocks]

    def process(self):
        self.walk(self.start_element)


class HTMLReduce:

    handlers = []

    def __init__(self, el: _Element = None) -> None:
        self.__start_element = None
        self.load(el)
        super().__init__()

    def load(self, source):
        if not source:
            return self
        if isinstance(source, _Element):
            self.__start_element = source
        else:
            with open(source, mode='r') as fd:
                self.__start_element = lxml.html.parse(fd).getroot().body
        return self

    def write(self, file):
        etree = self.__start_element.getroottree()
        with open(file, mode='w') as fd:
            # <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
            # It must be pointed because parser (seems) work does not properly.
            # if it does not containing inside file.
            # If file does not contain at least '<!DOCTYPE html>' then
            # lxml.html.parse(fd).getroot() will return None
            fd.write(lxml.html.tostring(etree.getroot(), encoding='unicode', method='html', doctype='<!DOCTYPE html>'))

    def reduce_content(self):
        for h in self.handlers:
            h.start_element = self.__start_element
            h.process()
        return self


if __name__ == '__main__':

    # Observation of lxml essentials
    #
    # test_str = '<p>Should be text of "p" <em>1st child em<em>level2</em></em><em>text of last "em"</em>' \
    #            'p-level1 but tail of last "em"</p><p>p-level1.2</p>'
    # start_p = lxml.html.fromstring(test_str)[0]
    # print('Start <p> text:', start_p.text)
    # print('Start <p> tail:', start_p.tail)
    # print('Last <em> text:', start_p[1].text)
    # print('Last <em> tail:', start_p[1].tail)
    # print('Trying to remove inner <em>:')
    # start_p[0][0].drop_tag()
    # start_p[1].drop_tag()
    # print('Result:', lxml.html.tostring(start_p))
    #

    # test_str = '<p><em>level1<em>level2</em></em><em>level1.2</em>p-level1</p><p>p-level1.2</p>'
    # elements = lxml.html.fromstring(test_str)
    # print("##### for el in elements.iter('em'):")
    # for el in elements.iter('em'):
    #     print(el.text, '->', el.tail)
    #
    # # ##### for el in elements.iter('em'):
    # # level1 -> None
    # # level2 -> None
    # # level1.2 -> p-level1
    #
    # print("##### for el in elements.iterchildren('p', reversed=True):")
    # for el in elements.iterchildren('p', reversed=True):
    #     print(el.text, '->', el.tail)
    #
    # # ##### for el in elements.iterchildren('p', reversed=True):
    # # p-level1.2 -> None
    # # None -> None
    #
    # print("##### for el in elements.iterchildren('em', reversed=True):")
    # for el in elements.iterchildren('em', reversed=True):
    #     print(el.text, '->', el.tail)
    #
    # # ##### for el in elements.iterchildren('em', reversed=True):
    #
    # print("##### for el in elements.iterdescendants('em'):")
    # for el in elements.iterdescendants('em'):
    #     print(el.text, '->', el.tail)
    #
    # # ##### for el in elements.iterdescendants('em'):
    # # level1 -> None
    # # level2 -> None
    # # level1.2 -> p-level1
    #
    # print("##### for el in elements.iterdescendants('p'):")
    # for el in elements.iterdescendants('p'):
    #     print(el.text, '->', el.tail)
    #
    # # ##### for el in elements.iterdescendants('p'):
    # # None -> None
    # # p-level1.2 -> None
    #
    #

    # Some real testing inside post_html_reduce.py
    pass
