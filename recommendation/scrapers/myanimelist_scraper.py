# recommendation/scrapers/myanimelist_scraper.py

import re
import json
from datetime import datetime
from django.utils import timezone
from .base_scraper import BaseScraper
import logging

logger = logging.getLogger('django')


class MyAnimeListScraper(BaseScraper):
    """
    MyAnimeList爬虫 - 针对全球最大动漫数据库的定向爬虫

    特性:
    - 高精度元数据抽取
    - 内容精确度验证
    """

    def __init__(self, delay=4.0, max_retries=3, timeout=15):
        """初始化MAL爬虫"""
        super().__init__(delay, max_retries, timeout)
        self.base_url = "https://myanimelist.net"

    def scrape_anime_list(self, page=1):
        """获取动漫列表页"""
        # 使用MAL的热门动画排行榜
        offset = (page - 1) * 50
        url = f"{self.base_url}/topanime.php?limit={offset}"
        response = self.fetch_url(url)
        if not response:
            return []

        soup = self.parse_html(response.text)
        if not soup:
            return []

        # 提取动漫URL
        anime_urls = []
        items = soup.select('tr.ranking-list')
        for item in items:
            link = item.select_one('td.title a')
            if link and 'href' in link.attrs:
                href = link['href']
                if href and href.startswith('http'):
                    anime_urls.append(href)
                else:
                    anime_urls.append(self.base_url + href)
        return anime_urls

    def scrape_anime_details(self, url):
        """获取动漫详情页"""
        response = self.fetch_url(url)
        if not response:
            return None

        soup = self.parse_html(response.text)
        if not soup:
            return None

        # 提取动漫ID
        anime_id = self._extract_id_from_url(url)
        if not anime_id:
            logger.warning(f"无法提取动漫ID: {url}")
            return None

        # 提取基本信息
        data = {
            'url': url,
            'id': anime_id
        }

        # 标题
        title_h1 = soup.select_one('h1.title-name')
        if title_h1:
            data['title'] = title_h1.text.strip()

            # 尝试获取原始日文标题
            original_title_span = soup.select_one('p.alternative-titles span.japanese')
            if original_title_span:
                data['original_title'] = original_title_span.text.strip()

        # 封面
        cover = soup.select_one('img[itemprop="image"]')
        if cover and 'data-src' in cover.attrs:
            data['cover_url'] = cover['data-src']
        elif cover and 'src' in cover.attrs:
            data['cover_url'] = cover['src']

        # 描述
        description = soup.select_one('p[itemprop="description"]')
        if description:
            data['description'] = description.text.strip()

        # 侧边信息
        info_div = soup.select_one('.leftside')
        if info_div:
            # 提取类型
            type_div = info_div.select_one('span:-soup-contains("Type:")')
            if type_div and type_div.parent:
                type_text = type_div.parent.text
                type_match = re.search(r'Type:\s*(.+?)(?:\n|$)', type_text)
                if type_match:
                    data['type'] = type_match.group(1).strip()

            # 提取集数
            episodes_div = info_div.select_one('span:-soup-contains("Episodes:")')
            if episodes_div and episodes_div.parent:
                episodes_text = episodes_div.parent.text
                episodes_match = re.search(r'Episodes:\s*(\d+)', episodes_text)
                if episodes_match:
                    data['episodes'] = int(episodes_match.group(1))
                else:
                    # 可能是电影或未知集数
                    data['episodes'] = 1

            # 提取状态
            status_div = info_div.select_one('span:-soup-contains("Status:")')
            if status_div and status_div.parent:
                status_text = status_div.parent.text
                if 'Finished Airing' in status_text:
                    data['is_completed'] = True
                else:
                    data['is_completed'] = False

            # 提取时长
            duration_div = info_div.select_one('span:-soup-contains("Duration:")')
            if duration_div and duration_div.parent:
                duration_text = duration_div.parent.text
                duration_match = re.search(r'(\d+)\s*min', duration_text)
                if duration_match:
                    data['duration'] = int(duration_match.group(1))

            # 提取上映日期
            aired_div = info_div.select_one('span:-soup-contains("Aired:")')
            if aired_div and aired_div.parent:
                aired_text = aired_div.parent.text
                # 尝试提取完整日期
                date_match = re.search(r'(\w+ \d+, \d{4})', aired_text)
                if date_match:
                    try:
                        date_obj = datetime.strptime(date_match.group(1), '%b %d, %Y')
                        data['release_date'] = date_obj.date()
                    except:
                        # 尝试只提取年份
                        year_match = re.search(r'(\d{4})', aired_text)
                        if year_match:
                            try:
                                data['release_date'] = datetime(int(year_match.group(1)), 1, 1).date()
                            except:
                                data['release_date'] = timezone.now().date()

        # 评分信息
        score_div = soup.select_one('div.score-label')
        if score_div:
            try:
                score_text = score_div.text.strip()
                if score_text and score_text != 'N/A':
                    data['rating'] = float(score_text)
            except:
                pass

        # 评分人数
        score_users = soup.select_one('span.score-users strong')
        if score_users:
            try:
                users_text = score_users.text.strip()
                users_text = users_text.replace(',', '')
                data['rating_count'] = int(users_text)
            except:
                pass

        # 排名信息 - 用于计算热门度
        popularity_div = soup.select_one('span:-soup-contains("Popularity:")')
        if popularity_div and popularity_div.parent:
            try:
                popularity_text = popularity_div.parent.text
                popularity_match = re.search(r'#(\d+)', popularity_text)
                if popularity_match:
                    # 越小排名越高，转换为0-1范围的热门度
                    rank = int(popularity_match.group(1))
                    # 根据排名计算热门度，最高5000名以内
                    data['popularity'] = max(0, min(1, 1 - (rank / 5000)))
            except:
                pass

        return data

    def _extract_id_from_url(self, url):
        """从URL中提取动漫ID"""
        match = re.search(r'/anime/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def convert_to_model(self, data):
        """将爬取的数据转换为模型格式"""
        if not data or 'title' not in data or not data['title']:
            return None

        # 标准化数据
        model_data = {
            'title': data['title'],
            'original_title': data.get('original_title', ''),
            'description': data.get('description', '') or f"MyAnimeList动漫。ID: {data.get('id', '')}",
            'type': data.get('type', '未分类'),
            'episodes': data.get('episodes', 1),
            'duration': data.get('duration'),
            'is_completed': data.get('is_completed', False),
            'cover_url': data.get('cover_url', '')
        }

        # 发布日期
        if 'release_date' in data:
            model_data['release_date'] = data['release_date']

        # 评分数据
        if 'rating' in data:
            # MAL评分为10分制，转换为5分制
            model_data['rating'] = min(5.0, data['rating'] / 2.0)
        if 'rating_count' in data:
            model_data['rating_count'] = data['rating_count']

        # 热门度
        if 'popularity' in data:
            model_data['popularity'] = data['popularity']
        elif 'rating' in data and 'rating_count' in data:
            # 根据评分和评分人数计算热门度
            popularity = min(1.0, (data['rating'] / 10.0) * 0.6 + (min(1.0, data['rating_count'] / 10000.0) * 0.4))
            model_data['popularity'] = popularity

        return model_data