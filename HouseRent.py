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

PAGE_NUM = 10
DOUBAN_PAGE_NUM = 20
DOWNLOAD_PERIOD = 907

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s\t%(filename)s:%(lineno)d\t%(funcName)s\t%(levelname)s\t%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')


# proxy = urllib2.ProxyHandler({'http': 'web-proxy.oa.com:8080', 'https': 'web-proxy.oa.com:8080'})
# opener = urllib2.build_opener(proxy)
# urllib2.install_opener(opener)


def get_tags(ins=None, not_ins=None):
    if not ins or (len(ins) == 1 and not ins[0]):
        ins = [u'六号线',u'6号线',u'呼家楼',u'金台路',u'十里堡',u'青年路',u'褡裢坡',u'黄渠',u'朝阳门',u'两居']
        
    not_ins = [u'公告',u'限女',u'合租',u'三居',u'北三环',u'中介',u'天通苑',u'清华',u'海淀',u'上地',u'清河',u'望京',u'来广营',u'一居',u'一室一厅',u'求租']

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
            logging.info(url)
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
            logging.error(e.message)
    for i in range(DOUBAN_PAGE_NUM):
        try:
            url = "https://www.douban.com/group/beijingzufang/discussion?start=%d" % (i * 25)
            logging.info(url)
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
            logging.error(e.message)
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
