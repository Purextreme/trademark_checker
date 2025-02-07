import logging
from typing import Dict, Any, Union, List
import requests
from config import US_CONFIG
import json

class USChecker:
    def __init__(self):
        """初始化美国商标查询器"""
        self.config = US_CONFIG
        self.logger = logging.getLogger("USChecker")
        self.logger.setLevel(logging.INFO)

    def _build_query_payload(self, query_name: str, nice_classes: List[str]) -> Dict[str, Any]:
        """构建查询请求体
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别列表
        Returns:
            Dict: 查询请求体
        """
        # 将类别编号格式化为三位数字字符串
        formatted_classes = [self.config["nice_classes"][cls] for cls in nice_classes if cls in self.config["nice_classes"]]
        
        return {
            "query": {
                "bool": {
                    "must": [{
                        "bool": {
                            "should": [
                                {
                                    "match_phrase": {
                                        "WM": {
                                            "query": query_name,
                                            "boost": 5
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "WM": {
                                            "query": query_name,
                                            "boost": 2
                                        }
                                    }
                                },
                                {
                                    "match_phrase": {
                                        "PM": {
                                            "query": query_name,
                                            "boost": 2
                                        }
                                    }
                                }
                            ]
                        }
                    }],
                    "filter": [
                        {
                            "term": {
                                "LD": "true"
                            }
                        },
                        {
                            "terms": {
                                "IC": formatted_classes
                            }
                        }
                    ]
                }
            },
            "size": 200,
            "from": 0,
            "track_total_hits": True,
            "_source": ["wordmark"]  # 只获取商标名
        }

    def search_trademark(self, query_name: str, nice_classes: Union[str, List[str]]) -> Dict[str, Any]:
        """搜索美国商标
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别（可以是单个类别字符串或类别列表）
        Returns:
            Dict: 查询结果
        """
        if isinstance(nice_classes, str):
            nice_classes = [nice_classes]

        try:
            self.logger.info(f"开始查询美国商标: {query_name} (类别: {', '.join(nice_classes)})")
            
            # 构建请求体
            payload = self._build_query_payload(query_name, nice_classes)
            
            # 构建请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'content-type': 'application/json',
                'origin': 'https://tmsearch.uspto.gov',
                'priority': 'u=1, i',
                'referer': 'https://tmsearch.uspto.gov/search/search-results',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
            }
            
            # 发送请求
            response = requests.post(
                'https://tmsearch.uspto.gov/api-v1-0-0/tmsearch',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            # 提取匹配结果
            hits = result.get("hits", {})
            hits_list = hits.get("hits", [])
            total = hits.get("totalValue", 0)  # 使用API返回的totalValue
            
            # 只提取商标名称
            brand_names = []
            for hit in hits_list:
                if 'source' in hit and 'wordmark' in hit['source']:
                    brand_name = hit['source']['wordmark']
                    if brand_name:
                        brand_names.append(brand_name)
                elif '_source' in hit and 'wordmark' in hit['_source']:
                    brand_name = hit['_source']['wordmark']
                    if brand_name:
                        brand_names.append(brand_name)
            
            self.logger.info(f"查询完成，找到 {total} 个商标名称")
            
            # 使用新的返回格式
            if brand_names:
                return {
                    "success": True,
                    "data": brand_names  # 直接返回商标列表
                }
            
            return {
                "success": True,
                "data": "NO_RESULTS"
            }
            
        except requests.RequestException as e:
            error_msg = f"查询美国商标时发生错误: {str(e)}"
            self.logger.error(error_msg)
            if hasattr(e.response, 'text'):
                print(f"错误响应内容: {e.response.text[:500]}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"处理查询结果时发生错误: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

def main():
    """主函数，用于测试"""
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(level=logging.DEBUG)
    
    checker = USChecker()
    
    # 测试单个类别查询
    print("\n测试单个类别查询:")
    result = checker.search_trademark("monica", "20")
    print(f"查询结果: {result}")
    
    if result["success"]:
        print(f"找到 {result['data']['total']} 个相关商标:")
        for brand in result['data']['hits']:
            print(f"  - {brand}")
    else:
        print(f"查询失败: {result['error']}")

if __name__ == "__main__":
    main() 