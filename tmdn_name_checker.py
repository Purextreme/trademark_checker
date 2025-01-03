import requests
import logging
from typing import Dict, Any
from config import TMDN_CONFIG, NICE_CLASS_MAP, QUERY_PARAMS

class TMDNNameChecker:
    def __init__(self):
        self.setup_logging()
        self.base_url = TMDN_CONFIG["base_url"]
        self.headers = TMDN_CONFIG["headers"]
        self.nice_class_map = NICE_CLASS_MAP

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def search_trademark(self, query_name: str, nice_class: str = "20", region: str = "美国") -> Dict[str, Any]:
        """搜索商标
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
            region: 查询区域（美国/美国+欧洲）
        """
        try:
            logging.info(f"开始查询TMDN商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')}, 区域: {region})")
            
            # 获取区域配置
            region_config = TMDN_CONFIG["regions"].get(region, TMDN_CONFIG["regions"]["美国"])
            
            payload = {
                "page": "1",
                "pageSize": str(QUERY_PARAMS["page_size"]),
                "criteria": "C",
                "basicSearch": query_name,
                "offices": region_config["offices"],
                "territories": region_config["territories"],
                "niceClass": [nice_class],
                "fTMStatus": ["Registered", "Filed"],
                "fields": ["tmName"]  # 只获取商标名称
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}"
                logging.error(error_msg)
                return {
                    "query_name": query_name,  # 添加查询名称
                    "status": "error",
                    "error_message": error_msg,
                    "brands": [],
                    "total_found": 0,
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": ["TMDN"],
                    "search_params": {
                        "region": region,
                        "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                        "status": "已注册或待审"
                    }
                }
            
            data = response.json()
            total_results = data.get('totalResults', 0)
            
            # 只提取品牌名称
            brands = [tm.get('tmName', '') for tm in data.get('tradeMarks', [])]
            
            logging.info(f"TMDN查询完成，找到 {total_results} 个结果")
            
            return {
                "query_name": query_name,  # 添加查询名称
                "status": "success",
                "brands": brands,
                "total_found": total_results,
                "has_exact_match": False,  # 这个字段会在主查询模块中更新
                "exact_matches": [],  # 这个字段会在主查询模块中更新
                "search_source": ["TMDN"],
                "search_params": {
                    "region": region,
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "已注册或待审"
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"TMDN查询出错: {error_msg}")
            return {
                "query_name": query_name,  # 添加查询名称
                "status": "error",
                "error_message": error_msg,
                "brands": [],
                "total_found": 0,
                "has_exact_match": False,
                "exact_matches": [],
                "search_source": ["TMDN"],
                "search_params": {
                    "region": region,
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "已注册或待审"
                }
            }

def main():
    """主函数，用于测试"""
    checker = TMDNNameChecker()
    
    # 测试美国区域
    print("\n测试美国区域查询:")
    result = checker.search_trademark("monica", "14", "美国")
    print(f"找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")
    
    # 测试美国+欧洲区域
    print("\n测试美国+欧洲区域查询:")
    result = checker.search_trademark("monica", "14", "美国+欧洲")
    print(f"找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")

if __name__ == "__main__":
    main() 