# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: file_provider.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM


import os
import collections.abc as abc


class GetFiles(abc.Iterable):
    """
        Filters facility has Deny logic if filters_allow is empty list then no one file will accepted.
        Added callback function(obj_getFiles, currentFileOrDir) you should accept or reject it,
        returning True for accept. If no one callback function does not return True this file/dir rejected.
        By default filters_allow contain one callback that accept all files and directories that
        don't start from '.' (hidden files/dirs)

        But if need more customize it then this callback can be removed by [] or changed
        objGetFiles.filters_allow = [someCallBack, someCallBack]
        for file in objGetFiles:
            print(file)

        If need to return it back
        objGetFiles.filters_allow = [objGetFiles._default_filter] # or [GetFiles._default_filter]
        for file in objGetFiles:
            print(file)

        filter callback has next signature - callable(obj_getFiles, currentFileOrDir)
        where obj_getFiles - current instance of GetFiles and currentFileOrDir - real path of current directory/file
        that will be included in final list if callback returns True.
        Note if currentFileOrDir is directory and callback not returns True this directory will be skip from traverse,
        include all files and subdirectories. That's why, sometimes useful to split logic into something like

            if os.path.isdir(file):
                if not os.path.basename(file).startswith('.'):
                    return True
            else: # file
                return True

    """
    _root_path = None
    _filters_allow = []

    def __init__(self, root_path='.', filters_allow=None) -> None:
        if filters_allow is None:
            filters_allow = [type(self)._default_filter]

        self.filters_allow = filters_allow
        self.root_path = root_path
        super().__init__()

    @property
    def root_path(self):
        return self._root_path

    @root_path.setter
    def root_path(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError('The root_path property must point to an existing directory or file.')
        self._root_path = path

    @staticmethod
    def _default_filter(file):
        # the same filters are used for both directories and files
        # if logic should be differ then just test 'file'. For example
        # if os.path.isdir(file):
        #     if not os.path.basename(os.path.realpath(file)).startswith('.'):
        #         return True
        # else: # file
        #     return True
        return not os.path.basename(os.path.realpath(file)).startswith('.')

    @property
    def filters_allow(self):
        return self._filters_allow

    @filters_allow.setter
    def filters_allow(self, filters):
        filters = list(filters)
        if len([f for f in filters if not callable(f)]) > 0:
            raise ValueError('each filter should be callable')
        self._filters_allow = filters

    def filter_file(self, file):
        """
            Makes traverse through the filters.
            If filter returns not None then traversing breaks.
            If filter returns True for a file then file will included into result.
            Otherwise will be excluded. Same for directories, but with little subtlety
            - all content of directory will excluded from traversing at all.
            But for end user this almost same.
        """
        result = False
        for f in self.filters_allow:
            result = f(file)
            if result is True or result is False:
                break
        return result

    def __filter_dirs(self, dirs, cur_path):
        """
            Removes directory from dirs if filter does not allow it
        """
        dlen = len(dirs)
        for i in range(dlen-1, -1, -1):
            fpath = os.path.join(cur_path, dirs[i])
            if not self.filter_file(fpath):
                dirs.pop(i)

    def _get_files(self):
        if os.path.isfile(self.root_path):
            yield self.root_path
        else:
            processed_real_dirs = []
            for root, dirs, files in os.walk(self.root_path, followlinks=True):
                # root is the concatenated root from previous step + each dir from dirs on next step.
                # but on the first step is the root that passed into os.walk

                root_real_path = os.path.realpath(root)
                if root_real_path in processed_real_dirs:
                    # skip walking through internal processed dirs too
                    dirs.clear()
                    continue
                # skip walking through dirs which don't allowed by filter
                self.__filter_dirs(dirs, root_real_path)
                processed_real_dirs.append(root_real_path)

                for file in files:
                    file_path = os.path.join(root, file)
                    file_real_path = os.path.realpath(file_path)

                    # check symlink that pointed inside of self.root_path to skip it
                    if os.path.islink(file_path):
                        real_root = os.path.realpath(self.root_path)
                        cmnpath = os.path.commonpath((real_root, file_real_path))
                        if cmnpath == real_root:
                            continue

                    if self.filter_file(file_real_path):
                        yield file_path

    def __iter__(self) -> abc.Iterator:
        return self._get_files()


if __name__ == '__main__':
    gf = GetFiles('../')  # '/home/ox23/PycharmProjects/py-post-parser'
    for file in gf:
        print(file)

    def odt_filter(file):
        if os.path.isfile(file):
            return os.path.basename(file).endswith('.odt')

    print('##### Second iteration should be only .odt files')
    gf.filters_allow.insert(0, odt_filter)
    for file in gf:
        print(file)

    print('##### Third iteration should be empty')
    gf.filters_allow = []
    for file in gf:
        if os.path.exists(file):
            print(file)
        else:
            print('ERROR:', file)

    print('##### Forth iteration should be only .odt files - like second')
    gf.filters_allow = [odt_filter, gf._default_filter]
    for file in gf:
        print(file)
