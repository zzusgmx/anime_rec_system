import os
import platform
import logging

logger = logging.getLogger('django')


def resolve_platform_path(path_string):
    """原子级跨平台路径解析器 - 量子态容错"""

    # 输入检查
    if not path_string:
        return None

    # 规范化路径分隔符
    normalized = path_string.replace('\\', '/')

    # 扩展用户路径 (~)
    expanded = os.path.expanduser(normalized)

    # 转换为绝对路径
    abs_path = os.path.abspath(expanded)

    # 平台适配校验
    system = platform.system()
    if system == 'Windows':
        # Windows 特殊处理
        if ':' not in abs_path and len(abs_path) > 2:
            # 可能是相对路径，尝试从当前目录解析
            alt_path = os.path.join(os.getcwd(), abs_path)
            if os.path.exists(alt_path):
                abs_path = alt_path
                logger.info(f"Windows 路径修复: {path_string} → {abs_path}")

    # 存在性检查
    if not os.path.exists(abs_path):
        logger.warning(f"路径不存在: {abs_path} (原始: {path_string})")
        # 父目录检查
        parent = os.path.dirname(abs_path)
        if os.path.exists(parent):
            logger.info(f"父目录存在: {parent}")
            # 列出父目录内容以辅助调试
            try:
                logger.info(f"父目录内容: {', '.join(os.listdir(parent))}")
            except:
                pass
        return None

    return abs_path