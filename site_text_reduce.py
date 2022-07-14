# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: site_text_reduce.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

import argparse
import os
from timeit import Timer

from lib.file_provider import GetFiles
from lib.post_html_reduce import PostHTMLReduce


def main():
    parser = argparse.ArgumentParser(description='Reduce a junks of post\'s texts file sources.')
    parser.add_argument('--dir', '-d', type=str, nargs='?', help='directory where source html files.')
    parser.add_argument('--file', '-f', type=str, nargs='?', help='source html file.')
    parser.add_argument('--keep-source', '-ks', nargs='?', type=bool,
                        help='Keep source files with *.src extension.',
                        default=True
                        )
    args = parser.parse_args()

    files = GetFiles()
    if args.file:
        if args.dir:
            print('It will process parameter --file. Parameter --dir will be ignored.')
        files.root_path = args.file
    elif args.dir:
        files.root_path = args.dir
        files.filters_allow.insert(0, lambda f: os.path.basename(f).endswith('.html') if os.path.isfile(f) else None)
    else:
        raise ValueError('One of arguments --dir or --file should be used.')

    reducer = PostHTMLReduce()
    for file in files:
        reducer.load(file).reduce_content()
        if args.keep_source:
            print('Process :{}'.format(file))
            os.replace(file, os.path.join(os.path.dirname(file), '~'+os.path.basename(file)+'.src'))
        reducer.write(file)


if __name__ == '__main__':
    t = Timer(main)
    print('Execution info (sec):', t.timeit(1))
