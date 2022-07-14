# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: grabber.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM


"""
    Site content grabber
"""
import io
import hashlib
from urllib.request import Request
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
from lxml.html import parse as html_parser
from lxml.etree import _Element
from typing import Iterable, Iterator, Union
from lib.ssl_provider import GetResponse
from http.client import HTTPResponse


def get_content_md5(content, remove_blanks=True):
    content = str(content)
    if remove_blanks:
        content = str(content.split()).encode()
    return hashlib.md5(content).hexdigest()


def iselement(el: _Element, name, attrs=None):
    result = False
    if el.tag == name:
        if attrs:
            for attr, val in attrs.items():
                if not attr or attr not in el.attrib:
                    break
                if val is not None and val != el.attrib[attr]:
                    break
            result = True
        else:
            result = True

    return result


def check_element(el: _Element, name, attrs=None, throw_exception=True):
    result = iselement(el, name, attrs)
    if not result and throw_exception:
        raise ValueError('Selector should points only on <a> tags.')
    return result


class ContentSelector(Iterable):
    selector = 'body'
    __content = None

    def __init__(self, content: Union[HTTPResponse, _Element, None] = None, selector=None) -> None:
        self.__current_element = None
        self.content = content

        if selector is not None:
            selector = str(selector).strip()
            if not selector:
                raise ValueError('Selector should be not an empty CSSselector string.')
            self.selector = selector

        super().__init__()

    @property
    def current_element(self):
        return self.__current_element

    @property
    def content(self):
        return self.__content

    @content.setter
    def content(self, value):
        if value is not None:
            if isinstance(value, (io.RawIOBase, io.BufferedIOBase)):
                value = html_parser(value).getroot()
            elif isinstance(value, _Element):
                pass
            else:
                raise ValueError('Content should have .read() method '
                                 'or instance of "{}" type.'.format(_Element.__name__))

        self.__content = value

    def process_element(self, el):
        return el

    def __iter__(self):
        for el in self.content.cssselect(self.selector):
            self.__current_element = el
            yield self.process_element(el)
        self.__current_element = None


class LinksGrabberResponseStatusIsNot200(Exception):
    pass


class LinksGrabber(Iterable):
    """
        It can duplicate text's links due to 'https://test.blog.lan/' and 'https://test.blog.lan/?page=1'
        can be same pages as for server but grabber counts this links as different.
        It can be fixed if a start url will be 'https://test.blog.lan/?page=1'. In other words,
        like url for first page in pager.

        For browser emulation it will add the 'headers' class argument as 'headers' parameter
        in urllib.request.Request(.... headers={} ....).
        Resulted object will be passed into urlopen(...) as 'url' parameter
    """

    element_url_attr = {'a': 'href', 'img': 'src'}

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0'
    }

    link_provider_class = None
    """
        Iterator that provides links over one page
    """

    page_provider_class = None
    """
        Iterator that provides links over page navigator pages
    """

    def __init__(self, start_url='', link_provider=None, page_provider=None) -> None:
        self.__current_start_url = None
        self.start_url = start_url
        self.link_provider = link_provider
        self.page_provider = page_provider
        super().__init__()

    def _init_provider(self, value, provider_name):
        inst = None
        if value is not None:
            # passed the class
            if isinstance(value, type):
                if not issubclass(value, ContentSelector):
                    raise TypeError('If {} is class then it must be ContentSelector subclass'.format(provider_name))
                inst = value()
            else:
                if provider_name == 'page_provider' and isinstance(value, Iterable):
                    # it is exclusion from rule. page_provider allows Iterable
                    pass
                elif not isinstance(value, ContentSelector):
                    raise ValueError(
                        'If {} is object then it must be ContentSelector instance'.format(provider_name)
                    )
                inst = value
        else:
            # set providers by default
            attr = getattr(self, provider_name + '_class')
            if attr is not None:
                if not issubclass(attr, ContentSelector):
                    raise TypeError(
                        'If {} has empty value then link_provider_class should be ContentSelector subclass'.format(
                            provider_name
                        )
                    )
                else:
                    inst = attr()
        return inst

    @property
    def link_provider(self):
        return self.__link_provider

    @link_provider.setter
    def link_provider(self, value):
        self.__link_provider = self._init_provider(value, 'link_provider')

    @property
    def page_provider(self):
        return self.__page_provider

    @page_provider.setter
    def page_provider(self, value):
        self.__page_provider = self._init_provider(value, 'page_provider')

    @property
    def current_start_url(self):
        return self.__current_start_url

    @property
    def start_url(self):
        return self.__start_url

    @start_url.setter
    def start_url(self, start_url):
        self.__start_url = urlunparse(urlparse(start_url))  # Just an url verification

    def _el2url(self, el):
        if el.tag in self.element_url_attr:
            attr = self.element_url_attr.get(el.tag)
            check_element(el, el.tag, {attr: None})

            # el.base_url is link on this page
            # but el.get(attr) for <a...> can be absolute url
            # urljoin resolve it
            return urljoin(el.base_url, el.get(attr))
        else:
            raise ValueError('tag {} is not supported by self.element_url_attr'.format(el.tag))

    def process_page_url(self, url):
        """
            This use only at time when grabbing (parsing) pager to get links of
            pages that follows by current one. This need for transformation url in comparable
            and valid form. For example - google.com uses only query string parameters
            'q' and 'start' but links at the same page will have different links in whole.
            Link on page 2 from page 3 or page 1 will not same.
            Example, how to fix it see below - GoogleLinksGrabber.process_page_url
        """
        return url

    def _iter_links(self, url, processed_urls):
        """
            It requests page from Web server by url then parse page
            and yield the links that defined by link_provider
        """
        if url not in processed_urls:
            resp = GetResponse(Request(url, headers=self.headers)).process()
            if resp.status == 200:
                self.link_provider.content = resp
                for text_url_el in self.link_provider:
                    yield self._el2url(text_url_el)
            else:
                raise LinksGrabberResponseStatusIsNot200(
                    'HTTPResponse returns status "{}" on url "{}".'.format(resp.status, url)
                )
            processed_urls.add(url)

    def _get_page_urls(self, page_provider, content, processed_urls: set):
        """
            The main purpose is process the content parameter to get paged links (if page has pager).
            To get a pager's links that point to the following pages, It uses page_provider.
            Also, it uses processed_urls to reduce duplication for paged links,
            if page_provider has not 'content' property then page_provider will return to back
            immediately, independent from the content's value.
        """
        new_page_urls = page_provider
        if hasattr(page_provider, 'content'):
            new_page_urls = []
            # need to parse the content to grab page's links
            page_provider.content = content

            for page_url_el in page_provider:
                page_url = page_url_el
                if isinstance(page_url_el, _Element):
                    check_element(page_url_el, 'a')
                    page_url = self._el2url(page_url_el)

                page_url = self.process_page_url(page_url)
                # page_url not in new_page_urls the fix if current page has link on itself
                if page_url not in processed_urls and page_url not in new_page_urls:
                    new_page_urls.append(page_url)
        return new_page_urls

    def __iter__(self) -> Iterator:
        processed_urls = set()
        page_urls = [self.start_url]
        while page_urls:
            # TODO: pop(0) could be reworked into len of iterable .... for save original
            # self.page_provider if it is list
            self.__current_start_url = page_urls.pop(0)
            # gets a content of current page (url) and yield links from
            yield from self._iter_links(self.__current_start_url, processed_urls)

            # get pager's links if last exists otherwise empty list or
            # self.page_provider if it simple iterable

            page_urls = self._get_page_urls(
                self.page_provider, getattr(self.link_provider, 'content', None), processed_urls
            )

        self.__current_start_url = None


class GoogleLinksProvider(ContentSelector):
    """
        Iterator that provides links over one page
    """
    selector = 'body div#search div.g > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > a[data-ved]'


class GooglePagerProvider(ContentSelector):
    """
        Iterator that provides links over page navigator pages
    """
    selector = 'div[role=navigation] table tr td a.fl'


class GoogleLinksGrabber(LinksGrabber):

    link_provider_class = GoogleLinksProvider

    page_provider_class = GooglePagerProvider

    def process_page_url(self, url):
        url = super().process_page_url(url)
        # for google need only 'q' and 'start' querystring parameters
        purl = urlparse(url, allow_fragments=False)
        qs = {key: val for key, val in parse_qs(purl.query).items() if key in ('q', 'start')}
        qs.setdefault('start', '0')
        return urlunparse(purl._replace(params='', query=urlencode(qs, doseq=True)))


if __name__ == '__main__':

    def test_grabber(link_grabber, max_links=35):
        print('### link grabber is started.')
        iterator = iter(link_grabber)
        for i in range(max_links):
            print('{}:{}'.format(i + 1, next(iterator)))
        print('### link grabber is done.')


    google_main_test_page = 'https://www.google.com/search?q=how+grabber+works&start=0'
    link_grab = GoogleLinksGrabber(google_main_test_page)
    test_grabber(link_grab, max_links=29)

    # Testing useful case when need parse all external links from certain pages
    class ExternalLinksProvider(ContentSelector):
        """
            Iterator that provides links over one page
        """
        selector = 'body a[href]'

    url_page_provider = [
        'https://en.wikipedia.org/wiki/Reach_extender',
        'https://www.bobvila.com/articles/best-grabber-tool/'
    ]
    link_grab.start_url = url_page_provider[0]
    link_grab.page_provider = url_page_provider[1:]
    link_grab.link_provider = ExternalLinksProvider()

    print('### link grabber is started.')
    i = (max_links_per_page := 23)
    is_start, prev_url = (True, None)
    for link in link_grab:
        if is_start:
            prev_url = link_grab.current_start_url
            is_start = False

        if link_grab.current_start_url == prev_url:
            i -= 1
        else:
            i = max_links_per_page - 1
            prev_url = link_grab.current_start_url
        if i < 0:
            continue
        print('{}:{}'.format(max_links_per_page - i, link))

    print('### link grabber is done.')
