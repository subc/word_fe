# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from collections import defaultdict
from werkzeug.utils import cached_property
from janome.tokenizer import Tokenizer
import re
from bs4 import BeautifulSoup


# DATA_PATH = '../dat/ffbe.dat'
DATA_PATH = '../dat/punk.dat'


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
    # 読み込み
    r = {}
    for posted in dat_reader(DATA_PATH):
        r[posted.num] = posted

    # 読み込み後のパース
    for key in r:
        r[key].check(r)

    # 評価高い投稿を出力
    for key in r:
        if r[key].priority > 200:
            print "++++++++++++++++++++"
            print r[key].priority
            print "++++++++++++++++++++"

            r[key].printer(r=r)

    raise

    # キーワード解析
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
            yield Posted(i + 1, line)


class Posted(object):
    def __init__(self, num, line):
        self.num = num
        self.line = line
        self.priority = 0
        self.child = []

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

    @cached_property
    def parse_bs4(self):
        """
        行毎のBeautifulSoupの解析結果
        :rtype : list of BeautifulSoup
        """
        return [BeautifulSoup(m, "lxml") for m in self.parse_post_message]

    @cached_property
    def post_message_for_output(self):
        """
        ポストメッセージからAタグ除外
        """
        r = []
        for soup in self.parse_bs4:
            s = soup.text
            if soup.a:
                for _a in soup.a:
                    s = s.replace(str(_a), "")
            r.append(s)
        return r

    @property
    def count_link(self):
        return sum([len(soup.a) for soup in self.parse_bs4 if soup.a])

    @cached_property
    def res(self):
        """
        >> 1 なら [1]
        >> 234, 561なら [234, 561]
        """
        r = []
        for t in [soup.a.text for soup in self.parse_bs4 if soup.a]:
            res_base = t.replace(">>", "")
            try:
                res = int(res_base)
                if 10 < res < 1000:
                    r.append(res)
            except:
                pass
        return r

    def set_cheap(self):
        """
        品質が悪い投稿
        """
        self.priority = -10000

    def printer(self, depth=0, r=None):
        prefix = "".join(['--' for x in range(depth)])
        print "{}◆◆ {}".format(prefix, str(self.num))
        for x in self.post_message_for_output:
            if len(x) > 1:
                print prefix, x

        # 子レスをprint
        if r:
            [r[child_res].printer(depth=depth + 1, r=r) for child_res in self.child if r[child_res].priority >= 0]

    def res_from(self, child_res):
        """
        特定投稿からのres
        """
        # 自己評価を上げる
        self.priority += 100

        # 子レスを記録
        self.set_child(child_res)

    def set_child(self, child_res):
        if self.num == child_res:
            return
        self.child.append(child_res)

    def check(self, r):
        """
        自己診断する
        """
        # NGワード
        # レス数の検知
        if self.count_link > 1:
            self.set_cheap()
            return

        # 未来に向けたレス
        for res_num in self.res:
            if self.num <= res_num:
                self.set_cheap()
            else:
                # レスによる重み付け
                if res_num in r:
                    parent = r[res_num]
                    parent.res_from(self.num)
                else:
                    print "NOT FOUND ERROR:{}".format(res_num)

        # 画像かURL入っていたら除外
        for x in self.post_message_for_output:
            if '://' in x:
                self.set_cheap()

t = Tokenizer()
main()
