'''
Author       : wyx-hhhh
Date         : 2025-06-04
LastEditTime : 2025-06-09
Description  : 
'''
import sys

from ..user import User
from .parser import Parser
from .util import handle_html


class InfoParser(Parser):
    def __init__(self, cookie, user_id):
        self.cookie = cookie
        self.url = 'https://weibo.cn/%s/info' % (user_id)
        self.selector = handle_html(self.cookie, self.url)

    def extract_user_info(self):
        """提取用户信息"""
        try:
            user = User()
            nickname = self.selector.xpath('//title/text()')[0]
            nickname = nickname[:-3]
            if nickname == u'登录 - 新' or nickname == u'新浪':
                sys.exit()
            user.nickname = nickname

            basic_info = self.selector.xpath("//div[@class='c'][3]/text()")
            zh_list = [u'性别', u'地区', u'生日', u'简介', u'认证', u'达人']
            en_list = [
                'gender', 'location', 'birthday', 'description',
                'verified_reason', 'talent'
            ]
            for i in basic_info:
                if i.split(':', 1)[0] in zh_list:
                    setattr(user, en_list[zh_list.index(i.split(':', 1)[0])],
                            i.split(':', 1)[1].replace('\u3000', ''))
			
            experienced = self.selector.xpath("//div[@class='tip'][2]/text()") 
            if experienced and experienced[0] == u'学习经历':
                user.education = self.selector.xpath(
                    "//div[@class='c'][4]/text()")[0][1:].replace(
                        u'\xa0', u' ')
                if self.selector.xpath(
                        "//div[@class='tip'][3]/text()")[0] == u'工作经历':
                    user.work = self.selector.xpath(
                        "//div[@class='c'][5]/text()")[0][1:].replace(
                            u'\xa0', u' ')
            elif experienced and experienced[0] == u'工作经历':
                user.work = self.selector.xpath(
                    "//div[@class='c'][4]/text()")[0][1:].replace(
                        u'\xa0', u' ')
            return user
        except Exception as e:
            pass
