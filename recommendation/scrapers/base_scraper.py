# recommendation/scrapers/base_scraper.py

import requests
import time
import random
import logging
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('django')


class BaseScraper(ABC):
    """
    爬虫基类 - 定义所有爬虫的通用行为和接口

    高级特性:
    - 速率限制
    - 错误重试
    - 用户代理轮换
    - 异常处理
    - 增量爬取
    """

    def __init__(self, delay=3.0, max_retries=3, timeout=10):
        """
        初始化爬虫基本参数

        Args:
            delay: 请求间隔时间（秒）
            max_retries: 最大重试次数
            timeout: 请求超时时间（秒）
        """
        self.delay = delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self._get_random_user_agent(),
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        self.last_request_time = 0

    def _get_random_user_agent(self):
        """返回随机User-Agent以模拟不同浏览器"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.101 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59',
        ]
        return random.choice(user_agents)

    def _respect_rate_limits(self):
        """确保请求间隔符合速率限制"""
        current_time = time.time()
        time_elapsed = current_time - self.last_request_time

        if time_elapsed < self.delay:
            time.sleep(self.delay - time_elapsed)

        self.last_request_time = time.time()

    def _quantum_encoding_fix(self, text):
        """
        量子编码修复算法 - 处理多重编码污染问题

        算法核心：反向追踪编码转换路径，通过多次编解码实现"退火"效果
        应对场景：特别适合处理被多次错误转码的文本
        """
        if not text:
            return ""

        # 试探性解码-重编码循环
        # 一个更激进的方法是尝试从已经损坏的文本中恢复原始字节
        try:
            # 第一层：逆向到Latin-1字节流
            try_bytes = text.encode('latin1')

            # 第二层：尝试作为UTF-8解码（常见双重编码情况）
            try_decode = try_bytes.decode('utf-8', errors='replace')

            # 质量检测 - 中日韩文字检测启发式算法
            cjk_ratio = sum(1 for c in try_decode if 0x4E00 <= ord(c) <= 0x9FFF) / len(try_decode) if try_decode else 0

            # 如果包含足够比例的CJK字符，认为修复成功
            if cjk_ratio > 0.1:  # 10%以上是CJK字符
                return try_decode

            # 尝试更多组合（针对多次编码损坏的极端情况）
            codec_chains = [
                ('latin1', 'utf-8'),
                ('utf-8', 'latin1', 'utf-8'),
                ('cp1252', 'utf-8'),
                ('gbk', 'utf-8'),
            ]

            for chain in codec_chains:
                try:
                    temp = text
                    # 应用编码链
                    for i, codec in enumerate(chain):
                        if i % 2 == 0:  # 偶数索引进行编码
                            temp = temp.encode(codec)
                        else:  # 奇数索引进行解码
                            temp = temp.decode(codec, errors='replace')

                    # 确保结果是字符串
                    if isinstance(temp, bytes):
                        temp = temp.decode('utf-8', errors='replace')

                    # 再次进行CJK检测
                    cjk_ratio = sum(1 for c in temp if 0x4E00 <= ord(c) <= 0x9FFF) / len(temp) if temp else 0
                    if cjk_ratio > 0.1:
                        return temp
                except:
                    continue
        except:
            pass

        # 终极回退：ASCII过滤
        return ''.join(c if ord(c) < 128 else '?' for c in text)

    def fetch_url(self, url, params=None):
        """
        获取URL内容，带重试和错误处理

        Args:
            url: 要请求的URL
            params: 查询参数

        Returns:
            requests.Response对象或None
        """
        for attempt in range(self.max_retries):
            try:
                # 尊重网站速率限制
                self._respect_rate_limits()

                # 发送请求
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )

                # 检查响应状态
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    logger.warning(f"页面不存在: {url}")
                    return None
                elif response.status_code in (429, 403):
                    # 触发了速率限制或禁止访问
                    wait_time = self.delay * (attempt + 2)
                    logger.warning(f"触发速率限制 ({response.status_code})，等待 {wait_time}秒")
                    time.sleep(wait_time)
                else:
                    logger.warning(f"非200状态码: {response.status_code} 来自 {url}")
                    time.sleep(self.delay)
            except (requests.RequestException, Exception) as e:
                logger.error(f"请求异常 ({attempt + 1}/{self.max_retries}): {e} 来自 {url}")
                time.sleep(self.delay * (attempt + 1))

        logger.error(f"达到最大重试次数，无法获取: {url}")
        return None

    def normalize_text(self, text):
        """
        字节级编码规范化 - 解决多源编码混乱问题

        处理流程:
        1. 尝试检测输入文本的实际编码
        2. 转换为UTF-8统一标准
        3. 清除不可打印字符和控制符
        """
        if not text:
            return ""

        # 如果已经是字符串，尝试修复可能的编码问题
        if isinstance(text, str):
            try:
                # 首先尝试作为utf-8反序列化，这可以捕获错误编码的字符串
                text_bytes = text.encode('raw_unicode_escape')

                # 然后尝试不同的编码格式解码
                for encoding in ['utf-8', 'shift-jis', 'gbk', 'euc-jp']:
                    try:
                        decoded = text_bytes.decode(encoding, errors='strict')
                        return decoded
                    except UnicodeDecodeError:
                        continue

                # 如果都失败，使用宽容模式
                return text_bytes.decode('utf-8', errors='replace')
            except:
                # 如果所有尝试都失败，保留原始文本但替换不可读字符
                return ''.join(ch if ord(ch) < 128 else '?' for ch in text)

        # 如果是字节对象，尝试解码
        elif isinstance(text, bytes):
            try:
                return text.decode('utf-8', errors='replace')
            except:
                return text.decode('latin1', errors='replace')

        return str(text)

    def parse_html(self, html_content):
        """解析HTML内容为BeautifulSoup对象"""
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.error(f"HTML解析错误: {e}")
            return None

    def _anime_exists(self, url):
        """
        检查动漫是否已存在于数据库中
        使用多种判断条件提高准确性
        """
        from anime.models import Anime
        import re

        # 提取URL中的唯一标识
        anime_id = self._extract_id_from_url(url)
        if not anime_id:
            logger.warning(f"无法从URL提取动漫ID: {url}")
            return False

        # 方法1: 通过ID精确匹配
        if Anime.objects.filter(description__regex=f"ID: {anime_id}[^0-9]").exists():
            logger.info(f"动漫 ID: {anime_id} 已存在于数据库中")
            return True

        # 方法2: 通过标题匹配
        try:
            # 从页面获取标题
            response = self.fetch_url(url)
            if response:
                soup = self.parse_html(response.text)
                if soup:
                    title_element = soup.select_one('h1.title-name')
                    if title_element:
                        title = title_element.text.strip()
                        # 标题完全匹配
                        if Anime.objects.filter(title=title).exists():
                            logger.info(f"标题为 '{title}' 的动漫已存在于数据库中")
                            return True

                        # 标题相似性匹配 - 移除特殊字符后比较
                        clean_title = re.sub(r'[^\w\s]', '', title).lower()
                        for anime in Anime.objects.all():
                            clean_db_title = re.sub(r'[^\w\s]', '', anime.title).lower()
                            # 如果标题非常相似
                            if clean_title == clean_db_title:
                                logger.info(f"找到相似标题: DB='{anime.title}' 爬取='{title}'")
                                return True
        except Exception as e:
            logger.error(f"检查标题匹配时出错: {str(e)}")

        return False

    def run(self, start_page=1, max_pages=1, incremental=True, do_import=True):
        """
        运行爬虫主流程

        Args:
            start_page: 开始爬取的页数
            max_pages: 最大爬取页数
            incremental: 是否增量爬取（只获取新内容）
            do_import: 是否将爬取的数据导入数据库

        Returns:
            新增动漫数量
        """
        logger.info(f"启动爬虫: {self.__class__.__name__}")
        logger.info(f"增量爬取模式: {'开启' if incremental else '关闭'}")
        logger.info(f"导入数据库: {'开启' if do_import else '关闭'}")
        logger.info(f"爬取页面: 从第{start_page}页开始，共{max_pages}页")

        total_added = 0
        total_skipped = 0
        total_scraped = 0

        try:
            for page_offset in range(max_pages):
                current_page = start_page + page_offset
                logger.info(f"爬取第 {current_page} 页")

                # 获取动漫列表
                anime_urls = self.scrape_anime_list(current_page)
                if not anime_urls:
                    logger.warning(f"第{current_page}页没有发现动漫URL，跳出循环")
                    break

                logger.info(f"在第 {current_page} 页发现 {len(anime_urls)} 个动漫链接")

                for url in anime_urls:
                    try:
                        # 检查是否已存在（增量爬取模式）
                        if incremental and self._anime_exists(url):
                            logger.info(f"动漫已存在，跳过: {url}")
                            total_skipped += 1
                            continue

                        # 获取动漫详情
                        logger.info(f"获取动漫详情: {url}")
                        anime_data = self.scrape_anime_details(url)
                        if not anime_data:
                            logger.warning(f"无法获取动漫详情: {url}")
                            continue

                        total_scraped += 1

                        # 如果不导入数据库，只统计爬取数量
                        if not do_import:
                            logger.info(f"成功爬取动漫: {anime_data.get('title', '未知标题')} (未导入数据库)")
                            continue

                        # 转换为模型格式并保存
                        model_data = self.convert_to_model(anime_data)
                        if model_data:
                            if self._save_anime(model_data):
                                total_added += 1
                                logger.info(f"成功添加动漫: {model_data.get('title', '未知标题')}")
                            else:
                                logger.error(f"保存动漫失败: {model_data.get('title', '未知标题')}")
                    except Exception as e:
                        logger.error(f"处理动漫URL时出错: {url}, 错误: {str(e)}")
                        continue

                    # 使用指数退避策略的随机延迟
                    base_delay = self.delay
                    random_factor = random.uniform(0.5, 1.5)  # 50%-150%的变化
                    delay_time = base_delay * random_factor
                    logger.debug(f"等待 {delay_time:.2f} 秒后继续")
                    time.sleep(delay_time)

            result_msg = f"爬虫完成: 爬取 {total_scraped} 部动漫"
            if do_import:
                result_msg += f", 导入 {total_added} 部动漫, 跳过 {total_skipped} 部已存在动漫"

            logger.info(result_msg)
            return total_added if do_import else total_scraped

        except Exception as e:
            logger.error(f"爬虫运行异常: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return total_added if do_import else total_scraped

    def _save_anime(self, data):
        """保存动漫数据到数据库"""
        from anime.models import Anime, AnimeType
        from django.db import transaction
        import traceback

        try:
            with transaction.atomic():
                # 获取或创建动漫类型
                anime_type, _ = AnimeType.objects.get_or_create(
                    name=data.get('type', '未分类'),
                    defaults={'description': f'爬虫导入的类型: {data.get("type", "未分类")}'}
                )

                # 创建动漫记录
                anime = Anime(
                    title=data['title'],
                    original_title=data.get('original_title', ''),
                    description=data.get('description', ''),
                    type=anime_type,
                    release_date=data.get('release_date', timezone.now().date()),
                    episodes=data.get('episodes', 1),
                    duration=data.get('duration'),
                    is_completed=data.get('is_completed', False),
                    is_featured=False,
                    popularity=data.get('popularity', 0),
                    rating_avg=data.get('rating', 0),
                    rating_count=data.get('rating_count', 0)
                )

                # 如果有封面URL，下载封面
                if 'cover_url' in data and data['cover_url']:
                    try:
                        image_response = self.fetch_url(data['cover_url'])
                        if image_response:
                            image_content = image_response.content
                            from django.core.files.base import ContentFile
                            import os
                            filename = os.path.basename(data['cover_url'])
                            if not filename or not filename.strip():
                                filename = f"cover_{data['title']}.jpg"
                            if not filename.endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
                                filename += '.jpg'
                            anime.cover.save(filename, ContentFile(image_content), save=False)
                        else:
                            logger.warning(f"无法获取封面图片: {data['cover_url']}")
                    except Exception as e:
                        logger.error(f"封面下载失败: {e}")
                        logger.error(traceback.format_exc())

                anime.save()
                logger.info(f"保存动漫成功: {data['title']}")
                return True

        except Exception as e:
            logger.error(f"保存动漫失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def _extract_id_from_url(self, url):
        """从URL中提取动漫ID"""
        # 默认实现，子类可重写
        import re
        match = re.search(r'/(\d+)/?(?:\?|$)', url)
        if match:
            return match.group(1)
        return None

    def convert_to_model(self, data):
        """
        将爬取的数据转换为模型格式 - 量子态数据规范化

        执行数据在爬虫空间到ORM空间的位相变换，处理编码位错、类型不匹配和
        语义退化等问题。采用多层防御策略确保数据完整性。

        Args:
            data: 爬取的原始数据字典(非规范化态)

        Returns:
            经过规范化处理的模型数据字典(规范化态)
        """
        # 1. 输入数据验证与防御 - 空数据和关键字段缺失检测
        if not data or 'title' not in data or not data['title']:
            return None

        # 2. 文本字段量子编码修复 - 对所有文本字段应用量子编码修复
        for key in ['title', 'original_title', 'description']:
            if key in data and data[key]:
                # 应用更激进的量子编码修复算法
                data[key] = self._quantum_encoding_fix(data[key])

        # 3. 数据规范化与转换 - 构建标准化的模型数据
        model_data = {
            'title': data['title'].strip(),
            'original_title': data.get('original_title', '').strip(),
            'description': data.get('description', '') or f"爬虫导入的动漫。ID: {data.get('id', '')}",
            'type': data.get('type', '未分类'),
            'episodes': int(data.get('episodes', 1)),  # 强制数值类型转换
            'is_completed': bool(data.get('is_completed', False)),  # 显式类型转换
            'cover_url': data.get('cover_url', '')
        }

        # 4. 可选字段处理 - 条件注入
        if 'release_date' in data:
            model_data['release_date'] = data['release_date']

        if 'duration' in data and data['duration']:
            model_data['duration'] = int(data['duration'])

        # 5. 评分数据规范化 - 确保评分在系统期望的范围内
        if 'rating' in data and data['rating']:
            # 确保评分在1-5范围内 (标准化为5分制)
            raw_rating = float(data['rating'])
            # 判断是否需要从10分制转换为5分制
            if raw_rating > 5:
                model_data['rating'] = min(5.0, raw_rating / 2.0)
            else:
                model_data['rating'] = min(5.0, max(0.0, raw_rating))

        if 'rating_count' in data and data['rating_count']:
            try:
                model_data['rating_count'] = int(data['rating_count'])
            except (ValueError, TypeError):
                # 抗噪处理 - 非整数处理
                model_data['rating_count'] = 0

        # 6. 热门度计算 - 合成指标
        if 'popularity' in data and data['popularity'] is not None:
            model_data['popularity'] = float(data['popularity'])
        elif 'rating' in data and 'rating_count' in data:
            # 自合成热门度算法 - 评分权重0.6，评分人数权重0.4
            rating_factor = data['rating'] / 10.0 if data['rating'] > 5 else data['rating'] / 5.0
            count_factor = min(1.0, data['rating_count'] / 5000.0)
            model_data['popularity'] = rating_factor * 0.6 + count_factor * 0.4

        # 7. 数据完整性最终检查
        for key, value in list(model_data.items()):
            if value is None:
                # 从数据字典中移除None值，让ORM使用默认值
                del model_data[key]

        return model_data

    @abstractmethod
    def scrape_anime_list(self, page=1):
        """
        抓取动漫列表页

        Args:
            page: 页码

        Returns:
            动漫URL列表
        """
        pass

    @abstractmethod
    def scrape_anime_details(self, url):
        """
        抓取动漫详情页

        Args:
            url: 动漫详情页URL

        Returns:
            动漫数据字典
        """
        pass