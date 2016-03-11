#!/bin/env python
# coding=utf-8
import json
import logging
import sys
import threading
import urllib
import urllib2
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from SocketServer import ThreadingMixIn

import bs4

reload(sys)
sys.setdefaultencoding('utf-8')

PAGE_NUM = 5
DOWNLOAD_PERIOD = 907


# proxy = urllib2.ProxyHandler({'http': 'web-proxy.oa.com:8080', 'https': 'web-proxy.oa.com:8080'})
# opener = urllib2.build_opener(proxy)
# urllib2.install_opener(opener)


def get_tags(ins=None, not_ins=None):
    if not ins or (len(ins) == 1 and not ins[0]):
        ins = [
            u'10号线', u'9号线',
            u'知春路', u'知春里', u'罗庄', u'巴沟', u'火器营', u'长春桥', u'车道沟',
            u'慈寿寺', u'西钓鱼台', u'公主坟', u'莲花桥', u'六里桥',
            u'白石桥南', u'国家图书馆', u'郭公庄', u'大葆台', u'六里桥东', u'七里庄'
        ]
    not_ins = [u'求租', u'已租']

    a_tags = json.load(open('./cache.json'))

    tmp_a_tags = []
    for a in a_tags:
        found = False
        for ni in not_ins:
            if ni in a[0]:
                found = True
                break
        if not found:
            tmp_a_tags.append(a)

    a_tags = tmp_a_tags
    tmp_a_tags = []
    for a in a_tags:
        found = False
        for _i in ins:
            if _i in a[0] and (a[2].startswith('2016') or ':' in a[2]):
                found = True
                break
        if found:
            tmp_a_tags.append(a)

    a_tags = tmp_a_tags
    return a_tags


class Handler(BaseHTTPRequestHandler):
    def str2dict(self, query, spliter1='&', spliter2='='):
        ret = {}
        arr1 = query.split(spliter1)
        for grp in arr1:
            arr2 = grp.split(spliter2)
            if len(arr2) > 1:
                ret[arr2[0]] = urllib.unquote(arr2[1]).decode('utf-8')
        return ret

    def parse_GET(self):
        if '?' in self.path:
            query = self.path.split('?')[1]
            self.getvar = self.str2dict(query)
        else:
            self.getvar = {}

    def parse_request(self):
        ret = BaseHTTPRequestHandler.parse_request(self)
        self.parse_GET()
        if self.command.upper() == 'POST':
            self.parse_POST()
        return ret

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        # ins = jieba.cut_for_search(self.getvar.get('ins', '').strip().replace('+',' '))
        # ins = ','.join(ins).split(',')
        ins = self.getvar.get('ins', '').strip().replace(' ', '+').split('+')
        tags = get_tags(ins=ins)
        f = open('./template.html')
        content = f.read()
        f.close()
        lis = ''
        unique = set()
        for tag in tags:
            if tag[1] not in unique:
                lis += '<li><a href="%s" target="_blank">[%s] %s</a></li>' \
                       % \
                       (tag[1], tag[2], tag[0])
            unique.add(tag[1])
        content = content.replace('{content}', lis)
        self.wfile.write(content)
        self.wfile.write('\n\n')
        return


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Handle requests in a separate thread."""


def download_and_parse():
    a_tags = []
    for i in range(PAGE_NUM):
        try:
            url = "http://www.newsmth.net/nForum/board/HouseRent?ajax&p=%d" % (i + 1)
            print url
            f = urllib2.urlopen(url, timeout=20)
            if f.getcode() != 200:
                continue
            content = f.read().decode('gbk')
            if len(content) > 4096:
                bs = bs4.BeautifulSoup(content, 'html.parser')
                tds = bs.find_all('td', 'title_9')
                tds_t = bs.find_all('td', 'title_10')
                for i in range(len(tds)):
                    a = tds[i].find('a')
                    a_tags.append(('【水木】' + a.text, 'http://www.newsmth.net' + a.attrs['href'], tds_t[i].text))
        except Exception, e:
            print e.message
    for i in range(PAGE_NUM):
        try:
            url = "https://www.douban.com/group/beijingzufang/discussion?start=%d" % (i * 25)
            print url
            f = urllib2.urlopen(url, timeout=20)
            if f.getcode() != 200:
                continue
            content = f.read().decode('utf-8')
            if len(content) > 4096:
                bs = bs4.BeautifulSoup(content, 'html.parser')
                tds = bs.find_all('td', 'title')
                tds_t = bs.find_all('td', 'time')
                for i in range(len(tds)):
                    a = tds[i].find('a')
                    a_tags.append(('【豆瓣】' + a.attrs['title'], a.attrs['href'], tds_t[i].text))
        except Exception, e:
            print e.message
        with open('cache.json', 'w') as f:
            f.write(json.dumps(a_tags))


class MyTimer(threading.Thread):
    def __init__(self, event, func, args):
        threading.Thread.__init__(self)
        self.daemon = True
        self.stopped = event
        self.func = func
        self.args = args

    def run(self):
        self.func(*self.args)
        while not self.stopped.wait(DOWNLOAD_PERIOD):
            self.func(*self.args)


if __name__ == '__main__':
    stopFlag = threading.Event()
    timer = MyTimer(stopFlag, download_and_parse, [])
    timer.start()
    server = ThreadedHTTPServer(('0.0.0.0', 8090), Handler)
    logging.info('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()
