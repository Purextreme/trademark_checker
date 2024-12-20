from playwright.sync_api import sync_playwright
import re
import logging
from typing import Dict, List, Any
import time
import sys
from threading import Lock

# 全局锁，用于确保同一时间只有一个查询在执行
query_lock = Lock()

class NameChecker:
    def __init__(self):
        # 配置日志输出到控制台
        self.setup_logging()
        logging.info("初始化 Playwright...")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(viewport={'width': 1920, 'height': 4096})
        self.page = self.context.new_page()
        logging.info("浏览器初始化完成")
        
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
        
    def cleanup(self):
        """清理资源"""
        try:
            if hasattr(self, 'page') and self.page:
                self.page.close()
            if hasattr(self, 'context') and self.context:
                self.context.close()
            if hasattr(self, 'browser') and self.browser:
                self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                self.playwright.stop()
            logging.info("资源已清理完毕")
        except Exception as e:
            logging.error(f"清理资源时出错: {str(e)}")

    def extract_total_results(self, text: str) -> int:
        """从结果状态文本中提取总结果数"""
        match = re.search(r'of (\d+) results', text)
        if match:
            return int(match.group(1))
        return 0

    @staticmethod
    def check_names(query_names: list[str]) -> list[Dict[str, Any]]:
        """检查多个商标名称（静态方法）"""
        with query_lock:  # 使用锁确保同一时间只有一个查询在执行
            try:
                # 创建新的实例
                checker = NameChecker()
                results = []
                
                # 执行查询
                for name in query_names:
                    try:
                        result = checker._check_name_internal(name)
                        result["query_name"] = name
                        results.append(result)
                        time.sleep(1)  # 查询间隔
                    except Exception as e:
                        logging.error(f"查询 {name} 时出错: {str(e)}")
                        results.append({
                            "query_name": name,
                            "status": "error",
                            "error_message": str(e),
                            "brands": [],
                            "total_found": 0,
                            "total_displayed": 0,
                            "has_exact_match": False,
                            "exact_matches": []
                        })
                
                return results
            finally:
                # 确保资源被清理
                checker.cleanup()

    def _check_name_internal(self, query_name: str) -> Dict[str, Any]:
        """内部商标名称检查实现"""
        logging.info(f"开始查询商标: {query_name}")
        url = f"https://branddb.wipo.int/en/similarname/results?sort=score%20desc&rows=15&asStructure=%7B%22_id%22:%227dea%22,%22boolean%22:%22AND%22,%22bricks%22:%5B%7B%22_id%22:%227deb%22,%22key%22:%22brandName%22,%22value%22:%22{query_name}%22,%22strategy%22:%22Simple%22%7D%5D%7D&fcdesignation=GB&fcdesignation=US&fcdesignation=DE&fcdesignation=EM&fcdesignation=ES&fcdesignation=FR&fcdesignation=IT&fcdesignation=CA&fcniceClass=20&fcstatus=Registered&fcstatus=Pending"
        
        try:
            # 导航到页面
            logging.info("正在加载查询页面...")
            self.page.goto(url, wait_until='networkidle')
            logging.info("页面加载完成，等待结果...")
            
            # 等待结果计数元素出现并且不再显示"Loading..."
            logging.info("等待结果计数元素出现...")
            results_count = self.page.locator('[data-test-id="resultsCount"]')
            results_count.wait_for(state='visible')
            logging.info("结果计数元素已出现")
            
            # 等待加载完成
            logging.info("等待结果加载完成...")
            self.page.wait_for_function("""
                () => {
                    const el = document.querySelector('[data-test-id="resultsCount"]');
                    return el && el.textContent && !el.textContent.includes('Loading...');
                }
            """)
            logging.info("结果加载完成")
            
            count_text = results_count.text_content()
            total_results = self.extract_total_results(count_text)
            logging.info(f"查询状态: {count_text}")
            
            if "No results found" not in count_text:
                # 使用 Playwright 的定位器获取所有品牌名称
                logging.info("开始获取品牌名称列表...")
                brand_elements = self.page.locator('.brandName')
                brand_names = []
                
                # 获取所有品牌名称
                count = brand_elements.count()
                logging.info(f"找到 {count} 个品牌名称元素")
                
                for i in range(count):
                    text = brand_elements.nth(i).text_content().strip()
                    if text:
                        brand_names.append(text)
                        logging.info(f"处理第 {i+1}/{count} 个品牌名称: {text}")
                
                brand_names.sort()
                
                # 检查完全匹配
                exact_matches = [name for name in brand_names 
                               if query_name.lower() in name.lower().split()]
                
                if exact_matches:
                    logging.info(f"发现 {len(exact_matches)} 个完全匹配的品牌")
                
                logging.info(f"商标查询完成: {query_name}, 找到 {len(brand_names)} 个结果")
                return {
                    "status": "success",
                    "status_message": count_text,
                    "brands": brand_names,
                    "total_found": total_results,
                    "total_displayed": len(brand_names),
                    "has_exact_match": len(exact_matches) > 0,
                    "exact_matches": exact_matches
                }
            else:
                logging.info(f"商标查询完成: {query_name}, 未找到结果")
                return {
                    "status": "success",
                    "status_message": count_text,
                    "brands": [],
                    "total_found": 0,
                    "total_displayed": 0,
                    "has_exact_match": False,
                    "exact_matches": []
                }
                
        except Exception as e:
            logging.error(f"查询时出错: {str(e)}")
            raise