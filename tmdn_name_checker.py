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

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def search_trademark(self, query_name: str) -> Dict[str, Any]:
        """搜索商标"""
        try:
            logging.info(f"开始查询商标: {query_name}")
            
            payload = {
                "page": "1",
                "pageSize": "30",
                "criteria": "C",
                "basicSearch": query_name,
                "fOffices": ["US"],
                "fNiceClass": ["20"],
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
                logging.error(f"API请求失败，状态码: {response.status_code}")
                return {
                    "status": "error",
                    "message": f"API请求失败，状态码: {response.status_code}",
                    "brands": [],
                    "total_found": 0
                }
            
            data = response.json()
            total_results = data.get('totalResults', 0)
            
            # 只提取品牌名称
            brands = [tm.get('tmName', '') for tm in data.get('tradeMarks', [])]
            
            logging.info(f"查询完成，找到 {total_results} 个结果")
            
            return {
                "status": "success",
                "brands": brands,
                "total_found": total_results
            }
            
        except Exception as e:
            logging.error(f"查询出错: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "brands": [],
                "total_found": 0
            }

def main():
    """主函数，用于测试"""
    checker = TMDNNameChecker()
    result = checker.search_trademark("monica")
    
    print(f"\n找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")
    else:
        print("未找到任何品牌")

if __name__ == "__main__":
    main() 