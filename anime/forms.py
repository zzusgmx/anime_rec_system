# anime/forms.py

from django import forms
from .models import Anime, AnimeType
from django.utils.text import slugify
import uuid


class AnimeTypeForm(forms.ModelForm):
    """动漫类型表单：用于创建和更新动漫类型"""

    class Meta:
        model = AnimeType
        fields = ['name', 'description', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '例如：少年、热血、科幻'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': '输入该类型的详细描述...'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用于URL的标识符，留空将自动生成'})
        }

    def clean_slug(self):
        """自动生成slug（如果未提供）"""
        slug = self.cleaned_data.get('slug')
        name = self.cleaned_data.get('name')

        # 如果未提供slug，则根据名称自动生成
        if not slug and name:
            slug = slugify(name)

            # 检查slug是否已存在，存在则添加随机后缀
            if AnimeType.objects.filter(slug=slug).exists():
                # 避免修改自己时判断重复
                if self.instance and self.instance.pk and self.instance.slug == slug:
                    return slug

                slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        return slug


class AnimeForm(forms.ModelForm):
    """动漫表单：用于创建和更新动漫信息"""

    # 添加额外字段，用于展示而非直接映射到模型
    release_year = forms.IntegerField(
        required=False,
        min_value=1900,
        max_value=2100,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '发布年份'})
    )

    class Meta:
        model = Anime
        fields = [
            'title', 'original_title', 'slug', 'description',
            'cover', 'release_date', 'episodes', 'duration',
            'type', 'is_featured', 'is_completed'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '动漫标题', 'required': True}),
            'original_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '原始标题（可选）'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '用于URL的标识符，留空将自动生成'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 5, 'placeholder': '详细描述...', 'required': True}),
            'cover': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'release_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'required': True}),
            'episodes': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '集数', 'required': True}),
            'duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '每集时长（分钟）'}),
            'type': forms.Select(attrs={'class': 'form-select', 'required': True}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        error_messages = {
            'title': {'required': '请输入动漫标题'},
            'description': {'required': '请输入动漫描述'},
            'release_date': {'required': '请选择发布日期'},
            'episodes': {'required': '请输入集数'},
            'type': {'required': '请选择动漫类型'},
        }

    def __init__(self, *args, **kwargs):
        """自定义初始化方法，为类型字段添加查询集"""
        super().__init__(*args, **kwargs)

        # 优化类型下拉列表：按名称排序
        self.fields['type'].queryset = AnimeType.objects.all().order_by('name')

        # 如果实例已存在，填充发布年份
        if self.instance and self.instance.pk and self.instance.release_date:
            self.initial['release_year'] = self.instance.release_date.year

        # 增加表单字段的提示信息
        self.fields['title'].help_text = "动漫的中文标题"
        self.fields['original_title'].help_text = "动漫的原始/日文标题（可选）"
        self.fields['cover'].help_text = "推荐尺寸：600×900像素，大小不超过5MB"
        self.fields['episodes'].help_text = "总集数，OVA可填1"
        self.fields['is_featured'].help_text = "标记为推荐将在首页展示"
        self.fields['is_completed'].help_text = "动漫是否已完结"

    def clean_slug(self):
        """自动生成slug（如果未提供）"""
        slug = self.cleaned_data.get('slug')
        title = self.cleaned_data.get('title')

        # 如果未提供slug，则根据标题自动生成
        if not slug and title:
            slug = slugify(title)

            # 检查slug是否已存在且不是当前实例，存在则添加随机后缀
            if Anime.objects.filter(slug=slug).exists():
                # 如果当前实例已存在且slug未变，则不需生成新slug
                if self.instance and self.instance.pk and self.instance.slug == slug:
                    return slug

                # 否则生成带随机值的新slug
                slug = f"{slug}-{str(uuid.uuid4())[:8]}"

        return slug

    def clean(self):
        """表单整体验证，处理日期和年份的同步"""
        cleaned_data = super().clean()
        release_date = cleaned_data.get('release_date')
        release_year = cleaned_data.get('release_year')

        # 如果提供了年份但没有日期，创建带该年份的默认日期
        if release_year and not release_date:
            from datetime import date
            cleaned_data['release_date'] = date(release_year, 1, 1)

        # 验证封面文件（如果提供）
        cover = cleaned_data.get('cover')
        if cover and hasattr(cover, 'size'):
            # 检查文件大小（5MB限制）
            if cover.size > 5 * 1024 * 1024:
                self.add_error('cover', '图片大小不能超过5MB')

            # 检查文件类型
            import os
            ext = os.path.splitext(cover.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                self.add_error('cover', '只支持JPG、PNG和WEBP格式的图片')

        return cleaned_data


class AnimeSearchForm(forms.Form):
    """动漫搜索表单：用于高级搜索功能"""

    query = forms.CharField(
        label='搜索',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '输入动漫标题或描述关键词...',
            'autocomplete': 'off'
        })
    )

    type = forms.ModelChoiceField(
        label='类型',
        required=False,
        queryset=AnimeType.objects.all().order_by('name'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    min_rating = forms.FloatField(
        label='最低评分',
        required=False,
        min_value=0,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最低评分',
            'step': '0.1'
        })
    )

    is_completed = forms.BooleanField(
        label='已完结',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    is_featured = forms.BooleanField(
        label='推荐作品',
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    sort_by = forms.ChoiceField(
        label='排序方式',
        required=False,
        choices=[
            ('-popularity', '热门度（高到低）'),
            ('popularity', '热门度（低到高）'),
            ('-rating_avg', '评分（高到低）'),
            ('rating_avg', '评分（低到高）'),
            ('-release_date', '发布日期（新到旧）'),
            ('release_date', '发布日期（旧到新）'),
            ('title', '标题（A-Z）'),
            ('-title', '标题（Z-A）'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )