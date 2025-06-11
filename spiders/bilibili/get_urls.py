import asyncio
import sys
from playwright.async_api import async_playwright
import re


class BilibiliUrlCollector:
    def __init__(self, use_existing_browser=True, debug_port=9222):
        """
        初始化B站URL收集器

        参数：
            use_existing_browser: 是否连接到现有浏览器实例
            debug_port: 调试端口号
        """
        self.browser = None
        self.page = None
        self.playwright = None
        self.use_existing_browser = use_existing_browser
        self.debug_port = debug_port

    async def setup_browser(self):
        """设置浏览器连接"""
        if self.playwright is None:
            self.playwright = await async_playwright().start()
        
        if self.use_existing_browser:
            # 连接到现有浏览器实例
            print(f"🔗 尝试连接到现有浏览器 (端口: {self.debug_port})")
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{self.debug_port}")
                
                # 获取现有页面或创建新页面
                contexts = self.browser.contexts
                if contexts:
                    pages = contexts[0].pages
                    if pages:
                        # 使用现有的第一个页面
                        self.page = pages[0]
                        print("✅ 使用现有浏览器页面")
                    else:
                        # 在现有上下文中创建新页面
                        self.page = await contexts[0].new_page()
                        print("✅ 在现有浏览器中创建新页面")
                else:
                    # 创建新上下文和页面
                    context = await self.browser.new_context()
                    self.page = await context.new_page()
                    print("✅ 在现有浏览器中创建新上下文和页面")
                    
                print("🎉 成功连接到现有浏览器！")
                
            except Exception as e:
                print(f"⚠️ 无法连接到现有浏览器: {e}")
                print("💡 请先启动Chrome浏览器并开启调试模式：")
                print(f"   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port={self.debug_port} --user-data-dir=/tmp/chrome-debug")
                raise Exception("无法连接到现有浏览器，请先按照上述说明启动Chrome")
        else:
            # 启动新的浏览器实例
            print("🚀 启动新的浏览器实例...")
            self.browser = await self.playwright.chromium.launch(headless=False)
            context = await self.browser.new_context()
            self.page = await context.new_page()

    async def navigate_to_page(self, base_url, page_number):
        """
        通过浏览器操作跳转到指定页码（纯操作式，不修改URL）
        
        参数：
            base_url: 基础URL
            page_number: 页码
        返回：
            是否跳转成功
        """
        print(f"🔄 通过输入框跳转到第 {page_number} 页")
        
        try:
            # 如果是第一页，直接访问基础URL
            if page_number == 1:
                await self.page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(3000)
                print(f"✅ 成功访问第 1 页")
                return True
            
            # 确保我们在正确的页面上
            current_url = self.page.url
            base_domain = base_url.split('?')[0]
            if not current_url.startswith(base_domain):
                print(f"📱 首先访问基础页面：{base_url}")
                await self.page.goto(base_url, wait_until="domcontentloaded", timeout=30000)
                await self.page.wait_for_timeout(3000)
            
            # 查找页码输入框
            input_xpath = '//*[@id="app"]/main/div[1]/div[2]/div/div[3]/div/div[2]/div/div/input'
            
            print(f"🔍 查找页码输入框...")
            
            # 等待输入框出现
            try:
                await self.page.wait_for_selector(f"xpath={input_xpath}", timeout=10000)
                print(f"✅ 找到页码输入框")
                
                # 获取输入框元素
                input_element = await self.page.query_selector(f"xpath={input_xpath}")
                
                if input_element:
                    # 检查输入框是否可见和可操作
                    is_visible = await input_element.is_visible()
                    is_enabled = await input_element.is_enabled()
                    
                    print(f"📋 输入框状态 - 可见: {is_visible}, 可用: {is_enabled}")
                    
                    if not is_visible or not is_enabled:
                        print(f"⚠️ 输入框不可操作，尝试滚动到可见区域")
                        await input_element.scroll_into_view_if_needed()
                        await self.page.wait_for_timeout(1000)
                    
                    # 点击输入框以获得焦点
                    print(f"👆 点击输入框")
                    await input_element.click()
                    await self.page.wait_for_timeout(500)
                    
                    # 全选并清空输入框内容
                    print(f"🗑️ 清空输入框内容")
                    await input_element.select_text()
                    await self.page.wait_for_timeout(200)
                    
                    # 输入目标页码
                    print(f"⌨️ 输入页码: {page_number}")
                    await input_element.type(str(page_number), delay=100)
                    await self.page.wait_for_timeout(500)
                    
                    # 验证输入是否正确
                    input_value = await input_element.input_value()
                    print(f"📝 输入框当前值: '{input_value}'")
                    
                    if str(page_number) not in input_value:
                        print(f"⚠️ 输入值不正确，重试...")
                        await input_element.fill(str(page_number))
                        await self.page.wait_for_timeout(500)
                    
                    # 按回车键确认跳转
                    print(f"⏎ 按下回车键")
                    await input_element.press("Enter")
                    
                    # 等待页面跳转
                    print(f"⏳ 等待页面跳转...")
                    await self.page.wait_for_timeout(4000)
                    
                    # 验证页面是否成功跳转
                    success = await self.verify_page_navigation(page_number)
                    if success:
                        print(f"✅ 成功跳转到第 {page_number} 页")
                        return True
                    else:
                        print(f"❌ 跳转到第 {page_number} 页失败")
                        return False
                        
                else:
                    print(f"❌ 无法获取输入框元素")
                    return False
                    
            except Exception as e:
                print(f"❌ 操作页码输入框时出错：{e}")
                # 尝试其他可能的输入框选择器
                return await self.try_alternative_input_methods(page_number)
            
        except Exception as e:
            print(f"❌ 跳转到第 {page_number} 页时出错：{e}")
            return False

    async def try_alternative_input_methods(self, page_number):
        """
        尝试其他可能的输入框定位方法
        """
        print(f"🔄 尝试其他输入框定位方法...")
        
        alternative_selectors = [
            'input[type="text"][placeholder*="页"]',
            'input[type="number"]',
            '.be-pager input',
            '.bili-pagination input',
            'input.page-input',
            '.pagination input'
        ]
        
        for selector in alternative_selectors:
            try:
                print(f"🔍 尝试选择器: {selector}")
                element = await self.page.query_selector(selector)
                if element:
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"✅ 找到可用的输入框: {selector}")
                        
                        # 执行输入操作
                        await element.click()
                        await self.page.wait_for_timeout(500)
                        await element.select_text()
                        await element.type(str(page_number), delay=100)
                        await element.press("Enter")
                        await self.page.wait_for_timeout(4000)
                        
                        # 验证跳转
                        success = await self.verify_page_navigation(page_number)
                        if success:
                            print(f"✅ 通过备用方法成功跳转到第 {page_number} 页")
                            return True
                            
            except Exception as e:
                print(f"⚠️ 备用选择器 {selector} 失败: {e}")
                continue
        
        print(f"❌ 所有输入框定位方法都失败了")
        return False

    # 移除备用URL跳转方法，确保只使用操作式跳转

    async def verify_page_navigation(self, expected_page):
        """
        验证页面是否成功跳转到指定页码
        """
        try:
            # 首先检查输入框中的值
            input_xpath = '//*[@id="app"]/main/div[1]/div[2]/div/div[3]/div/div[2]/div/div/input'
            try:
                input_element = await self.page.query_selector(f"xpath={input_xpath}")
                if input_element:
                    input_value = await input_element.get_attribute('value')
                    if input_value and str(expected_page) == input_value.strip():
                        print(f"✅ 输入框显示页码：{input_value}")
                        return True
            except:
                pass
            
            # 检查URL中的页码参数
            current_url = self.page.url
            if f"pn={expected_page}" in current_url:
                print(f"✅ URL中包含页码参数：pn={expected_page}")
                return True
            
            # 尝试查找页码指示器的多种可能选择器
            page_indicators = [
                f'.be-pager-item[title="{expected_page}"]',
                f'.bili-pagination__item[title="{expected_page}"]',
                f'[data-page="{expected_page}"]',
                '.be-pager-item--current',
                '.bili-pagination__item--current',
                '.be-pager-item.be-pager-item-active',
                '.current-page'
            ]
            
            for selector in page_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        text = await element.text_content()
                        if text and str(expected_page) in text.strip():
                            print(f"✅ 找到页码指示器：{text.strip()}")
                            return True
                except:
                    continue
            
            # 检查页面内容是否发生变化（作为最后的验证手段）
            try:
                # 检查是否有视频内容
                video_selectors = [
                    'a[href*="/video/BV"]',
                    '.video-card',
                    '.bili-video-card'
                ]
                
                for selector in video_selectors:
                    elements = await self.page.query_selector_all(selector)
                    if len(elements) > 0:
                        print(f"✅ 页面包含 {len(elements)} 个视频元素，假设跳转成功")
                        return True
            except:
                pass
            
            print(f"⚠️ 无法确认是否成功跳转到第 {expected_page} 页，但继续执行")
            return True  # 假设成功，继续执行
            
        except Exception as e:
            print(f"⚠️ 验证页面跳转时出错：{e}")
            return True

    async def get_video_urls_with_pagination(self, base_url, page_numbers, xpath=None):
        """
        获取多个页面的视频URL
        
        参数：
            base_url: 基础URL
            page_numbers: 页码列表
            xpath: 用于定位视频链接的XPath表达式
        返回：
            所有页面的视频URL列表
        """
        if xpath is None:
            xpath = '//*[@id="app"]/main/div[1]/div[2]/div/div[2]/div/div/div/div/div/div/div[2]/div[1]/a'
        
        all_video_urls = set()
        
        try:
            await self.setup_browser()
            
            # 设置用户代理
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            for i, page_num in enumerate(page_numbers, 1):
                print(f"\n📄 处理第 {page_num} 页 ({i}/{len(page_numbers)})")
                
                # 跳转到指定页面
                success = await self.navigate_to_page(base_url, page_num)
                if not success:
                    print(f"❌ 跳转到第 {page_num} 页失败，跳过")
                    continue
                
                # 尝试滚动页面以加载更多内容
                await self.scroll_to_load_content()
                
                # 使用XPath查找所有视频链接
                print(f"🔍 在第 {page_num} 页查找视频链接")
                
                # 提取当前页面的视频URL
                page_video_urls = await self.extract_video_urls_multiple_strategies(xpath)
                
                # 添加到总集合中
                page_urls_count = len(page_video_urls)
                new_urls_count = len(set(page_video_urls) - all_video_urls)
                all_video_urls.update(page_video_urls)
                
                print(f"✅ 第 {page_num} 页找到 {page_urls_count} 个URL，其中 {new_urls_count} 个是新的")
                
                # 如果不是最后一页，等待一下再处理下一页
                if i < len(page_numbers):
                    print("⏳ 等待2秒后处理下一页...")
                    await self.page.wait_for_timeout(2000)
            
            return list(all_video_urls)
            
        except Exception as e:
            print(f"❌ 获取多页面视频URL时出错：{e}")
            return list(all_video_urls)

    async def get_video_urls(self, page_url, xpath=None):
        """
        获取单个页面上所有视频的URL (原版方法)

        参数：
            page_url: 要抓取的页面URL
            xpath: 用于定位视频链接的XPath表达式
        返回：
            视频URL列表
        """
        if xpath is None:
            xpath = '//*[@id="app"]/main/div[1]/div[2]/div/div[2]/div/div/div/div/div/div/div[2]/div[1]/a'
        
        try:
            await self.setup_browser()
            
            # 设置用户代理
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            print(f"📱 正在访问页面：{page_url}")
            await self.page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待页面加载完成
            await self.page.wait_for_timeout(3000)
            
            # 尝试滚动页面以加载更多内容
            await self.scroll_to_load_content()
            
            # 使用XPath查找所有视频链接
            print(f"🔍 使用XPath查找视频链接：{xpath}")
            
            # 尝试多种选择器策略
            video_urls = await self.extract_video_urls_multiple_strategies(xpath)
            
            return video_urls
            
        except Exception as e:
            print(f"❌ 获取视频URL时出错：{e}")
            return []
        """
        获取页面上所有视频的URL

        参数：
            page_url: 要抓取的页面URL
            xpath: 用于定位视频链接的XPath表达式
        返回：
            视频URL列表
        """
        if xpath is None:
            xpath = '//*[@id="app"]/main/div[1]/div[2]/div/div[2]/div/div/div/div/div/div/div[2]/div[1]/a'
        
        try:
            await self.setup_browser()
            
            # 设置用户代理
            await self.page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            print(f"📱 正在访问页面：{page_url}")
            await self.page.goto(page_url, wait_until="domcontentloaded", timeout=30000)
            
            # 等待页面加载完成
            await self.page.wait_for_timeout(3000)
            
            # 尝试滚动页面以加载更多内容
            await self.scroll_to_load_content()
            
            # 使用XPath查找所有视频链接
            print(f"🔍 使用XPath查找视频链接：{xpath}")
            
            # 尝试多种选择器策略
            video_urls = await self.extract_video_urls_multiple_strategies(xpath)
            
            return video_urls
            
        except Exception as e:
            print(f"❌ 获取视频URL时出错：{e}")
            return []

    async def extract_video_urls_multiple_strategies(self, primary_xpath):
        """
        使用多种策略提取视频URL
        """
        video_urls = set()
        
        # 策略1: 使用提供的XPath
        try:
            elements = await self.page.locator(f"xpath={primary_xpath}").all()
            for element in elements:
                href = await element.get_attribute('href')
                if href:
                    full_url = self.normalize_bilibili_url(href)
                    if full_url:
                        video_urls.add(full_url)
            print(f"✅ 策略1 (XPath) 找到 {len(video_urls)} 个URL")
        except Exception as e:
            print(f"⚠️ 策略1 (XPath) 失败: {e}")
        
        # 策略2: 通用CSS选择器
        try:
            css_selectors = [
                'a[href*="/video/BV"]',
                'a[href*="bilibili.com/video"]',
                '.video-card a',
                '.bili-video-card a',
                '.card-box a'
            ]
            
            for selector in css_selectors:
                elements = await self.page.locator(selector).all()
                for element in elements:
                    href = await element.get_attribute('href')
                    if href:
                        full_url = self.normalize_bilibili_url(href)
                        if full_url:
                            video_urls.add(full_url)
            
            print(f"✅ 策略2 (CSS选择器) 总共找到 {len(video_urls)} 个唯一URL")
        except Exception as e:
            print(f"⚠️ 策略2 (CSS选择器) 失败: {e}")
        
        # 策略3: 正则表达式匹配页面内容
        try:
            page_content = await self.page.content()
            bv_pattern = r'(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[0-9A-Za-z]{10})'
            matches = re.findall(bv_pattern, page_content)
            
            for bv in set(matches):
                full_url = f"https://www.bilibili.com/video/{bv}"
                video_urls.add(full_url)
            
            print(f"✅ 策略3 (正则表达式) 总共找到 {len(video_urls)} 个唯一URL")
        except Exception as e:
            print(f"⚠️ 策略3 (正则表达式) 失败: {e}")
        
        return list(video_urls)

    def normalize_bilibili_url(self, href):
        """
        标准化B站视频URL
        """
        if not href:
            return None
        
        # 如果是相对路径，补全域名
        if href.startswith('/'):
            href = f"https://www.bilibili.com{href}"
        elif href.startswith('//'):
            href = f"https:{href}"
        
        # 验证是否为有效的B站视频URL
        bv_pattern = r'BV[0-9A-Za-z]{10}'
        if re.search(bv_pattern, href):
            # 提取BV号并构造标准URL
            match = re.search(bv_pattern, href)
            if match:
                bv = match.group(0)
                return f"https://www.bilibili.com/video/{bv}"
        
        return None

    async def scroll_to_load_content(self):
        """
        滚动页面以加载更多内容
        """
        try:
            print("📜 滚动页面以加载更多内容...")
            
            # 获取页面高度
            last_height = await self.page.evaluate("document.body.scrollHeight")
            
            scroll_attempts = 0
            max_scrolls = 5  # 最多滚动5次
            
            while scroll_attempts < max_scrolls:
                # 滚动到页面底部
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                
                # 等待新内容加载
                await self.page.wait_for_timeout(2000)
                
                # 获取新的页面高度
                new_height = await self.page.evaluate("document.body.scrollHeight")
                
                # 如果高度没有变化，说明没有更多内容了
                if new_height == last_height:
                    break
                
                last_height = new_height
                scroll_attempts += 1
                print(f"   📜 滚动 {scroll_attempts}/{max_scrolls} 次")
            
            # 滚动回顶部
            await self.page.evaluate("window.scrollTo(0, 0)")
            await self.page.wait_for_timeout(1000)
            
        except Exception as e:
            print(f"⚠️ 滚动页面时出错: {e}")

    async def close(self):
        """关闭浏览器连接"""
        try:
            if not self.use_existing_browser and self.browser:
                await self.browser.close()
                print("🔒 新建的浏览器实例已关闭")
            elif self.use_existing_browser:
                print("🔗 保持现有浏览器连接")
            
            if self.playwright:
                await self.playwright.stop()
                print("🎭 Playwright连接已断开")
        except Exception as e:
            print(f"⚠️ 关闭浏览器时出错：{e}")


async def collect_urls_multi_page(base_url, page_numbers, xpath=None):
    """
    收集多个页面上的所有视频URL
    
    参数：
        base_url: 基础页面URL
        page_numbers: 页码列表
        xpath: 可选的XPath表达式
    """
    collector = BilibiliUrlCollector(use_existing_browser=True, debug_port=9222)
    
    try:
        video_urls = await collector.get_video_urls_with_pagination(base_url, page_numbers, xpath)
        
        if video_urls:
            print(f"\n🎉 总共找到 {len(video_urls)} 个唯一视频URL:")
            
            # 输出逗号分隔的URL
            urls_string = ','.join(video_urls)
            print(f"\n📋 逗号分隔的URL列表:")
            print(urls_string)
            
            # 同时保存到文件
            with open('video_urls.txt', 'w', encoding='utf-8') as f:
                f.write(urls_string)
            print(f"\n💾 URL列表已保存到 video_urls.txt")
            
            return video_urls
        else:
            print("❌ 没有找到任何视频URL")
            return []
            
    except Exception as e:
        print(f"❌ 收集URL时出错：{e}")
        return []
    
    finally:
        await collector.close()


async def collect_urls(page_url, xpath=None):
    """
    收集页面上的所有视频URL (原有的单页面版本)
    
    参数：
        page_url: 要抓取的页面URL
        xpath: 可选的XPath表达式
    """
    collector = BilibiliUrlCollector(use_existing_browser=True, debug_port=9222)
    
    try:
        video_urls = await collector.get_video_urls(page_url, xpath)
        
        if video_urls:
            print(f"\n🎉 成功找到 {len(video_urls)} 个视频URL:")
            
            # 输出逗号分隔的URL
            urls_string = ','.join(video_urls)
            print(f"\n📋 逗号分隔的URL列表:")
            print(urls_string)
            
            # 同时保存到文件
            with open('video_urls.txt', 'w', encoding='utf-8') as f:
                f.write(urls_string)
            print(f"\n💾 URL列表已保存到 video_urls.txt")
            
            return video_urls
        else:
            print("❌ 没有找到任何视频URL")
            return []
            
    except Exception as e:
        print(f"❌ 收集URL时出错：{e}")
        return []
    
    finally:
        await collector.close()


def parse_page_input(page_input):
    """
    解析页码输入
    
    参数：
        page_input: 页码输入字符串，支持格式如 "1", "1,3,5", "1-5"
    返回：
        页码列表
    """
    page_numbers = []
    
    try:
        # 处理逗号分隔的页码
        parts = page_input.split(',')
        
        for part in parts:
            part = part.strip()
            
            # 处理范围格式 (如 "1-5")
            if '-' in part:
                start, end = part.split('-')
                start_num = int(start.strip())
                end_num = int(end.strip())
                page_numbers.extend(range(start_num, end_num + 1))
            else:
                # 单个页码
                page_numbers.append(int(part))
        
        # 去重并排序
        page_numbers = sorted(list(set(page_numbers)))
        
    except ValueError as e:
        print(f"❌ 页码格式错误：{e}")
        return []
    
    return page_numbers


def interactive_main():
    """交互式主函数"""
    print("🎯 === B站视频URL收集工具 (交互式) ===")
    print("\n💡 请确保Chrome浏览器已开启调试模式：")
    print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    
    # 获取基础URL
    base_url = input("\n📄 请输入基础页面URL (如: https://space.bilibili.com/123456/video): ").strip()
    if not base_url:
        print("❌ URL不能为空")
        return
    
    # 获取页码
    print("\n📋 页码输入格式说明:")
    print("   单页: 1")
    print("   多页: 1,3,5")
    print("   范围: 1-5")
    print("   混合: 1,3-5,8")
    
    page_input = input("\n📄 请输入要抓取的页码: ").strip()
    if not page_input:
        print("❌ 页码不能为空")
        return
    
    # 解析页码
    page_numbers = parse_page_input(page_input)
    if not page_numbers:
        print("❌ 页码解析失败")
        return
    
    # 可选的自定义XPath
    custom_xpath = input("\n🎯 请输入自定义XPath (可选，直接回车使用默认): ").strip()
    xpath = custom_xpath if custom_xpath else None
    
    print(f"\n📊 任务概览:")
    print(f"   🔗 基础URL: {base_url}")
    print(f"   📄 页码: {page_numbers}")
    print(f"   🎯 XPath: {xpath or '使用默认'}")
    
    confirm = input("\n❓ 确认开始抓取? (y/N): ").strip().lower()
    if confirm not in ['y', 'yes']:
        print("❌ 任务已取消")
        return
    
    print("\n🔄 开始收集URL...\n")
    
    # 运行异步任务 - 使用纯操作式跳转
    if len(page_numbers) == 1:
        # 单页面处理，也使用操作式跳转
        asyncio.run(collect_urls_multi_page(base_url, page_numbers, xpath))
    else:
        # 多页面处理
        asyncio.run(collect_urls_multi_page(base_url, page_numbers, xpath))


def main():
    """主函数"""
    # 检查是否有命令行参数
    if len(sys.argv) == 1:
        # 没有参数，使用交互式模式
        interactive_main()
    elif len(sys.argv) >= 2:
        # 有参数，使用命令行模式
        if sys.argv[1] in ['-h', '--help', 'help']:
            print_help()
            return
        
        page_url = sys.argv[1]
        xpath = sys.argv[2] if len(sys.argv) > 2 else None
        
        print("🎯 === B站视频URL收集工具 (命令行模式) ===")
        print(f"📄 目标页面：{page_url}")
        if xpath:
            print(f"🎯 使用XPath：{xpath}")
        
        print("\n💡 请确保Chrome浏览器已开启调试模式：")
        print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
        print("\n🔄 开始收集URL...\n")
        
        # 运行异步任务 - 提取页码并使用操作式跳转
        # 从URL中提取页码
        page_number = 1
        if 'pn=' in page_url:
            import urllib.parse as urlparse
            parsed = urlparse.urlparse(page_url)
            params = urlparse.parse_qs(parsed.query)
            if 'pn' in params:
                try:
                    page_number = int(params['pn'][0])
                except:
                    page_number = 1
        
        # 获取基础URL（去掉页码参数）
        base_url = page_url.split('?')[0] if '?' in page_url else page_url
        
        # 使用操作式跳转
        asyncio.run(collect_urls_multi_page(base_url, [page_number], xpath))


def print_help():
    """显示帮助信息"""
    print("🎯 === B站视频URL收集工具 ===")
    print("\n📖 使用方法:")
    print("  交互式模式:")
    print("    python get_urls.py")
    print("    然后按提示输入URL和页码")
    print("\n  命令行模式:")
    print("    python get_urls.py <page_url> [xpath]")
    print("\n📋 示例:")
    print("  交互式:")
    print("    python get_urls.py")
    print("\n  命令行:")
    print('    python get_urls.py "https://space.bilibili.com/123456/video"')
    print('    python get_urls.py "https://space.bilibili.com/123456/video" "//*[@id=\'app\']/main/div[1]/div[2]/div/div[2]/div/div/div/div/div/div/div[2]/div[1]/a"')
    print("\n🎯 页码格式说明 (仅交互式模式):")
    print("    单页: 1")
    print("    多页: 1,3,5")
    print("    范围: 1-5")
    print("    混合: 1,3-5,8")
    print("\n💡 使用前请确保Chrome浏览器已开启调试模式：")
    print("    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")


if __name__ == "__main__":
    main()
