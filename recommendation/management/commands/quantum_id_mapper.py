# 创建文件：quantum_id_mapper.py
from django.core.management.base import BaseCommand
from anime.models import Anime
import pandas as pd
from fuzzywuzzy import process  # 高级模糊匹配库 (pip install fuzzywuzzy python-Levenshtein)
import re


class Command(BaseCommand):
    help = 'ID空间量子映射器 - 执行Kaggle→爬虫ID的概率映射'

    def add_arguments(self, parser):
        parser.add_argument('--kaggle', type=str, required=True, help='Kaggle动漫CSV路径')
        parser.add_argument('--threshold', type=int, default=90, help='标题匹配阈值(0-100)')

    def handle(self, *args, **options):
        # 1. 加载数据源
        kaggle_df = pd.read_csv(options['kaggle'])
        db_animes = list(Anime.objects.values_list('id', 'title', 'description'))

        # 2. 生成标题映射表
        db_titles = [x[1] for x in db_animes]
        self.stdout.write(f"🧠 启动模糊匹配引擎: {len(db_titles)} DB记录 vs {len(kaggle_df)} Kaggle记录")

        # 3. 原子精确匹配通道 - O(n) 线性扫描
        exact_matches = 0
        fuzzy_matches = 0

        for _, krow in kaggle_df.iterrows():
            kid = krow['anime_id']
            ktitle = krow['name']

            # 尝试精确匹配
            match = None
            for dbid, dbtitle, dbdesc in db_animes:
                if ktitle.lower() == dbtitle.lower():
                    match = (dbid, 100)
                    break

            # 回退到模糊匹配 - O(n²)复杂度，但只针对未匹配项
            if not match:
                # 执行模糊匹配，返回(match, score)
                match_result = process.extractOne(ktitle, db_titles)
                if match_result and match_result[1] >= options['threshold']:
                    # 找到模糊匹配的DB ID
                    idx = db_titles.index(match_result[0])
                    match = (db_animes[idx][0], match_result[1])
                    fuzzy_matches += 1

            # 应用匹配结果
            if match:
                dbid, score = match
                anime = Anime.objects.get(id=dbid)

                # 注入Kaggle ID到描述中 - 创建双向映射
                id_pattern = r"Kaggle ID: \d+"
                if "Kaggle ID:" not in anime.description:
                    anime.description = f"{anime.description}\nKaggle ID: {kid}"
                    anime.save(update_fields=['description'])

                    if score == 100:
                        exact_matches += 1
                    self.stdout.write(f"✅ 映射: {ktitle} → {anime.title} (Score:{score}%)")

        self.stdout.write(f"🔄 映射完成: {exact_matches}精确匹配 + {fuzzy_matches}模糊匹配")