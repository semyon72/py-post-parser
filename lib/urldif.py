# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: urldif.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from collections.abc import Mapping
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse


PLUS = '+'
MINUS = '-'
NOTEQUAL = '!'
EQUAL = '='

PATH_SEPARATOR = '/'


def diff_dict(cur: Mapping, other: Mapping):
    if not isinstance(cur, Mapping) or not isinstance(other, Mapping):
        raise Exception('Both arguments must be Mapping.')
    res = {}

    cur_keys, other_keys = (set(cur), set(other))
    ckex, okex = (cur_keys - other_keys, other_keys - cur_keys)
    res[MINUS] = {k: cur[k] for k in ckex} if len(ckex) > 0 else None
    res[PLUS] = {k: other[k] for k in okex} if len(okex) > 0 else None

    com_keys = tuple(cur_keys & other_keys)

    # Comparison part
    neq, eq = ({}, {})
    for i in com_keys:
        td = eq
        if cur[i] != other[i]:
            td = neq
        td[i] = cur[i]

    res[NOTEQUAL] = neq if len(neq) > 0 else None
    res[EQUAL] = eq if len(eq) > 0 else None

    return res


def diff_path(cur: str, other: str):
    c = dict(enumerate((i for i in str(cur).split(PATH_SEPARATOR) if i)))
    o = dict(enumerate((i for i in str(other).split(PATH_SEPARATOR) if i)))
    return diff_dict(c, o)


def diff_qs(cur: str, other: str):
    c = parse_qs(str(cur), True)
    o = parse_qs(str(other), True)
    return diff_dict(c, o)


class UrlDiff:
    """
    It allows to compare 2 urls. Other facilities suppose on the 1st url is current.
    Thus, diffs (read) - shows information relatively to current (1st) url in __init__,

          diffs (setter) - accepts new 'other' url. If need to compare current url with
          second 'other' then need to assign an instance.diffs a new 'other' url.

          get_differences() - shows a differences current (1st) url relatively to 'other'.

          compose() - assembles url for (1st) url that was passed in __init__
    """
    '''
    And some examples about subtleties of urllib.parse for info:

    urlparse('http://site.com/path/name;param1;p2;p3;array=23,34,56?qs=1&qs=2')
    RESULT: ParseResult(scheme='http', netloc='site.com', path='/path/name', params='param1;p2;p3;array=23,34,56',
                        query='qs=1&qs=2', fragment='')

    urlsplit('http://site.com/path/name;param1;p2;p3;array=23,34,56?qs=1&qs=2')
    RESULT: SplitResult(scheme='http', netloc='site.com', path='/path/name;param1;p2;p3;array=23,34,56',
                        query='qs=1&qs=2', fragment='')

    urlencode([('qs',1),('qs',2),('qs',' some Что dif lang ')])
    RESULT: 'qs=1&qs=2&qs=+some+%D0%A7%D1%82%D0%BE+dif+lang+'
    urlencode({'with': [''], 'extra': ['extraval']}, doseq=True)
    RESULT: 'with=&extra=extraval'
    BUT -> urlencode({'with': [''], 'extra': ['extraval']})
    RESULT: 'with=%5B%27%27%5D&extra=%5B%27extraval%27%5D'

    If nup has value
    nup -> ParseResult(
        scheme='http',
        netloc='site.com', 
        path='/path/name', 
        params='param1;p2;p3;array=23,34,56', 
        query='qs=1&qs=2&qs=+some+%D0%A7%D1%82%D0%BE+dif+lang+', fragment=''
    )
    urlunparse(nup)
    RESULT: 'http://site.com/path/name;param1;p2;p3;array=23,34,56?qs=1&qs=2&qs=+some+%D0%A7%D1%82%D0%BE+dif+lang+'
    '''
    def __init__(self, url: str, other: str) -> None:
        self.__parsed_url = urlparse(url)
        self.__path_has_trailing_slash = True if len(self.__parsed_url.path[-1:]) > 0 else False
        self.__path_has_lead_slash = True if len(self.__parsed_url.path[:1]) > 0 else False
        self.__diffs = None
        self.diffs = other
        super().__init__()

    @property
    def parsed_url(self):
        return self.__parsed_url
    #
    # def _diff_path(self, other):
    #     return diff_path(self.__parsed_url.path, other.parsed_url.path)
    #
    # def _diff_qs(self, other):
    #     return diff_qs(self.__parsed_url.query, other.parsed_url.query)

    @property
    def diffs(self):
        """
            Returns dict where keys is PLUS, MINUS, EQUAL, NOTEQUAL each of these
            is dict where:
                int keys - index in path
                text keys - parameter in query string
        """
        return self.__diffs

    @diffs.setter
    def diffs(self, other):
        if not other:
            self.__diffs = None
            return

        other = urlparse(str(other))
        pd = diff_path(self.__parsed_url.path, other.path)
        qs = diff_qs(self.__parsed_url.query, other.query)
        for k, v in pd.items():
            if v:
                if qs[k]:
                    v.update(qs[k])
            elif qs[k]:
                v = qs[k]
            pd[k] = v
        res = pd
        self.__diffs = res
        # next line is mandatory and is related to the behaviour of 'url_asdict' property and its name
        self.__dict__.pop('url_asdict', None)

    def get_differences(self):
        """
            Returns diffs without EQUAL key and only those where value is not empty
        """
        if not self.diffs:
            raise ValueError('Property "diffs" does not contain value. You should assign some not empty url.')
        return {k: v for k, v in self.diffs.items() if v and k != EQUAL}

    @property
    def url_asdict(self):
        """
            Something like cached property for object.
        """
        prop_name = 'url_asdict'
        if prop_name in self.__dict__:
            res = self.__dict__[prop_name]
        else:
            res = {k: v for val in (v for k, v in self.diffs.items() if k != PLUS and v) for k, v in val.items()}
            self.__dict__[prop_name] = res
        return res

    def compose(self, kwargs: Mapping = None):
        """
            Return 2-tuple (path, query)
            At now, diffs contains something like
            {
             '-': None,
             '+': {'with': ['']},
             '!': {'page': ['1'], 'next_val': ['nextval']},
             '=': {0: 'some', 1: 'url', 2: 'path', 'dbl_val': ['one', 'two']}
             }
             '+' - contains values that exists in other but are absent in current.
             We do not need this part to compose url - /some/path/?q=rrrr
             All other  - contain information that describe current url
             Numerical (int) keys are path's parts and string keys are query string parts

             kwargs - dictionary for redefining values and parameters.
        """
        query_diffs = dict(self.url_asdict)
        if kwargs:
            query_diffs.update(kwargs)

        path, cidx = ([], 0)
        for k, v in sorted(query_diffs.items(), key=lambda i: hash(i[0])):
            if isinstance(k, int):
                if k != cidx:
                    raise ValueError('Path should be sequential but exist gap on index "{}"'.format(k))
                path.append(str(v))
                cidx += 1
                del query_diffs[k]

        path = PATH_SEPARATOR.join(path)
        if path and self.__path_has_trailing_slash:
            path += PATH_SEPARATOR
        if path and self.__path_has_lead_slash:
            path = PATH_SEPARATOR + path

        return path, urlencode(query_diffs, doseq=True)

    def unparse(self, kwargs: Mapping = None):
        new = self.__parsed_url._replace(**dict(zip(('path', 'query'), self.compose(kwargs))))
        return urlunparse(new)

    def __getitem__(self, item):
        query_diffs = self.url_asdict
        return query_diffs[item]


if __name__ == '__main__':

    url_paths = (
        ('https://test.blog.lan/?page=2',
         'https://test.blog.lan/?page=2',
         {'+': None, '-': None, '!': None, '=': None}),
        ('https://test.blog.lan/some/url/path/?page=2',
         'https://test.blog.lan/some/url/path/?page=2',
         {'+': None, '-': None, '!': None, '=': {0: 'some', 1: 'url', 2: 'path'}}),
        ('https://test.blog.lan/some/url/path?page=2',
         'https://test.blog.lan/some/url/path/with/extra/?page=2',
         {'+': {3: 'with', 4: 'extra'}, '-': None, '!': None, '=': {0: 'some', 1: 'url', 2: 'path'}}),
        ('https://test.blog.lan/some/url/path/with/extra?page=2',
         'https://test.blog.lan/some/url/path/?page=2',
         {'+': None, '-': {3: 'with', 4: 'extra'}, '!': None, '=': {0: 'some', 1: 'url', 2: 'path'}}),
        ('https://test.blog.lan/some/url_changed/path/with/?page=2',
         'https://test.blog.lan/some/url/path_changed/with/extra/?page=2',
         {'+': {4: 'extra'}, '-': None, '!': {1: 'url_changed', 2: 'path'}, '=': {0: 'some', 3: 'with'}}),
    )

    url_qs = (
        ('https://test.blog.lan/',
         'https://test.blog.lan',
         {'+': None, '-': None, '!': None, '=': None}),
        ('https://test.blog.lan/some/url/path/?page=2',
         'https://test.blog.lan/some/url/path/?page=2',
         {'+': None, '-': None, '!': None, '=': {'page': ['2']}}),
        ('https://test.blog.lan/some/url/path/with/extra/?page=2',
         'https://test.blog.lan/some/url/path?page=2&with=&extra=extraval',
         {'+': {'with': [''], 'extra': ['extraval']}, '-': None, '!': None, '=': {'page': ['2']}}),
        ('https://test.blog.lan/some/url/path?page=2&with=&extra=extraval&some=1',
         'https://test.blog.lan/some/url/path/?page=2&some=1',
         {'+': None, '-': {'with': [''], 'extra': ['extraval']}, '!': None, '=': {'page': ['2'], 'some': ['1']}}),

        ('https://test.blog.lan/some/url/path/?page=1&next_val=nextval&dbl_val=one&dbl_val=two',
         'https://test.blog.lan/some/url/path?dbl_val=one&dbl_val=two&page=2&with=&next_val=nextval_dif_val',
         {'+': {'with': ['']}, '-': None, '!': {'page': ['1'], 'next_val': ['nextval']},
          '=': {'dbl_val': ['one', 'two']}}),
    )

    def url_path_test(urls, dif_func=diff_path):
        for p in urls:
            if dif_func is diff_path:
                arg0 = urlparse(p[0]).path
                arg1 = urlparse(p[1]).path
            else:
                arg0 = urlparse(p[0]).query
                arg1 = urlparse(p[1]).query
            diff = dif_func(arg0, arg1)
            print('For url "{0}" and "{1}" diff result is "{2}"'.format(p[0], p[1], diff))
            if diff != p[2]:
                raise ValueError('For url "{0}" and "{1}" diff should be "{2}" but result is "{3}"'.format(
                    p[0], p[1], p[2], diff
                ))

    print('##### test the diff_path function for paths')
    url_path_test(url_paths)

    print('##### test the diff_qs function for urls')
    url_path_test(url_qs, diff_qs)

    print('##### test for UrlDiff')
    url_current = url_qs[4][0]
    url_other = url_qs[4][1]
    udiff = UrlDiff(url_current, url_other)

    diffs_test_val = {'-': None, '+': {'with': ['']}, '!': {'page': ['1'], 'next_val': ['nextval']},
                      '=': {0: 'some', 1: 'url', 2: 'path', 'dbl_val': ['one', 'two']}}
    print('For url "{}" and "{}" UrlDiff.diffs is {}'.format(url_current, url_other, udiff.diffs))
    if str(udiff.diffs) != str(diffs_test_val):
        raise ValueError(
            'For url "{}" and "{}" UrlDiff.diffs should be {}'.format(url_current, url_other, diffs_test_val)
        )

    get_differences_test_val = {'+': {'with': ['']}, '!': {'page': ['1'], 'next_val': ['nextval']}}
    print('For url "{}" and "{}" UrlDiff.get_differences() is {}'.format(
        url_current, url_other, udiff.get_differences())
    )
    if str(udiff.get_differences()) != str(get_differences_test_val):
        raise ValueError(
            'For url "{}" and "{}" UrlDiff.get_differences() should be {}'.format(
                url_current, url_other, get_differences_test_val
            )
        )

    url_res = urlparse(url_current)
    new_res = url_res._replace(**dict(zip(('path', 'query'), udiff.compose())))
    print('For url "{}" is composed url "{}".'.format(urlunparse(url_res), urlunparse(new_res)))
    if url_res != new_res:
        raise ValueError('Result of composing is not same as original.')

    test_url = "https://test.blog.lan/some/url_modified/path/?page=24&next_val=nextval&dbl_val=one&dbl_val=two"
    url_res = urlparse(test_url)
    new_res = url_res._replace(**dict(zip(('path', 'query'), udiff.compose({'page': 24, 1: 'url_modified'}))))
    print('For url "{}" is composed url "{}".'.format(urlunparse(url_res), urlunparse(new_res)))
    if url_res != new_res:
        raise ValueError('Result of composing is not same as original.')
