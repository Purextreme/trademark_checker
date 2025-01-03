from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import re
import logging
from typing import Dict, Any
import sys
import time
from config import WIPO_CONFIG, NICE_CLASS_MAP, QUERY_PARAMS

class WIPOChecker:
    def __init__(self):
        self.setup_logging()
        self.nice_class_map = NICE_CLASS_MAP
        self.max_retries = WIPO_CONFIG["max_retries"]
        self.retry_delay = WIPO_CONFIG["retry_delay"]
        self.base_url = WIPO_CONFIG["base_url"]
        
    def setup_logging(self):
        """配置日志输出格式"""
        root = logging.getLogger()
        if root.handlers:
            for handler in root.handlers:
                root.removeHandler(handler)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s', '%Y-%m-%d %H:%M:%S'))
        root.addHandler(handler)
        root.setLevel(logging.INFO)

    def _try_get_page_content(self, page, url: str, max_retries: int = 3) -> bool:
        """尝试获取页面内容，带重试机制"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logging.info(f"第 {attempt + 1} 次重试...")
                    time.sleep(self.retry_delay)
                
                response = page.goto(url, wait_until='networkidle')
                if not response:
                    logging.error("页面加载失败，无响应")
                    continue
                    
                logging.info(f"页面响应状态: {response.status}")
                if response.status != 200:
                    logging.error(f"页面返回错误状态码: {response.status}")
                    continue
                
                # 等待页面基本元素加载
                page.wait_for_selector('body', timeout=10000)
                
                # 检查页面内容
                content = page.content()
                if len(content) < 1000:
                    logging.warning(f"页面内容可能不完整，长度: {len(content)}")
                    continue
                
                # 等待结果计数元素出现
                results_count = page.locator('[data-test-id="resultsCount"]')
                results_count.wait_for(state='visible', timeout=15000)
                
                # 获取结果文本
                count_text = results_count.text_content()
                if not count_text:
                    logging.warning("结果计数元素为空")
                    continue
                    
                if "No results found" in count_text:
                    logging.info("确认无搜索结果")
                    return True
                    
                if "Displaying" in count_text and "results" in count_text:
                    # 找到结果后，确保等待品牌名称加载完成
                    time.sleep(1)  # 给一个短暂的缓冲时间
                    try:
                        # 等待第一个品牌名称元素出现即可
                        page.wait_for_selector('.brandName', timeout=5000)
                        logging.info("搜索结果和品牌名称已加载完成")
                        return True
                    except PlaywrightTimeout:
                        logging.error("等待品牌名称元素超时")
                        continue
                
                logging.warning("页面内容格式不符合预期")
                return False
                
            except Exception as e:
                logging.error(f"加载失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    raise e
        
        return False

    def _build_wipo_url(self, query_name: str, nice_class: str, region: str) -> str:
        """构建WIPO查询URL"""
        # 获取区域配置
        region_config = WIPO_CONFIG["regions"].get(region, WIPO_CONFIG["regions"]["美国"])
        designations = region_config["designations"]
        
        # 构建designation参数
        designation_params = "&".join([f"fcdesignation={d}" for d in designations])
        
        url = (f"{self.base_url}?sort=score%20desc"
               f"&rows={QUERY_PARAMS['wipo_display_limit']}"
               f"&asStructure=%7B%22_id%22:%227dea%22,%22boolean%22:%22AND%22,%22bricks%22:"
               f"%5B%7B%22_id%22:%227deb%22,%22key%22:%22brandName%22,%22value%22:%22{query_name}%22,"
               f"%22strategy%22:%22Simple%22%7D%5D%7D"
               f"&{designation_params}"
               f"&fcniceClass={nice_class}"
               f"&fcstatus=Registered&fcstatus=Pending")
        
        return url

    def search_trademark(self, query_name: str, nice_class: str = "20", region: str = "美国") -> Dict[str, Any]:
        """查询单个商标名称"""
        logging.info(f"开始查询WIPO商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')}, 区域: {region})")
        
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logging.info(f"整体查询第 {attempt + 1} 次重试...")
                    time.sleep(self.retry_delay)
                
                with sync_playwright() as playwright:
                    logging.info("正在启动浏览器...")
                    browser = playwright.chromium.launch(headless=True)
                    context = browser.new_context(
                        viewport={'width': 1920, 'height': 4096},
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                    )
                    page = context.new_page()
                    
                    url = self._build_wipo_url(query_name, nice_class, region)
                    logging.info(f"正在访问URL: {url}")
                    
                    if self._try_get_page_content(page, url):
                        results_count = page.locator('[data-test-id="resultsCount"]')
                        count_text = results_count.text_content()
                        logging.info(f"获取到结果文本: {count_text}")
                        
                        total_results = self._extract_total_results(count_text)
                        logging.info(f"解析到总结果数: {total_results}")
                        
                        if "No results found" not in count_text:
                            brand_elements = page.locator('.brandName')
                            brand_names = []
                            count = brand_elements.count()
                            
                            for i in range(count):
                                text = brand_elements.nth(i).text_content().strip()
                                if text:
                                    brand_names.append(text)
                            
                            brand_names.sort()
                            logging.info(f"WIPO查询完成: {query_name}, 找到 {len(brand_names)} 个结果")
                            
                            return {
                                "status": "success",
                                "brands": brand_names,
                                "total_found": total_results,
                                "query_name": query_name,
                                "has_exact_match": False,
                                "exact_matches": [],
                                "search_source": ["WIPO"],
                                "search_params": {
                                    "region": region,
                                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                                    "status": "已注册或待审"
                                }
                            }
                        else:
                            logging.info(f"WIPO查询完成: {query_name}, 未找到结果")
                            return {
                                "status": "success",
                                "brands": [],
                                "total_found": 0,
                                "query_name": query_name,
                                "has_exact_match": False,
                                "exact_matches": [],
                                "search_source": ["WIPO"],
                                "search_params": {
                                    "region": region,
                                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                                    "status": "已注册或待审"
                                }
                            }
                    
            except Exception as e:
                logging.error(f"查询过程中出错 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                if attempt == self.max_retries - 1:
                    return {
                        "status": "error",
                        "error_message": str(e),
                        "brands": [],
                        "total_found": 0,
                        "query_name": query_name,
                        "has_exact_match": False,
                        "exact_matches": [],
                        "search_source": ["WIPO"],
                        "search_params": {
                            "region": region,
                            "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                            "status": "已注册或待审"
                        }
                    }

    def _extract_total_results(self, text: str) -> int:
        """从结果状态文中提取总结果数"""
        match = re.search(r'of (\d+) results', text)
        if match:
            return int(match.group(1))
        return 0

def main():
    """主函数，用于测试"""
    checker = WIPOChecker()
    
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