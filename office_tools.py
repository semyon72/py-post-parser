# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: office_tools.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

"""
Converts files.
-h or --help for usage.

For convert one file into other it does something like a command line:
soffice --headless --convert-to "html:XHTML Writer File:UTF8" --convert-images-to "jpg" some_file.odt

"""
import shutil
import os.path
import re
import argparse
import tempfile

from lib import soffice
from lib.file_provider import GetFiles

# Values from the 'imghdr' package documentation.
IMG_TYPE_NAME = {'rgb', 'gif', 'pbm', 'pgm', 'ppm', 'tiff', 'rast', 'xbm', 'jpeg', 'bmp', 'png', 'webp', 'exr'}


def process_extra_files(src_file_name, target_dir):
    # This is fix for image files that will stored with different name
    # It happens up on conversion to html for example.
    src_dir, src_file_name = os.path.split(src_file_name)
    extra_files = os.listdir(src_dir)
    if len(extra_files) > 0:
        print('Process extra files:')
        for tfile in sorted(extra_files, key=lambda file: os.stat(os.path.join(src_dir, file)).st_mtime_ns):
            src_extra_file = os.path.join(src_dir, tfile)
            # No need to calculate crc32 because
            # soffice converter includes some checksum of content of image (extra) files already
            # for example /tmp/tmphb5r8qrp/OpenSSL certificate relations_html_5ecd9b4895629bde.png
            # 5ecd9b4895629bde - on each run is same
            #
            # if imghdr.what(src_extra_file) in IMG_TYPE_NAME:
            #     # if file is some image
            #     # calculate crc file and change the resulting file name
            #     with open(src_extra_file, mode='rb') as fd:
            #         crc32_str = str(crc32(fd.read()))
            #     dst_file = ''.join([
            #         os.path.join(target_dir, os.path.splitext(src_file_name)[0]),
            #         '_',
            #         crc32_str,
            #         os.path.splitext(os.path.basename(tfile))[1]
            #     ])
            # else:
            #     dst_file = os.path.join(target_dir, os.path.basename(tfile))
            dst_file = os.path.join(target_dir, os.path.basename(tfile))
            shutil.move(src_extra_file, dst_file)
            print('File "{}": Moved in "{}" directory.'.format(src_extra_file, dst_file))


def main():
    parser = argparse.ArgumentParser(description='Convert LibreOffice(OpenOffice) files into other formats.')
    parser.add_argument('--source-dir', '-s',
                        type=str, nargs='?',
                        help='source directory. Default: ".". It will ignored if --source defined',
                        default='.')
    parser.add_argument('--source-mask', '-m',
                        nargs='?',
                        type=str,
                        help='regular expression for source file mask. Default: ".+\.odt$"',
                        default=".+\.odt$"
                        )
    parser.add_argument('--source', '-f',
                        nargs='?',
                        type=str,
                        help='source file. If exists then --source-path and --source-mask will be ignore.')
    parser.add_argument('--convert-to', '-to',
                        type=str,
                        help='target format for conversion. Default: "html"',
                        default='html')
    parser.add_argument('--target-dir', '-todir',
                        type=str,
                        help='target dir',
                        required=True)
    args = parser.parse_args()

    if not os.path.exists(args.target_dir):
        raise FileNotFoundError('target directory must exists.')

    if not os.path.isdir(args.target_dir):
        raise FileNotFoundError('target directory must be directory.')

    real_target_dir = os.path.realpath(args.target_dir)

    if args.source:
        gfiles = GetFiles(args.source)
    else:
        mask = ''
        if args.source_mask:
            mask = re.compile(args.source_mask)

        def mask_filter(file):
            if os.path.isfile(file):
                if isinstance(mask, re.Pattern):
                    match = mask.match(file)
                    return True if match else False

        gfiles = GetFiles(args.source_dir)
        if args.source_mask:
            gfiles.filters_allow.insert(0, mask_filter)

        real_source_dir = os.path.realpath(args.source_dir)
        if os.path.commonpath([real_source_dir, real_target_dir]) == real_source_dir:
            raise ValueError('Logic error encountered.'
                             ' Target directory should not be inside the source directory.')

    # Choice appropriate converter
    if args.convert_to == 'html':
        converter = soffice.ConvertToHTML(None)
    elif args.convert_to == 'xhtml':
        converter = soffice.ConvertToXHTML(None)
    else:
        converter = soffice.Converter(None, convert_to=args.convert_to)

    with tempfile.TemporaryDirectory() as tmpdir:
        converter.outdir = tmpdir
        for file in gfiles:
            print('File "{}": Start.'.format(file))
            converter.file = file
            converter.process()
            print('File "{}": Stored in "{}" directory.'.format(file, tmpdir))

            # change file ext and test it existence in temporary directory
            res_file = ''.join([os.path.splitext(os.path.basename(file))[0], '.', converter.convert_to.value])
            abs_res_file = os.path.join(tmpdir, res_file)
            if not os.path.exists(abs_res_file):
                raise FileNotFoundError('Program logic error or something went wrong. After conversation file "{0}"'
                                        ' should exists.'.format(abs_res_file))

            # move to real out_dir
            rel_file_dir = os.path.relpath(
                os.path.realpath(os.path.dirname(file)),
                os.path.realpath(gfiles.root_path)
            )

            res_target_dir = os.path.join(real_target_dir, rel_file_dir)
            if not os.path.exists(res_target_dir):
                os.makedirs(res_target_dir)
            shutil.move(abs_res_file, os.path.join(res_target_dir, res_file))
            print('File "{}": Moved in "{}" directory.'.format(abs_res_file, res_target_dir))

            process_extra_files(abs_res_file, res_target_dir)


if __name__ == '__main__':
    # logging.getLogger().setLevel(logging.INFO)
    main()
