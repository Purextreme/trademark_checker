"""
商标查询系统配置文件
"""

# 商标类别说明
NICE_CLASS_MAP = {
    "14": "贵重金属及合金等",
    "20": "家具镜子相框等",
    "21": "家庭或厨房用具及容器等"
}

# TMDN配置
TMDN_CONFIG = {
    "base_url": "https://www.tmdn.org/tmview/api/search/results",
    "headers": {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "Origin": "https://www.tmdn.org",
        "Referer": "https://www.tmdn.org/tmview/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    },
    "regions": {
        "美国": {
            "offices": ["US"],
            "territories": ["US"]
        },
        "美国+欧洲": {
            "offices": ["EM", "FR", "GB", "ES", "US", "DE", "IT", "JP"],
            "territories": [
                "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
                "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
                "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GB", "JP", "US"
            ]
        }
    }
}

# WIPO配置
WIPO_CONFIG = {
    "base_url": "https://branddb.wipo.int/en/similarname/results",
    "regions": {
        "美国": {
            "designations": ["US"]
        },
        "美国+欧洲": {
            "designations": ["GB", "US", "DE", "EM", "ES", "FR", "IT"]
        }
    },
    "max_retries": 3,
    "retry_delay": 5  # 重试间隔秒数
}

# 本地数据库配置
LOCAL_DB_CONFIG = {
    "csv_file": "checked_name.csv",
    "encoding": "utf-8",
    "columns": {
        "name": "使用词汇",
        "region": "风险国家",
        "nice_class": "类别"
    }
}

# 查询结果状态
QUERY_STATUS = {
    "LOCAL_MATCH": "以下名称之前已经查询过啦",
    "EXACT_MATCH": "存在完全匹配",
    "NEED_ATTENTION": "需要注意",
    "NO_MATCH": "未查询到匹配结果",
    "ERROR": "查询出错"
}

# 查询参数
QUERY_PARAMS = {
    "max_names_per_query": 100,  # 每次最多查询的名称数量
    "page_size": 30,  # 每页显示的结果数量
    "wipo_display_limit": 15  # WIPO系统显示限制
} 