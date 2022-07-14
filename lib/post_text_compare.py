# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: post_text_compare.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

"""
    Site content grabber
"""
import sys
import lxml.html
import lxml.etree
import json

from json.decoder import JSONDecodeError
from time import sleep
from timeit import Timer
from collections import namedtuple
from os.path import isfile, basename

from lib.file_provider import GetFiles
from lib.grabber import LinksGrabber, ContentSelector
from lib.html_tools import DiffContent, NormalizeContent
from lib.ssl_provider import GetResponse


class TextsLinksProvider(ContentSelector):
    """
        Iterator that provides links over one page
    """
    selector = 'article.card section.card-body.entry-text div.body-text a.btn'


class PagerProvider(ContentSelector):
    """
        Iterator that provides links over page navigator pages
    """
    selector = 'div.body_content > nav li.page-item a.page-link'


class TextLinksGrabber(LinksGrabber):
    """
        It can duplicate text's links due to 'https://test.blog.lan/' and 'https://test.blog.lan/?page=1'
        can be same pages as for server but grabber counts this links as different.
        It can be fixed if a start url will be 'https://test.blog.lan/?page=1'. In other words,
        like url for first page in pager.
    """
    link_provider_class = TextsLinksProvider
    page_provider_class = PagerProvider


class BodyTextSelector(ContentSelector):
    selector = 'article.card section.card-body.entry-text div.body-text'


class PostTextsComparer:
    """
        'https://blog.lan/?page=1'
    """

    relations_file_name = 'relations.txt'

    ratio_limit = 0.75

    relation_item_class = namedtuple('RelationItem', ['url', 'file', 'ratio', 'diff'], defaults=('', '', 0, []))

    def __init__(self, start_url, files_dir, relations_file_name=None) -> None:
        self.__relations = []
        self.__relations_file_name = relations_file_name or self.relations_file_name
        self.load_relations(self.__relations_file_name)
        self.start_url = start_url
        self.files_dir = files_dir
        super().__init__()

    @property
    def relation_file_name(self):
        return self.__relations_file_name

    def urls(self):
        return set(TextLinksGrabber(self.start_url))

    def files(self):

        def filter_func(file):
            if isfile(file):
                return basename(file).endswith('.html')

        file_provider = GetFiles(self.files_dir)
        file_provider.filters_allow.insert(0, filter_func)
        return set(file_provider)

    @property
    def relations(self):
        """
            List of items each of which is a named tuple like a dictionary
            { 'url': 'http://some.site/url/path?query=string',
              'file': '/some/path/to/file.html',
              'ratio': [0.0 - 1.0],
              'diff': [('insert', 'some content'), ('replace', 'some content'), ('delete', 'some content')]
            }
            'url' can be empty in same time when 'file' exists - file, probably, have not related content on site.
             Or, same but from other side, url have not content that correlates to anyone of files.
            'file' did not present but 'url' exists - same as above but in reversed meaning
        """
        return self.__relations

    def load_relations(self, file):
        if isfile(file):
            self.__relations_file_name = file
            with open(self.__relations_file_name, mode='r') as fd:
                try:
                    self.__relations = [self.relation_item_class(*item) for item in json.load(fd)]
                except JSONDecodeError as err:
                    err.args = (err.args[0] + '. File "{}"'.format(self.__relations_file_name), *err.args[1:])
                    raise err

        return self

    def dump_relations(self):
        if self.relations:
            indent = ' '*4
            with open(self.__relations_file_name, mode='w') as fd:
                fd.write("[\n")
                lrel = len(self.relations)
                for rel in self.relations:
                    lrel -= 1
                    fd.write("{}{}".format(indent, json.dumps(rel)))
                    if lrel > 0:
                        fd.write(',')
                    fd.write("\n")
                fd.write("]".format(indent))

    @staticmethod
    def _get_url_content(url) -> str:
        content = GetResponse(url).process()
        res_el = tuple(BodyTextSelector(content))
        if len(res_el) != 1:
            raise ValueError('Something went wrong. Post\'s text should be exact one.')
        return str(NormalizeContent(res_el[0]))

    @staticmethod
    def _get_file_content(file) -> str:
        with open(file, mode='r', encoding='utf8') as fd:
            res_str = str(NormalizeContent(lxml.html.parse(fd).getroot().body))
        return res_str

    def compare(self):
        urls = self.urls()
        files = self.files()

        related_urls = {item.url: item.file for item in self.relations if item.file}

        res_rel = []

        def _compare(a, b):
            diff = DiffContent(a=a, b=b)
            diff_res = diff.compare()
            res_item = self.relation_item_class(url=url, file=file, ratio=diff.ratio(), diff=diff_res)
            return res_item

        # pass through urls that have relations to files
        _urls = set(related_urls) & urls
        for url in _urls:
            file = related_urls.get(url)
            if file:
                res_item = _compare(self._get_url_content(url), self._get_file_content(file))
                res_rel.append(res_item)
                files.discard(file)

        # pass through other urls that have not relations to files
        urls = urls - _urls
        for url in urls:
            max_item = None
            a = self._get_url_content(url)
            for file in files:
                res_item = _compare(a, self._get_file_content(file))
                if max_item is None or res_item.ratio > max_item.ratio:
                    max_item = res_item
                if max_item.ratio == 1:
                    break

            if max_item and max_item.ratio > self.ratio_limit:
                res_rel.append(max_item)
                files.discard(max_item.file)
            else:
                res_rel.append(self.relation_item_class(url=url))

        # add files that have no relations to urls
        for file in files:
            res_rel.append(self.relation_item_class(file=file))

        self.__relations = res_rel
        return self


class LoggedPostTextsComparer(PostTextsComparer):

    sleep_time_for_render = 0.01
    ERASE_LINE = "\x1b[2K"
    CURSOR_UP_ONE = "\x1b[1A"

    def urls(self):
        print('Loading urls....')
        return super().urls()

    def files(self):
        print('Loading files....')
        return super().files()

    def load_relations(self, file):
        print('Loading relations....')
        return super().load_relations(file)

    def dump_relations(self):
        print('Dumping relations....')
        super().dump_relations()

    @staticmethod
    def _get_url_content(url) -> str:
        print('Getting content of {}'.format(url))
        return PostTextsComparer._get_url_content(url)

    @staticmethod
    def _get_file_content(file) -> str:
        sys.stdout.write("Getting content of {}".format(file))
        sys.stdout.flush()
        sleep(LoggedPostTextsComparer.sleep_time_for_render)
        result = PostTextsComparer._get_file_content(file)
        sys.stdout.write("\r{}".format(LoggedPostTextsComparer.ERASE_LINE))
        return result

    def compare(self):
        print('Starting comparison...')
        result = super().compare()
        return result


if __name__ == '__main__':

    url = 'http://blog.lan/?page=1'
    file = '../work.result'

    def exec_test(url, file):
        post_comp = LoggedPostTextsComparer(url, file).compare()
        post_comp.dump_relations()
        print('Details of comparison see in {}'.format(post_comp.relation_file_name))

    t = Timer('exec_test(url, file)', globals={'exec_test': exec_test, 'url': url, 'file': file})
    print('Execution info (sec):', t.timeit(1))

    # Result should be like above if run without relations.txt
    # Loading relations....
    # Starting comparison...
    # Loading urls....
    # Loading files....
    # Getting content of http://blog.lan/entry/7/?page=1&text=1
    # Getting content of http://blog.lan/entry/6/?page=1&text=1
    # Getting content of http://blog.lan/entry/3/?page=1&text=1
    # Getting content of http://blog.lan/entry/5/?page=1&text=1
    # Getting content of http://blog.lan/entry/2/?page=1&text=1
    # Getting content of http://blog.lan/entry/1/?page=1&text=1
    # Getting content of http://blog.lan/entry/8/?page=1&text=1
    # Getting content of http://blog.lan/entry/4/?page=1&text=1
    # Getting content of http://blog.lan/entry/9/?page=1&text=1
    # File usage cache info: CacheInfo(hits=223, misses=32, maxsize=32, currsize=32)
    # Dumping relations....
    # Details of comparison see in ./relations.txt
    # Execution info (sec): 57.446313866999844
