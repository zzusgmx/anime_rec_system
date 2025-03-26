# Generated by Django 5.1.7 on 2025-03-25 08:51
#templatetags
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('anime', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserComment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('content', models.TextField(verbose_name='评论内容')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('like_count', models.PositiveIntegerField(default=0, verbose_name='点赞数')),
                ('anime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='anime.anime', verbose_name='动漫')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户评论',
                'verbose_name_plural': '用户评论列表',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='UserFavorite',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('anime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorited_by', to='anime.anime', verbose_name='动漫')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='favorites', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户收藏',
                'verbose_name_plural': '用户收藏列表',
            },
        ),
        migrations.CreateModel(
            name='UserLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('comment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='recommendation.usercomment', verbose_name='评论')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户点赞',
                'verbose_name_plural': '用户点赞列表',
            },
        ),
        migrations.CreateModel(
            name='UserRating',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('rating', models.FloatField(verbose_name='评分')),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('anime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to='anime.anime', verbose_name='动漫')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ratings', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '用户评分',
                'verbose_name_plural': '用户评分列表',
            },
        ),
        migrations.CreateModel(
            name='RecommendationCache',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('score', models.FloatField(verbose_name='推荐分数')),
                ('rec_type', models.CharField(choices=[('CF', '协同过滤'), ('CB', '基于内容'), ('POP', '热门推荐')], max_length=3, verbose_name='推荐类型')),
                ('expires_at', models.DateTimeField(verbose_name='过期时间')),
                ('anime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recommended_to', to='anime.anime', verbose_name='推荐动漫')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cached_recommendations', to=settings.AUTH_USER_MODEL, verbose_name='用户')),
            ],
            options={
                'verbose_name': '推荐缓存',
                'verbose_name_plural': '推荐缓存列表',
                'ordering': ['-score'],
                'indexes': [models.Index(fields=['user', '-score'], name='user_rec_score_idx'), models.Index(fields=['expires_at'], name='rec_expiry_idx')],
            },
        ),
        migrations.AddIndex(
            model_name='usercomment',
            index=models.Index(fields=['anime', '-timestamp'], name='anime_comment_time_idx'),
        ),
        migrations.AddIndex(
            model_name='usercomment',
            index=models.Index(fields=['user', '-timestamp'], name='user_comment_time_idx'),
        ),
        migrations.AddIndex(
            model_name='userfavorite',
            index=models.Index(fields=['user', '-timestamp'], name='user_favorite_time_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userfavorite',
            unique_together={('user', 'anime')},
        ),
        migrations.AddIndex(
            model_name='userlike',
            index=models.Index(fields=['comment', '-timestamp'], name='comment_like_time_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userlike',
            unique_together={('user', 'comment')},
        ),
        migrations.AddIndex(
            model_name='userrating',
            index=models.Index(fields=['user', '-timestamp'], name='user_rating_time_idx'),
        ),
        migrations.AddIndex(
            model_name='userrating',
            index=models.Index(fields=['anime', '-rating'], name='anime_rating_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='userrating',
            unique_together={('user', 'anime')},
        ),
    ]
