import requests
import logging
from typing import Dict, Any

class TMDNNameChecker:
    def __init__(self):
        self.setup_logging()
        self.base_url = "https://www.tmdn.org/tmview/api/search/results"
        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
            'Origin': 'https://www.tmdn.org',
            'Referer': 'https://www.tmdn.org/tmview/',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
        }
        self.nice_class_map = {
            "14": "贵重金属及合金等",
            "20": "家具镜子相框等",
            "21": "家庭或厨房用具及容器等"
        }

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def search_trademark(self, query_name: str, nice_class: str = "20") -> Dict[str, Any]:
        """搜索商标
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
        """
        try:
            logging.info(f"开始查询TMDN商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')})")
            
            payload = {
                "page": "1",
                "pageSize": "30",
                "criteria": "C",
                "basicSearch": query_name,
                "fOffices": ["US"],
                "fNiceClass": [nice_class],
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
                    "status": "error",
                    "error_message": error_msg,
                    "brands": [],
                    "total_found": 0,
                    "search_params": {
                        "region": "US",
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
                "status": "success",
                "brands": brands,
                "total_found": total_results,
                "search_params": {
                    "region": "US",
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "已注册或待审"
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"TMDN查询出错: {error_msg}")
            return {
                "status": "error",
                "error_message": error_msg,
                "brands": [],
                "total_found": 0,
                "search_params": {
                    "region": "US",
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "已注册或待审"
                }
            }

def main():
    """主函数，用于测试"""
    checker = TMDNNameChecker()
    result = checker.search_trademark("monica", "14")
    
    print(f"\n找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")
    else:
        print("未找到任何品牌")
    print("\n查询参数:", result['search_params'])

if __name__ == "__main__":
    main() 