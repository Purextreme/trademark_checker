import re
from typing import Tuple

def validate_name(name: str) -> Tuple[bool, str]:
    """验证商标名称是否合法
    Args:
        name: 要验证的商标名称
    Returns:
        (is_valid, message): 是否合法及消息
        如果合法，返回 (True, 处理后的名称)
        如果不合法，返回 (False, 错误消息)
    """
    # 去除前后空格
    name = name.strip()
    
    # 检查是否为空
    if not name:
        return False, "名称不能为空"
    
    # 检查是否包含特殊字符（只允许字母、数字和空格）
    if not re.match(r'^[a-zA-Z0-9\s]*$', name):
        return False, "名称只能包含字母和数字"
    
    # 检查是否包含多个单词
    words = name.split()
    if len(words) > 1:
        return False, "名称只能是一个单词，不能包含空格"
    
    # 检查长度限制
    if len(name) > 50:  # 设置一个合理的长度限制
        return False, "名称长度不能超过50个字符"
    
    # 检查是否只包含数字
    if name.isdigit():
        return False, "名称不能只包含数字"
    
    return True, name