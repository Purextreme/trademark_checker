import sys
from playwright.sync_api import sync_playwright, TimeoutError, expect
import logging
from typing import Dict, Any, List, Union, Optional
from bs4 import BeautifulSoup
from config import UK_CONFIG

class UKChecker:
    def __init__(self):
        self.setup_logging()
        self.config = UK_CONFIG
        self._ensure_browser_installed()
        self.playwright = None
        self.browser = None

    def _ensure_browser_installed(self):
        """确保Playwright浏览器已安装"""
        try:
            import subprocess
            import sys
            
            self.logger.info("检查Playwright浏览器安装状态...")
            result = subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.logger.info("Playwright浏览器已正确安装")
            else:
                self.logger.warning(f"Playwright浏览器安装可能有问题: {result.stderr}")
        except Exception as e:
            self.logger.error(f"检查Playwright浏览器时出错: {str(e)}")

    def setup_logging(self):
        """配置日志输出格式"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def search_trademark(self, query_name: str, nice_classes: Union[str, List[str]]) -> Dict[str, Any]:
        """搜索英国商标（独立运行版本）"""
        try:
            # 每次查询都创建新的Playwright实例
            with sync_playwright() as playwright:
                self.playwright = playwright
                self.browser = playwright.chromium.launch(
                    headless=True,
                    args=['--disable-gpu', '--no-sandbox']
                )
                
                context = self.browser.new_context(
                    viewport=self.config["viewport"],
                    user_agent=self.config["user_agent"]
                )
                page = context.new_page()
                
                # 设置超时时间
                page.set_default_timeout(60000)
                
                # 访问搜索页面
                self.logger.info("访问搜索页面...")
                page.goto(self.config["base_url"])
                page.wait_for_load_state('domcontentloaded')
                page.wait_for_load_state('networkidle')
                
                # 输入搜索词
                self.logger.info("输入搜索词...")
                search_phrase = page.wait_for_selector('input[name="wordSearchPhrase"]', state='visible')
                search_phrase.fill(query_name)
                
                # 设置商标类别
                self.logger.info("设置商标类别...")
                class_input = page.wait_for_selector('input[value="Click here to select a class..."]', state='visible')
                class_input.click()
                
                # 选择所有指定的类别
                for nice_class in nice_classes:
                    class_config = self.config["nice_classes"].get(nice_class)
                    if class_config:
                        # 等待类别选项出现并点击
                        class_option = page.wait_for_selector(f'li[data-option-array-index="{class_config["index"]}"]', state='visible')
                        class_option.click()
                        # 等待一下以确保选择已被接受
                        page.wait_for_timeout(500)
                        # 重新点击输入框以准备选择下一个类别（如果有的话）
                        if nice_class != nice_classes[-1]:  # 如果不是最后一个类别
                            page.wait_for_selector('input[value="Click here to select a class..."]', state='visible').click()
                
                # 点击页面空白处以关闭类别选择框
                page.click('body')
                
                # 设置每页显示结果数
                self.logger.info("设置每页显示结果数...")
                page_size = page.wait_for_selector('select[name="pageSize"]', state='visible')
                page_size.select_option(self.config["page_size"])
                
                # 设置商标状态
                self.logger.info("设置商标状态...")
                legal_status = page.wait_for_selector('select[name="legalStatus"]', state='visible')
                legal_status.select_option(self.config["legal_status"])
                
                # 提交搜索
                self.logger.info("提交搜索请求...")
                submit_button = page.wait_for_selector('button#button[type="submit"]', state='visible')
                
                # 点击提交按钮并等待导航开始
                submit_button.click()
                
                # 等待加载指示器出现
                self.logger.info("等待搜索开始...")
                try:
                    page.wait_for_selector('.loading-box', state='visible', timeout=5000)
                    self.logger.info("搜索正在进行中...")
                except TimeoutError:
                    pass  # 有些情况下可能没有加载指示器
                
                # 等待页面导航完成
                self.logger.info("等待页面加载...")
                page.wait_for_load_state('domcontentloaded', timeout=30000)
                
                # 等待网络请求完成
                self.logger.info("等待数据加载...")
                page.wait_for_load_state('networkidle', timeout=30000)
                
                # 检查是否有"无结果"提示
                self.logger.info("检查查询结果...")
                error_summary = page.query_selector('div.error-summary')
                if error_summary:
                    error_text = error_summary.inner_text()
                    if "No trade marks matching your search criteria were found" in error_text:
                        self.logger.info("未找到匹配的商标")
                        return {
                            "success": True,
                            "message": "未找到匹配的商标",
                            "data": {
                                "total": 0,
                                "hits": []
                            }
                        }
                
                # 等待结果加载并解析
                self.logger.info("等待结果显示...")
                try:
                    page.wait_for_selector('div.search-results', state='visible', timeout=30000)
                except TimeoutError:
                    # 再次检查是否有"无结果"提示
                    error_summary = page.query_selector('div.error-summary')
                    if error_summary and "No trade marks matching your search criteria were found" in error_summary.inner_text():
                        return {
                            "success": True,
                            "message": "未找到匹配的商标",
                            "data": {
                                "total": 0,
                                "hits": []
                            }
                        }
                    else:
                        # 如果既没有结果也没有无结果提示，则确实是超时错误
                        error_msg = "查询超时：服务器响应时间过长"
                        self.logger.error(error_msg)
                        return {
                            "success": False,
                            "message": error_msg,
                            "data": {
                                "total": 0,
                                "hits": []
                            }
                        }
                
                self.logger.info("解析查询结果...")
                soup = BeautifulSoup(page.content(), 'html.parser')
                
                # 提取商标名称
                trademarks = []
                for result in soup.find_all('div', class_='search-results'):
                    mark_text = result.find('span', string='Mark text:')
                    if mark_text and (mark_name := mark_text.find_next('span', class_='data')):
                        brand_name = mark_name.text.strip()
                        if brand_name:  # 确保不是空字符串
                            trademarks.append(brand_name)
                
                self.logger.info(f"找到 {len(trademarks)} 个商标")
                
                # 关闭上下文
                context.close()
                return {
                    "success": True,
                    "message": f"找到 {len(trademarks)} 个结果",
                    "data": {
                        "total": len(trademarks),
                        "hits": trademarks
                    }
                }
                
        except Exception as e:
            error_msg = f"系统错误：{str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "data": {
                    "total": 0,
                    "hits": []
                }
            }

def main():
    """主函数，用于测试"""
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(level=logging.DEBUG)
    
    checker = UKChecker()
    
    # 测试单个类别查询
    print("\n测试单个类别查询:")
    result = checker.search_trademark("monica", "20")
    print(f"查询结果: {result}")
    
    if result["success"]:
        print(f"找到 {result['data']['total']} 个相关商标:")
        for brand in result['data']['hits']:
            print(f"  - {brand}")
    else:
        print(f"查询失败: {result['message']}")
    
    # 测试多个类别查询
    print("\n测试多个类别查询:")
    result = checker.search_trademark("monica", ["14", "20"])
    print(f"查询结果: {result}")
    
    if result["success"]:
        print(f"找到 {result['data']['total']} 个相关商标:")
        for brand in result['data']['hits']:
            print(f"  - {brand}")
    else:
        print(f"查询失败: {result['message']}")

if __name__ == "__main__":
    main() 