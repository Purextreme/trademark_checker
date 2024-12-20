from playwright.sync_api import sync_playwright
import re
import logging
from typing import Dict, Any
import sys

class WIPOChecker:
    def __init__(self):
        self.setup_logging()
        self.nice_class_map = {
            "14": "贵重金属及合金等",
            "20": "家具镜子相框等",
            "21": "家庭或厨房用具及容器等"
        }
        
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

    def search_trademark(self, query_name: str, nice_class: str = "20") -> Dict[str, Any]:
        """查询单个商标名称
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
        """
        logging.info(f"开始查询WIPO商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')})")
        
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={'width': 1920, 'height': 4096})
                page = context.new_page()
                
                url = (f"https://branddb.wipo.int/en/similarname/results?sort=score%20desc&rows=15"
                      f"&asStructure=%7B%22_id%22:%227dea%22,%22boolean%22:%22AND%22,%22bricks%22:"
                      f"%5B%7B%22_id%22:%227deb%22,%22key%22:%22brandName%22,%22value%22:%22{query_name}%22,"
                      f"%22strategy%22:%22Simple%22%7D%5D%7D"
                      f"&fcdesignation=US&fcniceClass={nice_class}"
                      f"&fcstatus=Registered&fcstatus=Pending")
                
                # 导航到页面
                page.goto(url, wait_until='networkidle')
                
                # 等待结果计数元素出现
                results_count = page.locator('[data-test-id="resultsCount"]')
                results_count.wait_for(state='visible')
                
                # 等待加载完成
                page.wait_for_function("""
                    () => {
                        const el = document.querySelector('[data-test-id="resultsCount"]');
                        return el && el.textContent && !el.textContent.includes('Loading...');
                    }
                """)
                
                count_text = results_count.text_content()
                total_results = self._extract_total_results(count_text)
                
                if "No results found" not in count_text:
                    # 获取品牌名称列表
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
                        "search_params": {
                            "region": "US",
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
                        "search_params": {
                            "region": "US",
                            "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                            "status": "已注册或待审"
                        }
                    }
                
        except Exception as e:
            logging.error(f"WIPO查询出错: {str(e)}")
            return {
                "status": "error",
                "error_message": str(e),
                "brands": [],
                "total_found": 0,
                "search_params": {
                    "region": "US",
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "已注册或待审"
                }
            }

    def _extract_total_results(self, text: str) -> int:
        """从结果状态文本中提取总结果数"""
        match = re.search(r'of (\d+) results', text)
        if match:
            return int(match.group(1))
        return 0