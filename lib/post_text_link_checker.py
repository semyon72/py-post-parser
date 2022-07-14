# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: post_text_link_checker.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from urllib.parse import urlunparse, urlparse

from lib.grabber import ContentSelector
from lib.link_checker import LoggedLinkCheckerMixin, LinkChecker
from lib.post_text_compare import PagerProvider


class TextLinkSelector(ContentSelector):
    # selector = 'div.body_content article section.card-body.entry-text :is(a[href], img[src])'
    # construction above is not supported by lxml + cssselect (1.1.0) package
    selector = 'div.body_content article section.card-body.entry-text img[src], '\
               'div.body_content article section.card-body.entry-text a[href]'


class PostTextLinkChecker(LinkChecker):

    link_provider_class = TextLinkSelector
    page_provider_class = PagerProvider


class LoggedPostTextLinkChecker(LoggedLinkCheckerMixin, PostTextLinkChecker):

    def _is_link_a(self, ltype='a'):
        el = self.link_provider.current_element
        return el is not None and el.tag == ltype

    def _is_link_local(self, url):
        clr = {'path': '', 'params': '', 'query': '', 'fragment': ''}
        rcurl = urlunparse(urlparse(self.link_grabber.current_start_url)._replace(**clr))
        rurl = urlunparse(urlparse(url)._replace(**clr))
        return rcurl == rurl

    CHECK_LINK_TYPES = {
        'all': lambda self, url: url,
        'local': lambda self, url: url if self._is_link_local(url) else None,
        'external': lambda self, url: url if not self._is_link_local(url) else None,
        'img': lambda self, url: url if self._is_link_a('img') else None,
        'local_img': lambda self, url: url if self._is_link_a('img') and self._is_link_local(url) else None,
        'external_img': lambda self, url: url if self._is_link_a('img') and not self._is_link_local(url) else None,
        'a': lambda self, url: url if self._is_link_a('a') else None,
        'local_a': lambda self, url: url if self._is_link_a('a') and self._is_link_local(url) else None,
        'external_a': lambda self, url: url if self._is_link_a('a') and not self._is_link_local(url) else None
    }

    check_link_type = 'all'

    def process_url(self, url):
        # if url is empty it will skip a checking
        func = self.CHECK_LINK_TYPES.get(self.check_link_type)
        if not callable(func):
            raise ValueError('check_link_type is {} but must be one of {}'.format(
                self.check_link_type, self.CHECK_LINK_TYPES.keys()
            ))
        url = func(self, url)
        if url:
            url = super().process_url(url)

        return url
