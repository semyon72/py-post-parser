# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: html_tools.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from collections import namedtuple

from lxml.etree import _Element
import difflib


class NormalizeContent:

    block_tags = ('address', 'article', 'aside', 'blockquote', 'details', 'dialog', 'dd', 'div', 'dl', 'dt',
                  'fieldset', 'figcaption', 'figure', 'footer', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'header', 'hgroup', 'hr', 'li', 'main', 'nav', 'ol', 'p', 'pre', 'section', 'table', 'ul')

    block_tag_prefix = "\n"

    def __init__(self, el: _Element) -> None:
        if el is None or not isinstance(el, _Element):
            raise ValueError('"el" should be "lxml.etree._Element" type')
        self.start_element = el
        super().__init__()

    @staticmethod
    def _normalize_string(string):
        if string:
            string = ' '.join(string.split())
            if not string:
                string += ' '
        return string

    def normalize(self):
        for e in self.start_element.iter():
            if e.tag in self.block_tags:
                if e.text is None:
                    e.text = self.block_tag_prefix
                else:
                    e.text = self.block_tag_prefix + e.text.strip()
        return self

    def __str__(self):
        return self.normalize()._normalize_string(self.start_element.text_content())


class DiffContent:

    ignore_empty_differences = True

    comparison_result_class = namedtuple('ComparisonResult',
                                         ['tag', 'a_index', 'a_diff', 'b_index', 'b_diff', 'diff_ex'],
                                         defaults=('', -1, '', -1, '', '')
                                         )

    def __init__(self, a, b) -> None:
        self.a = str(NormalizeContent(a)) if isinstance(a, _Element) else NormalizeContent._normalize_string(str(a))
        self.b = str(NormalizeContent(b)) if isinstance(a, _Element) else NormalizeContent._normalize_string(str(b))
        self.sequence_matcher = difflib.SequenceMatcher(a=self.a, b=self.b)
        super().__init__()

    def compare(self):

        def get_diff_ex(s, bi, ei):
            magic_const = 10
            result = ''
            if bi != ei and ei - bi < magic_const:
                bi = bi - magic_const if bi - magic_const >= 0 else 0
                ei += magic_const
                result = s[bi:ei]

            return result

        seq_match = self.sequence_matcher
        result = []
        for tag, a_bi, a_ei, b_bi, b_ei in seq_match.get_opcodes():
            # tag is one of theses ('replace', 'delete', 'insert', 'equal')
            if tag != 'equal':
                adif = seq_match.a[a_bi:a_ei]
                bdif = seq_match.b[b_bi:b_ei]
                if self.ignore_empty_differences:
                    adif = adif.strip()
                    bdif = bdif.strip()
                if adif != bdif:
                    if adif:
                        dif_ex = get_diff_ex(seq_match.a, a_bi, a_ei)
                    else:
                        dif_ex = get_diff_ex(seq_match.b, b_bi, b_ei)
                    result.append(self.comparison_result_class(tag, a_bi, adif, b_bi, bdif, dif_ex))
        return result

    def is_equal(self):
        return not self.compare()

    def ratio(self):
        return self.sequence_matcher.ratio()


if __name__ == '__main__':

    from lib.ssl_provider import GetResponse
    from lib.post_text_compare import BodyTextSelector
    import lxml.html

    url = 'http://blog.lan/entry/9/?text=1'
    file = '../work.result/Debian/OpenSSL/OpenSSL config files.html'

    content = GetResponse(url).process()
    a_el = tuple(BodyTextSelector(content))
    if len(a_el) != 1:
        raise ValueError('Something went wrong. Post\'s text should be exact one.')

    b_el = None
    with open(file, mode='r', encoding='utf8') as fd:
        b_el = lxml.html.parse(fd).getroot().body

    diff = DiffContent(a_el[0], b_el)

    print(url, '->', file)
    diff_res = diff.compare()
    print('Equal:', True if not diff_res else False)
    print('Ratio:', diff.ratio())
    if diff_res:
        print('Differences:', "\n", diff_res)

# Result Should be
#
# http://blog.lan/entry/9/?text=1 ->
#   /home/ox23/PycharmProjects/py-post-parser/work.result/Debian/OpenSSL/OpenSSL config files.html
# Equal: False
# Ratio: 0.9914492112634528
# Differences:
#  [ComparisonResult(
#       tag='insert',
#       a_index=5565,
#       a_diff='',
#       b_index=5576,
#       b_diff='The following file properties are converted to META tags when you export a file as an HTML document:'
#   )]

