# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from collections import defaultdict
from werkzeug.utils import cached_property
from janome.tokenizer import Tokenizer
import re
from bs4 import BeautifulSoup


DATA_PATH = '../dat/ffbe.dat'
# DATA_PATH = '../dat/punk.dat'


def token_is_sub(token):
    """
    名詞、形容詞以外ならTrue
    """
    if "動詞" in token.part_of_speech:
        return True

    if "助" in token.part_of_speech:
        return True

    if "記号" in token.part_of_speech:
        return True

    if "数" in token.part_of_speech:
        return True

    if "サ変接続" in token.part_of_speech:
        return True

    if re.match(r'[a-zA-Z0-9]', token.surface):
        return True
    return False


def final_filter(prev_token, token):
    """
    最終的に登録するかを判定
    """
    if not prev_token:
        return False

    s = prev_token.surface + token.surface
    if len(s) <= 2:
        return False

    if "スレ" in s:
        return False

    if re.match(r'[ぁ-ん]', s):
        return False

    if re.match(r'[0-9]', token.surface):
        return False

    if len(token.surface) == 1 and re.match(r'[ぁ-ん]', token.surface):
        return False

    return True


def main():
    print "start"
    r = {}
    for posted in dat_reader(DATA_PATH):
        r[posted.num] = posted

    tfidf1 = defaultdict(int)
    tfidf2 = defaultdict(int)
    tfidf2_post = defaultdict(list)

    for key in r:
        p = r[key]
        for message in p.parse_post_message:
            # Aタグ排除
            soup = BeautifulSoup(message, "lxml")

            # janome
            _prev_token = None
            try:
                for token in t.tokenize(soup.text):
                    tfidf1[token.surface] += 1

                    # tokenが助詞なら相手しない
                    if final_filter(_prev_token, token):
                        tfidf2[_prev_token.surface + token.surface] += 1
                        if p not in tfidf2_post[_prev_token.surface + token.surface]:
                            tfidf2_post[_prev_token.surface + token.surface] += [p]

                    _prev_token = token

                    # tokenが助詞ならtfidf2の先頭文字から除外
                    if token_is_sub(token):
                        _prev_token = None
            except:
                pass

    print "+++++++++++++++++++++++"
    print "tfidf1"
    print "+++++++++++++++++++++++"
    for key in tfidf1:
        if tfidf1[key] > 10:
            print "{}:{}".format(key, tfidf1[key])

    print "+++++++++++++++++++++++"
    print "tfidf2-post"
    print "+++++++++++++++++++++++"
    for key in tfidf2_post:
        if tfidf2[key] > 5:
            print "+++++++{}+++++++".format(key)
            for posted in tfidf2_post[key]:
                posted.printer()
            # print "".join([x.post_message for x in tfidf2_post[key]])

    print "+++++++++++++++++++++++"
    print "tfidf2"
    print "+++++++++++++++++++++++"
    for key in tfidf2:
        if tfidf2[key] > 5:
            print "{}:{}".format(key, tfidf2[key])

    print "finish"


def dat_reader(path):
    # File Read
    f = open(path, 'r')
    for i, line in enumerate(f):
        if 20 < i < 1000:
            yield Posted(i, line)


class Posted(object):
    def __init__(self, num, line):
        self.num = num
        self.line = line

    def __repr__(self):
        return self.parse_post_message[0]

    @cached_property
    def splited(self):
        return self.line.split('<>')

    @property
    def post_message(self):
        return self.splited[3]

    @cached_property
    def parse_post_message(self):
        return self.post_message.split('<br>')

    def printer(self):
        print "--- {}".format(str(self.num))
        for x in self.parse_post_message:
            print x

t = Tokenizer()
main()
