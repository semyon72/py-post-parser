# IDE: PyCharm
# Project: py-post-parser
# Path: lib
# File: next_page_recognizer.py
# Contact: Semyon Mamonov <semyon.mamonov@gmail.com>
# Created by ox23 at 2022-01-29 (y-m-d) 10:40 PM

from abc import ABCMeta, abstractmethod
from functools import reduce

from lib.urldif import UrlDiff, PLUS, MINUS, NOTEQUAL


ROUND_PRECISION = 3


class NextPageRecognizerAbs(metaclass=ABCMeta):

    @abstractmethod
    def recognize(self):
        raise NotImplementedError()


class NextPageAutoRecognizer(NextPageRecognizerAbs):

    def __init__(self, url1, url2, *args) -> None:
        self._urls = [url1, url2, *args]
        super().__init__()

    def _calc_differences(self, diff: UrlDiff):
        differences = diff.get_differences()
        dif_keys = set(differences)

        if len(dif_keys - set((PLUS, MINUS, NOTEQUAL))) > 0:
            raise ValueError(
                'Something went wrong. Result of UrlDiff.get_differences() can contain only "+", "-", "!" keys.'
            )

        def weight_of_list(values):
            gcnt, bcnt, res = (0, 0, [])
            for v in values:
                try:
                    v = int(v)
                except ValueError:
                    bcnt += 1
                else:
                    gcnt += 1
                    res.append(v)
            return round(gcnt / (gcnt + bcnt), ROUND_PRECISION), res

        def weight_of_item(item):
            ki = []
            sum_w = 0
            il = len(item)
            for k, v in item.items():
                if isinstance(k, int):
                    v = (v, )
                w, vr = weight_of_list(v)
                sum_w += round(1/il * w, ROUND_PRECISION)
                if w > 0:
                    ki.append((w, k, vr))

            if sum_w == 0:
                return 0, ki

            return round(sum_w / il, ROUND_PRECISION), ki

        positive_cnt, res = (0, [])
        for diff_key in (PLUS, MINUS, NOTEQUAL):
            w = weight_of_item(differences.get(diff_key, {}))
            if w[0] > 0:
                positive_cnt += 1
                res.append(w)

        sum_w = 0
        for w in res:
            sum_w += round(w[0] / positive_cnt, ROUND_PRECISION)

        if positive_cnt > 0:
            return round(sum_w / positive_cnt, ROUND_PRECISION), res
        else:
            return 0, res

    def recognize(self):
        """
            Returns 3-tuple
            0 - name or index that probably identify a page in url
            1 - values - which were set in the url for this name or index, generally a list of one element
                These values, also in general, do not matter.
            2 - UrlDiff object
            Or will raise an exception if has not recognize 'page' with 100% probability.
        """

        diffs = []
        pos_w_cnt = 0

        def reduce_func(cur_url, next_url):
            nonlocal pos_w_cnt
            diff = UrlDiff(cur_url, next_url)
            w, res = self._calc_differences(diff)
            if w == 1:
                diffs.append((w, res, diff))
                pos_w_cnt += 1
            return next_url

        result = {}
        reduce(reduce_func, self._urls)
        for total_prob, prob_info, diff in sorted(diffs, key=lambda item: item[0], reverse=True):
            # next line just for testing purposes. For more wide information
            # an expression "if w == 1:" in "reduce_func" can be changed into "if w > 0:"
            # print(w, wi, diff)
            if len(prob_info) != 1:
                raise ValueError('If total probability is 1.0 then prob_info should have only one item'
                                 ' that probably define a page.'
                                 ' Partially this limited by "if w == 1:" expression in "reduce_func" ')
            partial_prob, field_info = prob_info[0]
            if len(field_info) != 1:
                raise ValueError('If total probability is 1.0 then field_info should have only one field'
                                 ' that probably to define a page.'
                                 ' Partially this limited by "if w > 0:" expression in "weight_of_item" ')
            field_prob, field_name_index, field_values = field_info[0]
            result.setdefault(
                field_name_index, [0, field_values, diff]
            )[0] += round(field_prob / pos_w_cnt, ROUND_PRECISION)

        if len(result) != 1:
            raise ValueError("Result of recognition has no exact one answer.\n RESULT:\n{}".format(result))
        field_index, filed_info = next(iter(result.items()))
        return field_index, filed_info[1], filed_info[2]


if __name__ == '__main__':
    urls = (
        # 'https://test.blog.lan/some/0/',
        # 'https://test.blog.lan/some/1/',
        # 'https://test.blog.lan/some/2?',
        # 'https://test.blog.lan/some/2/',
        # 'https://test.blog.lan/some/4',
        # 'https://test.blog.lan/some/5/',
        #
        'https://test.blog.lan/some/url',
        'https://test.blog.lan/some/url/?page=2',
        # 'https://test.blog.lan/some/url?page=3',
        # 'https://test.blog.lan/some/url/?page=4',
        # 'https://test.blog.lan/some/url?page=5',
        # 'https://test.blog.lan/some/6?page=4',
        # 'https://test.blog.lan/some/2/path/?page=2',
        # 'https://test.blog.lan/some/5/path/with/extra/?page=2',
        # 'https://test.blog.lan/some/url/path/?page=3',
        # 'https://test.blog.lan/some/url/path_changed/with/extra/?page=2',
        # 'https://test.blog.lan/some/url/path/with/extra/?page=2',
        # 'https://test.blog.lan/some/url/path?page=2&with=&extra=extraval',
        # 'https://test.blog.lan/some/url/path?page=2&with=&extra=extraval&some=1',
        # 'https://test.blog.lan/some/url/path/?page=2&some=1',
        # 'https://test.blog.lan/some/url/path/?page=1&next_val=nextval&dbl_val=one&dbl_val=two',
        # 'https://test.blog.lan/some/url/path?dbl_val=one&dbl_val=two&page=2&with=&next_val=nextval_dif_val'
     )

    recognizer = NextPageAutoRecognizer(*urls)
    page_field, values, diff = recognizer.recognize()
    cur_val = diff[0]
    print(diff.unparse({page_field: 5}))
