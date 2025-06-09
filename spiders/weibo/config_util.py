import codecs
import os
import sys
import browser_cookie3
from datetime import datetime
import json


def _is_date(date_str):
    """判断日期格式是否正确"""
    try:
        if ':' in date_str:
            datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        else:
            datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_config(config):
    """验证配置是否正确"""

    # 验证filter、pic_download、video_download
    argument_list = ['filter', 'pic_download', 'video_download']
    for argument in argument_list:
        if config[argument] != 0 and config[argument] != 1:
            print(u'%s值应为0或1,请重新输入' % config[argument])
            sys.exit()

    # 验证since_date
    since_date = config['since_date']
    if (not _is_date(str(since_date))) and (not isinstance(since_date, int)):
        sys.exit()

    # 验证end_date
    end_date = str(config['end_date'])
    if (not _is_date(end_date)) and (end_date != 'now'):
        print(u'end_date值应为yyyy-mm-dd形式或"now",请重新输入')
        sys.exit()

    # 验证random_wait_pages
    random_wait_pages = config['random_wait_pages']
    if not isinstance(random_wait_pages, list):
        print(u'random_wait_pages参数值应为list类型,请重新输入')
        sys.exit()
    if (not isinstance(min(random_wait_pages), int)) or (not isinstance(
            max(random_wait_pages), int)):
        print(u'random_wait_pages列表中的值应为整数类型,请重新输入')
        sys.exit()
    if min(random_wait_pages) < 1:
        print(u'random_wait_pages列表中的值应大于0,请重新输入')
        sys.exit()

    # 验证random_wait_seconds
    random_wait_seconds = config['random_wait_seconds']
    if not isinstance(random_wait_seconds, list):
        print(u'random_wait_seconds参数值应为list类型,请重新输入')
        sys.exit()
    if (not isinstance(min(random_wait_seconds), int)) or (not isinstance(
            max(random_wait_seconds), int)):
        print(u'random_wait_seconds列表中的值应为整数类型,请重新输入')
        sys.exit()
    if min(random_wait_seconds) < 1:
        print(u'random_wait_seconds列表中的值应大于0,请重新输入')
        sys.exit()

    # 验证global_wait
    global_wait = config['global_wait']
    if not isinstance(global_wait, list):
        print(u'global_wait参数值应为list类型,请重新输入')
        sys.exit()
    for g in global_wait:
        if not isinstance(g, list):
            print(u'global_wait参数内的值应为长度为2的list类型,请重新输入')
            sys.exit()
        if len(g) != 2:
            print(u'global_wait参数内的list长度应为2,请重新输入')
            sys.exit()
        for i in g:
            if (not isinstance(i, int)) or i < 1:
                print(u'global_wait列表中的值应为大于0的整数,请重新输入')
                sys.exit()

    # 验证write_mode
    write_mode = ['txt', 'csv', 'json', 'mongo', 'mysql', 'sqlite', 'kafka','post']
    if not isinstance(config['write_mode'], list):
        print(u'write_mode值应为list类型')
        sys.exit()
    for mode in config['write_mode']:
        if mode not in write_mode:
            print(
                u'%s为无效模式，请从txt、csv、json、post、mongo、sqlite, kafka和mysql中挑选一个或多个作为write_mode' %
                mode)
            sys.exit()

    # 验证user_id_list
    user_id_list = config['user_id_list']
    if (not isinstance(user_id_list,
                       list)) and (not user_id_list.endswith('.txt')):
        print(u'user_id_list值应为list类型或txt文件路径')
        sys.exit()
    if not isinstance(user_id_list, list):
        if not os.path.isabs(user_id_list):
            user_id_list = os.getcwd() + os.sep + user_id_list
        if not os.path.isfile(user_id_list):
            print(u'不存在%s文件' % user_id_list)
            sys.exit()


def get_user_config_list(file_name, default_since_date):
    """获取文件中的微博id信息"""
    with open(file_name, 'rb') as f:
        try:
            lines = f.read().splitlines()
            lines = [line.decode('utf-8-sig') for line in lines]
        except UnicodeDecodeError:
            print(u'%s文件应为utf-8编码，请先将文件编码转为utf-8再运行程序' % file_name)
            sys.exit()
        user_config_list = []
        for line in lines:
            info = line.split(' ')
            if len(info) > 0 and info[0].isdigit():
                user_config = {}
                user_config['user_uri'] = info[0]
                if len(info) > 2 and _is_date(info[2]):
                    if len(info) > 3 and _is_date(info[2] + ' ' + info[3]):
                        user_config['since_date'] = info[2] + ' ' + info[3]
                    else:
                        user_config['since_date'] = info[2]
                else:
                    user_config['since_date'] = default_since_date
                if user_config not in user_config_list:
                    user_config_list.append(user_config)
    return user_config_list


def update_user_config_file(user_config_file_path, user_uri, nickname,
                            start_time):
    """更新用户配置文件"""
    if not user_config_file_path:
        user_config_file_path = os.getcwd() + os.sep + 'user_id_list.txt'
    with open(user_config_file_path, 'rb') as f:
        lines = f.read().splitlines()
        lines = [line.decode('utf-8-sig') for line in lines]
        for i, line in enumerate(lines):
            info = line.split(' ')
            if len(info) > 0:
                if user_uri == info[0]:
                    if len(info) == 1:
                        info.append(nickname)
                        info.append(start_time)
                    if len(info) == 2:
                        info.append(start_time)
                    if len(info) > 3 and _is_date(info[2] + ' ' + info[3]):
                        del info[3]
                    if len(info) > 2:
                        info[2] = start_time
                    lines[i] = ' '.join(info)
                    break
    with codecs.open(user_config_file_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def add_user_uri_list(user_config_file_path, user_uri_list):
    """向user_id_list.txt文件添加若干user_uri"""
    if not user_config_file_path:
        user_config_file_path = os.getcwd() + os.sep + 'user_id_list.txt'
    if os.path.isfile(user_config_file_path):
        user_uri_list[0] = '\n' + user_uri_list[0]
    with codecs.open(user_config_file_path, 'a', encoding='utf-8') as f:
        f.write('\n'.join(user_uri_list))
      
def get_cookie():
    """Get weibo.cn cookie from Chrome browser"""
    try:
        chrome_cookies = browser_cookie3.chrome(domain_name='weibo.cn')
        cookies_dict = {cookie.name: cookie.value for cookie in chrome_cookies}
        return cookies_dict
    except Exception as e:
        print(u'Failed to obtain weibo.cn cookie from Chrome browser: %s' % str(e))
        raise 
    
def update_cookie_config(cookie, user_config_file_path):
    """Update cookie in config.json"""
    if not user_config_file_path:
        user_config_file_path = os.getcwd() + os.sep + 'config.json' 
    try:
        with codecs.open(user_config_file_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        cookie_string = '; '.join(f'{name}={value}' for name, value in cookie.items())
        
        if config['cookie'] != cookie_string:
            config['cookie'] = cookie_string
            with codecs.open(user_config_file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(u'Failed to update cookie in config file: %s' % str(e))
        raise 
    
def check_cookie(user_config_file_path): 
    """Checks if user is logged in"""
    try:
        cookie = get_cookie()
        if cookie.get("MLOGIN", '0') == '0':
            print("使用 Chrome 在此登录 %s" % "https://passport.weibo.com/sso/signin?entry=wapsso&source=wapssowb&url=https://m.weibo.cn/")
            sys.exit()
        else:
            update_cookie_config(cookie, user_config_file_path)
    except Exception as e:
        print(u'Check for cookie failed: %s' % str(e))
        raise 
