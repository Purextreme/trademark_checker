"""
商标查询系统配置文件
"""

# 商标类别说明
NICE_CLASS_MAP = {
    "14": "贵重金属及合金等",
    "20": "家具镜子相框等",
    "21": "家庭或厨房用具及容器等"
}

# UK商标系统配置
UK_CONFIG = {
    "base_url": "https://trademarks.ipo.gov.uk/ipo-tmtext",
    "page_size": "50",
    "legal_status": "LIVELEGALSTATUS",
    "timeout": 30000,  # 30秒
    "viewport": {
        "width": 1920,
        "height": 1080
    },
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "nice_classes": {
        "14": {
            "index": "14",
            "description": "14 - Jewellery and watches"
        },
        "20": {
            "index": "20",
            "description": "20 - Furniture and furnishings"
        },
        "21": {
            "index": "21",
            "description": "21 - Household utensils; glassware, porcelain and earthenware"
        }
    }
}

# TMDN配置
TMDN_CONFIG = {
    "base_url": "https://www.tmdn.org/tmview/api/search/results",
    "headers": {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Content-Type": "application/json; charset=utf-8",
        "DNT": "1",
        "Origin": "https://www.tmdn.org",
        "Referer": "https://www.tmdn.org/tmview/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows"
    },
    "regions": {
        "美国": {
            "offices": ["US"],
            "territories": ["US"]
        },
        "英国": {
            "offices": ["GB"],
            "territories": ["GB"]
        },
        "欧盟": {
            "offices": ["EM", "FR", "ES", "DE", "IT"],
            "territories": [
                "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
                "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
                "PL", "PT", "RO", "SK", "SI", "ES", "SE"
            ]
        }
    },
    "request_defaults": {
        "page": "1",
        "pageSize": "30",
        "criteria": "C",
        "tmStatus": ["Filed", "Registered"],
        "newPage": True,
        "fields": [
            "ST13", "markImageURI", "tmName", "tmOffice", "applicationNumber",
            "applicationDate", "tradeMarkStatus", "niceClass", "applicantName"
        ]
    }
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
    "NO_MATCH": "未查询到匹配结果",
    "ERROR": "查询出错"
}

# 查询参数
QUERY_PARAMS = {
    "max_names_per_query": 100,  # 每次最多查询的名称数量
    "page_size": 30  # 每页显示的结果数量
}

# 美国商标系统配置
US_CONFIG = {
    "base_url": "https://tmsearch.uspto.gov/api-v1-0-0/tmsearch",
    "headers": {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9,en;q=0.8",
        "content-type": "application/json",
        "dnt": "1",
        "origin": "https://tmsearch.uspto.gov",
        "priority": "u=1, i",
        "referer": "https://tmsearch.uspto.gov/search/search-results",
        "sec-ch-ua": '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36"
    },
    "nice_classes": {
        "14": "014",
        "20": "020",
        "21": "021"
    },
    "request_defaults": {
        "size": 100,
        "from": 0,
        "track_total_hits": True
    }
} 