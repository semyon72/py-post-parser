# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: soffice.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

import os
import pathlib
import subprocess as sp
import logging
from abc import abstractmethod, ABCMeta
from collections import namedtuple
from functools import wraps

SOFFICE_COMMAND_NAME = 'soffice'
SOFFICE_HEADLESS_OPTION_NAME = '--headless'


class OptionAbs(metaclass=ABCMeta):
    """
        Interface to return [...] that need as part of args in subprocess for SofficeContentComparer and ....
    """
    @abstractmethod
    def args(self):
        raise NotImplemented()


class OptionAbsBase(OptionAbs):

    """
        for example: option is '--convert-to'; value is 'html:XHTML Writer File:UTF8'
        or : option is '--convert-images-to'; value is 'jpg'
    """
    _option = ''
    _value = ''

    def __init__(self, option=None, value=None) -> None:
        self.option = option if option is not None else self._option
        self.value = value if value is not None else self._value
        super().__init__()

    def _sanitize(self, value):
        return value if (value := str(value).strip()) else ''

    @property
    def option(self):
        return self._option

    @option.setter
    def option(self, value):
        self._option = self._sanitize(value)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = self._sanitize(value)

    def args(self, allow_empty_option=False):

        if not self.option and self.value and not allow_empty_option:
            raise ValueError(
                'Semantically, option must be if value is specified. Class "{}".'.format(type(self).__name__)
            )

        if not self.value:
            if not self.option:
                return tuple()
            else:
                return self.option,
        elif not self.option:
            return self.value,

        return self.option, self.value


# 'soffice --headless'
SOFFICE_COMMON_ARGS = (
    *OptionAbsBase(SOFFICE_COMMAND_NAME).args(),
    *OptionAbsBase(SOFFICE_HEADLESS_OPTION_NAME).args()
)


class CatOption(OptionAbsBase):
    """
        '--cat /some_file_target/some.odt'
    """
    _option = '--cat'
    _value = ''

    def args(self):
        res = super().args()
        if len(res) != 2:
            raise ValueError('The "{0}" option must have "value" also.'.format(res[0]))
        else:
            rpath = os.path.realpath(res[1])
            if not os.path.exists(rpath) or not os.path.isfile(rpath):
                raise ValueError(
                    'Target file "{0} -> {1}" must exist being file.'.format(self.value, rpath))

        return res


class ConvertToOption(OptionAbsBase):
    """
        Something like
        '--convert-to', 'pdf' or '--convert-to', 'html:XHTML Writer File:UTF8'
        By default it configured to convert into pdf format.
    """
    _option = '--convert-to'
    _value = 'pdf'
    _filter = ''
    _filter_separator = ':'

    def __init__(self, option=None, value=None, filter=None) -> None:
        super().__init__(option=option, value=value)
        self._filter = filter if filter is not None else self._filter

    def _sanitize_filter(self, value):
        return self._sanitize(value)

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, value):
        self._filter = self._sanitize_filter(value)

    def args(self):
        res = [*super().args()]
        if len(res) != 2:
            raise ValueError('The "{0}" option must also have a "value", but no more.'.format(res[0]))

        filter = self.filter
        if filter:
            res[-1] += self._filter_separator + filter

        return tuple(res)


class ConvertToHTMLOption(ConvertToOption):
    """
        '--convert-to', 'html'
    """
    _value = 'html'
    _filter = ''


class ConvertToXHTMLOption(ConvertToOption):
    """
        '--convert-to', 'xhtml:XHTML Writer File:UTF8'
    """
    _value = 'xhtml'
    _filter = 'XHTML Writer File:UTF8'


class ConvertImagesToOption(OptionAbsBase):
    """
        '--convert-images-to', 'jpg'
    """
    _option = '--convert-images-to'
    _value = 'jpg'


class OutdirOption(OptionAbsBase):
    """
        '--outdir', '/some_dir_target/'
    """
    _option = '--outdir'
    _value = ''

    def args(self):
        res = super().args()
        if len(res) != 2:
            raise ValueError('Option "{0}" must have target directory as a "value".'.format(self.option))
        else:
            rpath = os.path.realpath(res[1])
            if not os.path.exists(rpath) or not os.path.isdir(rpath):
                raise ValueError('Target directory "{0} -> {1}" must exist being directory.'.format(self.value, rpath))

        return res


class FileOption(OptionAbsBase):
    """
        It supports a checking of next cases
        '/absolute_path_to_dir/lxml.odt'
        './relative_path_to_dir/lxml.odt'
        './relative_path_to_dir/*.odt'
        '*.odt'
    """
    _option = ''
    _value = ''

    def args(self):
        res = super().args(allow_empty_option=True)

        if len(res) != 1:
            raise ValueError('File should have "option" or "value" but no both. '
                             'Nothing specified or has redundant value.')
        p = pathlib.Path(res[0])
        if p.exists():
            if not p.is_file():
                raise ValueError('Path is not file "{0}"'.format(p.resolve()))
        else:
            # test to glob expression
            pgl = p.parent
            try:
                next(pgl.glob(p.name))
            except StopIteration:
                raise ValueError('Glob file pattern "{0}" has no matches in directory "{1}"'.format(p.name, pgl))
        return res


class ProcessableAbs(metaclass=ABCMeta):

    @abstractmethod
    def process(self):
        raise NotImplemented()


class logging_process:

    def __init__(self, *args, **kwargs) -> None:
        if len(args) != 1:
            raise ValueError('Decorator doesn\'t support parameters. Just use @logging_process.')
        if not callable(type(args[0])):
            raise ValueError('Attribute of class that decorated should be function.')
        self.__func = args[0]
        super().__init__()

    def __get__(self, instance, owner):
        if instance is None:
            if not issubclass(owner, ProcessBase):
                raise ValueError('Decorator supports only classes that implement the ProcessBase interface.')
            return self
        else:
            @wraps(self.__func)
            def wrapper(args):
                fname = args[-1:]
                logging.info('Attempt to get content "{0}".'.format(*fname))
                finfo = self.__func(instance, args)
                if len(finfo.err) > 0:
                    logging.error('File "{0}" processed with error:'.format(*fname))
                    logging.error(finfo.err.decode())
                if finfo.timeout_expired:
                    logging.error('Process finished by time out {0}sec. '
                                  'Probably, need to grow {1}._process_time_out '
                                  'value or set to None.'.format(self._process_time_out, self.__class__.__name__)
                                  )
                if finfo.return_code != 0:
                    logging.info('Process finished with error code {0}.'.format(finfo.return_code))
                if not finfo.has_error:
                    logging.info('Content is gotten.')
                return finfo
            return wrapper


class ProcessBase(ProcessableAbs):
    """
        Method process() returns ProcessResult tuple that contains the resulting information.
    """

    _process_time_out = None
    """ 
    None - will wait the end of execution, the positive value is a maximum time for execution.
    If execution time more than value then process will stopped but not killed right after N seconds.
    Popen.kill() should be invoked or use the Popen as context manager
    """

    __ProcessResult = namedtuple('ProcessResult', ['out', 'err', 'return_code', 'timeout_expired', 'has_error'])

    @logging_process
    def _get_subprocess_result(self, args):
        toexp = False
        proc = sp.Popen(args, stdout=sp.PIPE, stderr=sp.PIPE)
        try:
            result = proc.communicate(timeout=self._process_time_out)
        except sp.TimeoutExpired as err:
            toexp = True
            # before the next step we need to kill or terminate the process
            proc.kill()  # has -9 returncode
            # fetch data that have been processed so far
            result = proc.communicate()

        return self.__ProcessResult(
            timeout_expired=toexp, out=result[0], err=result[1], return_code=proc.returncode,
            has_error=len(result[1]) > 0 or toexp or proc.returncode != 0
        )

    def process(self):
        try:
            args = getattr(self, 'args')
        except AttributeError:
            raise NotImplemented()
        else:
            return self._get_subprocess_result(args)


class CatContent(ProcessBase):
    """
        IT USES LIBREOFFICE OR OPENOFFICE INSTALLATION IN SYSTEM.

        Main command is 'soffice --headless --cat /path_to_file/filename'

        Method process() returns ProcessResult tuple that contains resulting information.
    """

    _cat_args = None

    def __init__(self, file) -> None:
        self.file = file
        super().__init__()

    @property
    def file(self):
        return self._cat_args[1]

    @file.setter
    def file(self, file):
        self._cat_args = CatOption(value=file).args()

    @property
    def args(self):
        return tuple(filter(None, (*SOFFICE_COMMON_ARGS, *self._cat_args)))

    def process(self):
        """
            'soffice --headless --cat /path_to_file/filename'
        """
        return super().process()


class CatContentComparer(ProcessableAbs):
    """
        IT USES LIBREOFFICE OR OPENOFFICE INSTALLATION IN SYSTEM.
        It makes a comparison between two files, probably different formats, by content.

        Main command is 'soffice --headless --cat /path_to_file/filename'

        Unlike general behaviour of process() method the xxxxComparer classes return the Boolean
        value as result success processing of two contents and comparison.

        Internal, it will invoke 'soffice --headless --cat /path_to_file/filename' twice.
        If no errors happened then will return boolean result of comparison
        but otherwise it returns tuple that contains process information data that finished with error.
    """

    _file1 = None
    _file2 = None

    def __init__(self, file1, file2) -> None:
        self.file1 = file1
        self.file2 = file2
        super().__init__()

    @property
    def file1(self):
        return self._file1

    @file1.setter
    def file1(self, file):
        self._file1 = CatContent(file)

    @property
    def file2(self):
        return self._file2

    @file2.setter
    def file2(self, file):
        self._file2 = CatContent(file)

    def compare(self, content1, content2):
        """
            Just compare for equals of contents.
            If need differ logic then redefine it.
        """
        return content1 == content2

    def process(self):
        """
            It will invoke 'soffice --headless --cat /path_to_file/filename' twice.
            If no errors happened then will return boolean result of comparison
            but otherwise it returns tuple that contains process information data.
        """
        logging.info('Comparison started.')

        finfo1 = self.file1.process()
        if finfo1.has_error:
            return finfo1

        finfo2 = self.file2.process()
        if finfo2.has_error:
            return finfo2

        result = self.compare(finfo1.out, finfo2.out)
        logging.info('Result of comparison is: {0}.'.format(result))
        return result


class CatContentNoSpacesComparer(CatContentComparer):
    """
        IT USES LIBREOFFICE OR OPENOFFICE INSTALLATION IN SYSTEM.
        It makes a comparison between two files, probably different formats, by content.
        But before comparison content will be decoded into string where will be removed all spaces.
        Resulted strings will be compared by == operator (__eq__).

        Main command is 'soffice --headless --cat /path_to_file/filename'
    """

    _encoding = 'utf8'

    def compare(self, content1, content2):
        content1 = str(content1, encoding=self._encoding)
        content2 = str(content2, encoding=self._encoding)
        return content1.split() == content2.split()


class Converter(ProcessBase):
    """
        Method process() returns Boolean value.
        True if processed without errors.
    """

    _outdir = None
    _convert_to = None
    _file = None
    _convert_images_to = None

    def __init__(self, file, outdir=None, convert_to=None, convert_images_to=None) -> None:
        self.file = file
        self.outdir = outdir
        self.convert_to = convert_to
        self.convert_images_to = convert_images_to
        super().__init__()

    @property
    def file(self):
        return self._file

    def __setter(self, attr, _class, value):
        """
            If value is instance of _class then it will assigned as is
            otherwise setattr(self, attr, _class(value=value))
        """
        if not isinstance(value, _class):
            value = _class(value=value)

        setattr(self, attr, value)

    @file.setter
    def file(self, file):
        """
            If value is instance of FileOption then it will assigned as is
        """
        self.__setter('_file', FileOption, file)

    @property
    def outdir(self):
        return self._outdir

    @outdir.setter
    def outdir(self, value):
        """
            If value is instance of OutdirOption then it will assigned as is
        """
        self.__setter('_outdir', OutdirOption, value)

    @property
    def convert_to(self):
        return self._convert_to

    @convert_to.setter
    def convert_to(self, value):
        """
            If value is instance of ConvertToOption then it will assigned as is
        """
        self.__setter('_convert_to', ConvertToOption, value)

    @property
    def convert_images_to(self):
        return self._convert_images_to

    @convert_images_to.setter
    def convert_images_to(self, value):
        """
            If value is instance of ConvertImagesToOption then it will assigned as is
        """
        self.__setter('_convert_images_to', ConvertImagesToOption, value)

    @property
    def args(self):
        return (*SOFFICE_COMMON_ARGS, *self.convert_to.args(),
                *self.outdir.args(), *self.convert_images_to.args(),
                *self.file.args())

    def process(self):
        """
            If your target format need filter then assign desired
            value to self.convert_to.filter for example:
            self.convert_to.filter = 'some_filter_value'

            Filter is string defined in LibreOffice - something like 'XHTML Writer File'
            for example: soffice --headless  --convert-to 'html:XHTML Writer File:UTF8'
        """

        logging.info('Conversion started.')
        result = super().process()
        if result.has_error:
            logging.info('Process information: {0}'.format(result.out.decode()))
        logging.info('Conversion finished.')
        return not result.has_error


class ConvertToHTML(Converter):
    """
        This is not like ConverterToXHTML due to we use just 'html' as value for --convert-to
        By default, In this way the LibreOffice (OpenOffice) using filter : HTML (StarWriter) which
        ignore --convert-images-to argument.
    """

    def __init__(self, file, outdir=None) -> None:
        super().__init__(file, outdir, ConvertToHTMLOption())


class ConvertToXHTML(Converter):

    def __init__(self, file, outdir=None) -> None:
        super().__init__(file, outdir, ConvertToXHTMLOption(), ConvertImagesToOption())


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    result_dir = '../work.tmp/'

    file_1 = '../work/Docs/Apache and mod_ssl.odt'
    file_2 = '../work/Docs/CertBot & Apache.odt'
    file_3 = '../work/Docs/CertBot & Apache.html'
    file_4 = '../work/Docs/CertBot & Apache.xml'
    file_5 = '../work/Docs/GNU make.pdf'
    file_6 = '../work/OpenSSL/OpenSSL certificate relations.odt'

    # oconverter = Converter(file_6, result_dir, 'xml', 'jpg')
    # oconverter.process()
    #
    # oconverter = Converter(file_6, result_dir, 'html', 'jpg')
    # oconverter.process()
    #
    oconverter = ConvertToHTML(file_2, result_dir)
    oconverter.process()
    oconverter.file = file_6
    oconverter.process()

    oconverter = ConvertToXHTML(file_6, result_dir)
    res = oconverter.process()

    occ = CatContentComparer(file_2, file_3)
    res = occ.process()

    ocnsc = CatContentNoSpacesComparer(file_2, file_3)
    res = ocnsc.process()

    ocnsc.file1 = file_4
    ocnsc.file2 = file_2
    res = ocnsc.process()

    print(CatContent('../work/Docs/CertBot & Apache.xml').process().out.decode())
