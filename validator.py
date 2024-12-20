import re

def validate_name(name: str) -> tuple[bool, str]:
    """
    验证商标名称是否符合规则
    返回: (是否有效, 错误信息或处理后的名称)
    """
    # 去除前后空格
    name = name.strip()
    
    # 检查是否为空
    if not name:
        return False, "名称不能为空"
    
    # 检查是否包含空格
    if ' ' in name:
        return False, "名称不能包含空格"
    
    # 只允许英文字母
    if not name.isalpha():
        return False, "名称只能包含英文字母"
    
    return True, name