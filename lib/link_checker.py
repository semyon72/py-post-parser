# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: link_checker.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

import re
from collections.abc import Iterable
from http.client import HTTPResponse
from urllib.error import URLError
from urllib.parse import urlparse, urlunparse, quote, parse_qsl, urlencode
from urllib.request import Request

from lib.ssl_provider import GetResponse
from lib.grabber import LinksGrabber


class LinkCheckerBase:
    """
        It uses

        'https://blog.lan/?page=1'
    """

    ignore_querystring = False

    quote_url = True

    process_relative_url = True

    link_grabber_class = LinksGrabber

    def __init__(self, link_grabber=None, grabber_start_url=''):
        """
            grabber_start_url will be used at instantiation
            link_grabber, either using link_grabber_class or
            link_grabber property will take the grabber as class
        """
        self.grabber_start_url = grabber_start_url
        self.link_grabber = link_grabber
        # __checked_urls is dict where key is url and value is response's (status, reason) 2-tuple
        self.__checked_urls = {}
        super().__init__()

    @property
    def grabber_start_url(self):
        return self.__grabber_start_url

    @grabber_start_url.setter
    def grabber_start_url(self, url):
        url = '' if url is None else urlunparse(urlparse(url))
        self.__grabber_start_url = url

    @property
    def link_grabber(self):
        return self.__link_grabber

    @link_grabber.setter
    def link_grabber(self, grabber):
        if grabber is None:
            self.__link_grabber = self.link_grabber_class(self.grabber_start_url)
        elif isinstance(grabber, Iterable):
            self.__link_grabber = grabber
        elif isinstance(grabber, type) and issubclass(grabber, LinksGrabber):
            self.__link_grabber = grabber(self.grabber_start_url)
        else:
            raise ValueError('link_grabber should be Iterable that returns url on each iteration.'
                             ' It can be list, for example, or a descendant of LinksGrabber'
                             ' or an instance of it')

    def _quote_url(self, parsed_url):
        purl = parsed_url
        if self.quote_url:
            path = purl.path
            # test on validity https://www.rfc-editor.org/rfc/rfc3986
            if not purl.path.isascii() or re.search(r"\s", purl.path):
                path = quote(path)
            # no need to test on validity, urlencode works properly
            query = urlencode(parse_qsl(purl.query))
            purl = purl._replace(path=path, query=query)
        return purl

    def _process_relative_url(self, parsed_url):
        purl = parsed_url
        if self.process_relative_url:
            if not purl.scheme:
                ppurl = urlparse(self.link_grabber.current_start_url)
                purl = purl._replace(scheme=ppurl.scheme, netloc=ppurl.netloc)

        return purl

    def _ignore_querystring(self, parsed_url):
        _purl = parsed_url
        if self.ignore_querystring:
            _purl = _purl._replace(params='', query='', fragment='')

        return _purl

    def process_url(self, url):
        purl = urlparse(url)
        purl = self._ignore_querystring(purl)
        purl = self._process_relative_url(purl)
        purl = self._quote_url(purl)
        return urlunparse(purl)

    @property
    def checked_urls(self):
        return self.__checked_urls

    def _check_url(self, url, page_url, isprocessed=False):
        """
            @page_url is page where was found url
            @url is link like <a href='cvzcvzcx'> or <img src='cvzcvzcx'>
            @isprocessed is a pointer on url was processed or not before

            @returns 2-tuple ((status, reason), Response object)
        """

        if isprocessed:
            result = self.checked_urls.get(url, (0, 'looks like processed, but - ERROR'))
            return (result[0], result[1]+' - Checked already'), None

        try:
            resp = GetResponse(Request(url, method='HEAD')).process()
            if isinstance(resp, HTTPResponse):
                # Fix for cases: A web site's link points at local resource,
                # for example file:///..... and if it exists then a resp will return a file handler
                # to this file but this behaviour is not wished.
                if resp.status == 405:
                    resp = GetResponse(Request(url, method='GET')).process()
            else:
                raise URLError('not HTTPResponse returned')
        except URLError as err:
            # if connection wrong, server does not exists
            resp, result = (None, (0, err.reason))
        else:
            result = (resp.status, resp.reason)

        self.checked_urls[url] = result

        return result, resp

    def _process_urls(self):
        """
            Iterate over self.link_grabber and on each link on page
            to execute self._check_url(url, page_url, isprocessed=False)
            page_url is page where was found url
            and url is link like <a href='cvzcvzcx'> or <img src='cvzcvzcx'>
            but defined by self.link_provider. As rule It is descendant ContentSelector
        """
        self.checked_urls.clear()
        for url in self.__link_grabber:
            _url = self.process_url(url)
            if not _url:
                continue

            params = [_url, getattr(self.__link_grabber, 'current_start_url', None)]
            if _url in self.checked_urls:
                # url was processed
                params.append(True)

            self._check_url(*params)
        return self

    def check(self):
        return self._process_urls()


class LoggedLinkCheckerMixin:

    indentation = ' '*4

    unknown_page_message = 'Unknown page'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__current_page = None

    def _check_url(self, url, page_url, isprocessed=False):
        result, resp = super()._check_url(url, page_url, isprocessed)
        if self.__current_page != page_url:
            self.__current_page = page_url
            if self.__current_page is None:
                page_url = self.unknown_page_message

            print('current page: {}'.format(page_url))

        print('{}{}: status={}, reason: {}'.format(self.indentation, url, result[0], result[1]))
        return result, resp

    def _process_urls(self):
        self.__current_page = None
        return super()._process_urls()


class LoggedLinkCheckerBase(LoggedLinkCheckerMixin, LinkCheckerBase):
    pass


class LinkChecker(LinkCheckerBase):
    """
        This class is a simplifier for using LinkCheckerBase in declarative manner
        or by using the from_urls class method
    """

    link_provider_class = None

    page_provider_class = None

    def __init__(self, start_url='', link_provider=None, page_provider=None):
        super().__init__(grabber_start_url=start_url)
        self.link_provider = link_provider
        self.page_provider = page_provider

    def _init_provider(self, value, provider_name):
        class_val = getattr(self, provider_name + '_class')
        if value is None and class_val is not None:
            value = class_val()
        return value

    @property
    def link_provider(self):
        return self.link_grabber.link_provider

    @link_provider.setter
    def link_provider(self, value):
        self.link_grabber.link_provider = self._init_provider(value, 'link_provider')

    @property
    def page_provider(self):
        return self.link_grabber.page_provider

    @page_provider.setter
    def page_provider(self, value):
        self.link_grabber.page_provider = self._init_provider(value, 'page_provider')

    @classmethod
    def from_urls(cls, urls, link_provider=None):
        """
            It returns instance of itself class.
        """
        if isinstance(urls, str):
            start_url, page_provider = (urls, None)
        elif isinstance(urls, Iterable):
            iurls = iter(urls)
            start_url = next(iurls, None)
            if start_url is None:
                raise ValueError('page_provider should have at least one url')
            page_provider = [url for url in iurls]
        else:
            raise ValueError('urls should be either iterable or string')
        self = cls(start_url, page_provider=page_provider, link_provider=link_provider)
        return self


class LoggedLinkChecker(LoggedLinkCheckerMixin, LinkChecker):
    pass


if __name__ == '__main__':

    from lib.post_text_compare import TextsLinksProvider, PagerProvider

    class LoggedTextLinkChecker(LoggedLinkCheckerMixin, LinkChecker):
        link_provider_class = TextsLinksProvider
        page_provider_class = PagerProvider


    urls = ['https://blog.lan/?page=1', 'https://blog.lan/?page=2',
            'https://blog.lan/?page=3', 'https://blog.lan/?page=2',
            'https://blog.lan/?page=4']

    print('#start over iterable - LoggedLinkCheckerBase')
    LoggedLinkCheckerBase(urls).check()
    print('#test passed')

    class TextLinksGrabber(LinksGrabber):
        page_provider_class = PagerProvider
        link_provider_class = TextsLinksProvider

    print('#start over class grabber - LoggedLinkCheckerBase')
    LoggedLinkCheckerBase(TextLinksGrabber, urls[0]).check()
    print('#test passed')

    print('#start over class grabber - LoggedLinkCheckerBase')
    LoggedLinkCheckerBase(TextLinksGrabber, urls[0]).check()
    print('#test passed')

    print('#start over grabber\'s instance - LoggedLinkCheckerBase')
    LoggedLinkCheckerBase(TextLinksGrabber(urls[0])).check()
    print('#test passed')

    class PredefinedLoggedLinkCheckerBase(LoggedLinkCheckerBase):
        link_grabber_class = TextLinksGrabber

    print('#start over custom grabber - PredefinedLoggedLinkCheckerBase')
    PredefinedLoggedLinkCheckerBase(grabber_start_url=urls[0]).check()
    print('#test passed')

    print('#start over the changing of properties - LoggedLinkCheckerBase')
    checker = LoggedLinkCheckerBase()
    print('empty checker is created')
    checker.link_grabber = urls
    print('checker.link_grabber = urls - iterable')
    print('# checking')
    checker.check()
    print('# passed')
    print('preset checker.grabber_start_url = urls[0] - it will used on reset to default grabber')
    checker.grabber_start_url = urls[0]
    print('checker.link_grabber = None - reset to default')
    checker.link_grabber = None
    print('checker.link_grabber.link_provider = TextsLinksProvider()')
    checker.link_grabber.link_provider = TextsLinksProvider()
    print('checker.link_grabber.page_provider = PagerProvider()')
    checker.link_grabber.page_provider = PagerProvider()
    print('# checking')
    checker.check()
    print('# passed')
    checker.link_grabber = TextLinksGrabber
    print('# checker.link_grabber = TextLinksGrabber')
    print('# checking')
    checker.check()
    print('# passed')
    custom_grabber = TextLinksGrabber(start_url=urls[0])
    print('# checker.link_grabber = TextLinksGrabber(start_url=urls[0])')
    print('# checking')
    checker.check()
    print('# passed')

    print('Start LoggedTextLinkChecker(urls[0]). - common case')
    LoggedTextLinkChecker(urls[0]).check()
    print('# passed')

    print('Start LoggedTextLinkChecker.page_provider is None. - one page checking')
    LoggedTextLinkChecker.page_provider_class = None
    LoggedTextLinkChecker(urls[0]).check()
    print('# passed')

    print('Start iterable as page_provider.')
    LoggedTextLinkChecker.page_provider_class = None
    text_link_checker = LoggedTextLinkChecker.from_urls(urls)
    text_link_checker.check()
    print('---- End iterable as page_provider.')
