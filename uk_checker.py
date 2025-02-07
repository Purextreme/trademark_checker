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
        """搜索英国商标"""
        try:
            with sync_playwright() as playwright:
                # 修改浏览器启动配置
                browser = playwright.chromium.launch(
                    headless=True,  # 重新启用无头模式
                    slow_mo=100,  # 保留操作延迟
                    args=['--start-maximized', '--disable-dev-shm-usage', '--no-sandbox']  # 添加额外的启动参数
                )
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080},  # 保留窗口大小设置
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'  # 添加用户代理
                )
                page = context.new_page()
                
                # 设置超时时间
                page.set_default_timeout(60000)  # 保持60秒超时
                
                # 访问搜索页面
                self.logger.info("访问搜索页面...")
                page.goto(self.config["base_url"])
                # 等待页面完全加载
                page.wait_for_load_state('load')
                page.wait_for_load_state('domcontentloaded')
                page.wait_for_load_state('networkidle')
                
                # 确保搜索框已经可用
                self.logger.info("等待搜索框加载...")
                page.wait_for_selector('input[name="wordSearchPhrase"]', state='visible', timeout=30000)
                page.wait_for_timeout(1000)  # 额外等待以确保元素完全可交互
                
                # 输入搜索词
                self.logger.info("输入搜索词...")
                search_phrase = page.locator('input[name="wordSearchPhrase"]')
                search_phrase.fill(query_name)
                
                # 设置商标类别
                self.logger.info("设置商标类别...")
                class_input = page.wait_for_selector('input[value="Click here to select a class..."]', state='visible')
                class_input.click()
                
                # 确保类别是列表形式
                if isinstance(nice_classes, str):
                    nice_classes = [nice_classes]
                
                # 选择所有指定的类别
                for nice_class in nice_classes:
                    class_config = self.config["nice_classes"].get(nice_class)
                    if class_config:
                        # 等待类别选项出现并点击
                        class_option = page.wait_for_selector(f'li[data-option-array-index="{class_config["index"]}"]', state='visible')
                        class_option.click()
                        # 等待一下以确保选择已被接受
                        page.wait_for_timeout(1000)  # 保持增加的等待时间
                        # 重新点击输入框以准备选择下一个类别（如果有的话）
                        if nice_class != nice_classes[-1]:  # 如果不是最后一个类别
                            page.wait_for_selector('input[value="Click here to select a class..."]', state='visible').click()
                            page.wait_for_timeout(500)  # 保持额外等待
                
                # 点击页面空白处以关闭类别选择框
                page.click('body')
                page.wait_for_timeout(500)  # 保持额外等待
                
                # 设置每页显示结果数
                self.logger.info("设置每页显示结果数...")
                page_size = page.wait_for_selector('select[name="pageSize"]', state='visible')
                page_size.select_option(self.config["page_size"])
                page.wait_for_timeout(500)  # 保持额外等待
                
                # 设置商标状态
                self.logger.info("设置商标状态...")
                legal_status = page.wait_for_selector('select[name="legalStatus"]', state='visible')
                legal_status.select_option(self.config["legal_status"])
                page.wait_for_timeout(500)  # 保持额外等待
                
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
                try:
                    # 等待页面加载完成
                    page.wait_for_load_state('domcontentloaded', timeout=30000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    # 先等待一小段时间，让页面稳定
                    page.wait_for_timeout(2000)
                    
                    # 检查是否有错误提示
                    error_summary = page.query_selector('div.error-summary')
                    if error_summary:
                        error_text = error_summary.inner_text()
                        if "No trade marks matching your search criteria were found" in error_text:
                            return {
                                "success": True,
                                "data": "NO_RESULTS"  # 使用特殊标记表示没有结果
                            }
                        else:
                            return {
                                "success": False,
                                "error": error_text
                            }
                    
                    # 检查页面内容
                    page_content = page.content()
                    soup = BeautifulSoup(page_content, 'html.parser')
                    
                    # 提取商标名称
                    trademarks = []
                    results_fields = soup.find_all('div', class_='results-field')
                    for field in results_fields:
                        title = field.find('span', class_='title')
                        if title and 'Mark text:' in title.text:
                            data = field.find('span', class_='data')
                            if data:
                                brand_name = data.text.strip()
                                trademarks.append(brand_name)
                    
                    if trademarks:
                        return {
                            "success": True,
                            "data": trademarks  # 直接返回商标列表
                        }
                    
                    return {
                        "success": True,
                        "data": "NO_RESULTS"
                    }
                    
                except TimeoutError:
                    return {
                        "success": False,
                        "error": "查询超时（30秒）"
                    }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
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
        print(f"找到 {len(result['data'])} 个相关商标:")
        for brand in result['data']:
            print(f"  - {brand}")
    else:
        print(f"查询失败: {result['error']}")
    
    # 测试多个类别查询
    print("\n测试多个类别查询:")
    result = checker.search_trademark("monica", ["14", "20"])
    print(f"查询结果: {result}")
    
    if result["success"]:
        print(f"找到 {len(result['data'])} 个相关商标:")
        for brand in result['data']:
            print(f"  - {brand}")
    else:
        print(f"查询失败: {result['error']}")

if __name__ == "__main__":
    main() 