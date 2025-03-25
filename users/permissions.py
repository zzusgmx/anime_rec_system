# users/permissions.py

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    对象所有者权限
    确保用户只能访问/修改自己的资源
    """

    def has_object_permission(self, request, view, obj):
        """
        检查请求用户是否为对象所有者
        Args:
            request: 当前HTTP请求对象
            view: 当前视图实例
            obj: 当前操作的对象实例
        Returns:
            bool: 如果用户是对象所有者，返回True
        """
        # 查看obj是否有user属性(如Profile)，或者通过属性路径查找(如UserRating.user)
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id

        # 如果obj本身就是User实例
        if hasattr(obj, 'id') and hasattr(request.user, 'id'):
            return obj.id == request.user.id

        return False


class IsModeratorOrAdmin(permissions.BasePermission):
    """
    管理员或内容审核员权限
    用于内容管理功能
    """

    def has_permission(self, request, view):
        """
        检查用户是否为管理员或内容审核员
        Args:
            request: 当前HTTP请求对象
            view: 当前视图实例
        Returns:
            bool: 如果用户是管理员或内容审核员，返回True
        """
        # 检查用户是否已认证
        if not request.user or not request.user.is_authenticated:
            return False

        # 管理员直接通过
        if request.user.is_staff:
            return True

        # 检查用户是否属于审核员组
        return request.user.groups.filter(name='Moderators').exists()


class ReadOnly(permissions.BasePermission):
    """
    只读权限
    允许GET, HEAD, OPTIONS请求，禁止其他操作
    """

    def has_permission(self, request, view):
        """
        检查请求是否为安全方法（只读操作）
        Args:
            request: 当前HTTP请求对象
            view: 当前视图实例
        Returns:
            bool: 如果是只读操作，返回True
        """
        return request.method in permissions.SAFE_METHODS


# 自定义装饰器 - 用于视图函数的权限控制
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden
from functools import wraps


def moderator_required(view_func):
    """
    检查用户是否为管理员或内容审核员的装饰器
    用于限制视图函数访问
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # 检查用户权限
        if request.user.is_staff or request.user.groups.filter(name='Moderators').exists():
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("您没有权限执行此操作")

    return _wrapped_view


def owner_required(model_class):
    """
    检查用户是否为资源所有者的装饰器
    Args:
        model_class: 要检查所有权的模型类
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 获取对象ID
            obj_id = kwargs.get('pk') or kwargs.get('id')

            if not obj_id:
                return HttpResponseForbidden("无法验证资源所有权")

            try:
                # 查询对象
                obj = model_class.objects.get(pk=obj_id)

                # 检查所有权
                if hasattr(obj, 'user') and obj.user == request.user:
                    return view_func(request, *args, **kwargs)
                elif hasattr(obj, 'user_id') and obj.user_id == request.user.id:
                    return view_func(request, *args, **kwargs)
                else:
                    return HttpResponseForbidden("您不是该资源的所有者")
            except model_class.DoesNotExist:
                return HttpResponseForbidden("资源不存在")

        return _wrapped_view

    return decorator