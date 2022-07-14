# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: site_text_compare.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

"""
Grab site texts and compare with their source files.
-h or --help for usage.
"""

import argparse
import os
from timeit import Timer

from lib.html_tools import DiffContent
from lib.post_text_compare import LoggedPostTextsComparer
from urllib.parse import urlparse

from lib.post_text_link_checker import LoggedPostTextLinkChecker


def main():
    parser = argparse.ArgumentParser(description='Compare texts from site to file sources.')
    parser.add_argument('--url', '-u', type=str, nargs='?',  help='source url.')
    parser.add_argument('--dir', '-d', type=str, nargs='?', help='directory where source html file.')
    parser.add_argument('--relations', '-rel', nargs='?', type=str,
                        help='resulting file of the comparison.',
                        default='relations.txt'
                        )
    parser.add_argument('--check-links', '-cl', help='check links',
                        choices=[*LoggedPostTextLinkChecker.CHECK_LINK_TYPES]
                        )

    args = parser.parse_args()

    if not args.dir and not args.url:
        # returns information from relation file
        default_indent = " " * 4
        post_comp = LoggedPostTextsComparer('', '', args.relations if args.relations else None)
        if args.check_links:
            print('Running validation of "{}" links'.format(args.check_links))
            urls = (rel.url for rel in post_comp.relations if rel.url)
            checker = LoggedPostTextLinkChecker.from_urls(urls)
            checker.check_link_type = args.check_links
            checker.check()
        else:
            for i, rel in enumerate(post_comp.relations):
                print('{}:'.format(i+1), rel.url, '->', rel.file)
                indent = default_indent
                print(indent + 'Ratio:', rel.ratio)
                if len(rel.diff):
                    print(indent + 'Differences:')
                for dif in rel.diff:
                    tdif = DiffContent.comparison_result_class(*dif)
                    msg = '{indent}{tag}: i:{a_index} "{a_diff}" -> i:{b_index} "{b_diff}"'
                    if tdif.diff_ex:
                        msg += ' [...{diff_ex}...]'
                    print(msg.format(indent=indent * 2, **tdif._asdict()))
        exit(0)

    # --url = "https://blog.lan/?page=1" - -dir = "work.result"
    if not os.path.isdir(args.dir):
        raise FileNotFoundError('Directory containing source files for the site must exists.')

    url = urlparse(args.url)
    if not url.netloc:
        raise ValueError('Url should be valid url.')

    post_comp = LoggedPostTextsComparer(args.url, args.dir, args.relations if args.relations else None).compare()
    post_comp.dump_relations()
    print('Details of comparison see in {} or rerun without parameters.'.format(post_comp.relation_file_name))


if __name__ == '__main__':
    t = Timer(main)
    print('Execution info (sec):', t.timeit(1))
