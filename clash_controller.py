import requests
import time
import logging
from typing import List, Dict
import random

class ClashController:
    def __init__(self, api_url: str = "http://127.0.0.1:9097"):
        """初始化Clash控制器
        Args:
            api_url: Clash API地址
        """
        self.api_url = api_url
        self.setup_logging()
        # 使用更安全的测试URL
        self.test_urls = [
            "https://www.google.com",  # 主要测试URL
            "https://www.cloudflare.com",  # 备用测试URL
            "https://www.microsoft.com"  # 备用测试URL
        ]
        
    def setup_logging(self):
        """配置日志输出"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger("Clash Controller")
    
    def get_proxies(self) -> Dict:
        """获取所有代理信息"""
        try:
            response = requests.get(f"{self.api_url}/proxies")
            return response.json()
        except Exception as e:
            self.logger.error(f"获取代理列表失败: {str(e)}")
            return {}
    
    def get_proxy_group(self, group_name: str) -> Dict:
        """获取指定代理组的信息"""
        try:
            response = requests.get(f"{self.api_url}/proxies/{group_name}")
            return response.json()
        except Exception as e:
            self.logger.error(f"获取代理组 {group_name} 失败: {str(e)}")
            return {}
    
    def test_proxy_delay(self, proxy_name: str) -> int:
        """测试代理延迟
        Args:
            proxy_name: 代理名称
        Returns:
            int: 延迟时间（毫秒），-1表示测试失败
        """
        try:
            # 随机选择一个测试URL，避免对单一网站发送过多请求
            test_url = random.choice(self.test_urls)
            response = requests.get(f"{self.api_url}/proxies/{proxy_name}/delay", 
                                  params={"url": test_url, "timeout": 5000})
            if response.status_code == 200:
                return response.json().get("delay", -1)
            return -1
        except:
            return -1

    def probe_proxies(self, proxies: List[str]) -> Dict[str, int]:
        """探测一组代理的延迟
        Args:
            proxies: 代理列表
        Returns:
            Dict[str, int]: 代理名称到延迟的映射，-1表示测试失败
        """
        self.logger.info(f"开始探测 {len(proxies)} 个节点的延迟...")
        delays = {}
        for proxy in proxies:
            delay = self.test_proxy_delay(proxy)
            delays[proxy] = delay
            if delay != -1:
                self.logger.info(f"节点 {proxy} 延迟: {delay}ms")
            else:
                self.logger.warning(f"节点 {proxy} 延迟测试失败")
            time.sleep(0.5)  # 短暂等待，避免请求过快
        return delays
    
    def get_available_proxies(self, group_name: str) -> List[str]:
        """获取指定组中可用的代理列表"""
        group_info = self.get_proxy_group(group_name)
        if not group_info:
            return []
        
        all_proxies = group_info.get("all", [])
        # 过滤掉特殊节点和自动选择节点
        filtered_proxies = [
            proxy for proxy in all_proxies 
            if not proxy in ["DIRECT", "REJECT", "GLOBAL", "AUTO", "direct", "reject"] 
            and not proxy.startswith(("🚀", "♻️", "🔯", "🔄"))  # 过滤掉自动选择相关的节点
            and not "自动" in proxy
            and not "故障" in proxy
            and not "负载" in proxy
            and not "🇭🇰 香港 04" in proxy  # 排除错误节点
            and not "Cherry" in proxy# 排除Cherry Network节点
        ]
        
        self.logger.info(f"找到 {len(filtered_proxies)} 个可用节点")
        return filtered_proxies
    
    def switch_proxy(self, group_name: str, proxy_name: str) -> bool:
        """切换指定组的代理
        Args:
            group_name: 代理组名称
            proxy_name: 要切换到的代理名称
        Returns:
            bool: 是否切换成功
        """
        try:
            response = requests.put(
                f"{self.api_url}/proxies/{group_name}",
                json={"name": proxy_name}
            )
            if response.status_code == 204:
                self.logger.info(f"成功切换到节点: {proxy_name}")
                return True
            else:
                self.logger.error(f"切换节点失败: {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"切换节点时出错: {str(e)}")
            return False
    
    def auto_switch(self, group_name: str = "🎮 Game", interval: int = 20):
        """自动切换节点
        Args:
            group_name: 代理组名称
            interval: 切换间隔（秒）
        """
        self.logger.info(f"开始自动切换节点 (组: {group_name}, 间隔: {interval}秒)")
        self.logger.info(f"目标网站: {self.test_urls}")
        
        current_proxy = None  # 记录当前使用的节点
        
        while True:
            try:
                # 获取可用节点列表
                proxies = self.get_available_proxies(group_name)
                if not proxies:
                    self.logger.error(f"组 {group_name} 中没有可用节点")
                    time.sleep(interval)
                    continue
                
                # 如果当前节点不在列表中，从第一个开始
                if current_proxy not in proxies:
                    current_index = 0
                else:
                    current_index = proxies.index(current_proxy)
                    # 移动到下一个节点
                    current_index = (current_index + 1) % len(proxies)
                
                # 尝试所有节点，直到找到一个可用的
                nodes_tried = 0
                while nodes_tried < len(proxies):
                    candidate_proxy = proxies[current_index]
                    
                    # 测试节点可用性
                    self.logger.info(f"测试节点 {candidate_proxy} 的可用性...")
                    delay = self.test_proxy_delay(candidate_proxy)
                    
                    if delay != -1:
                        self.logger.info(f"节点 {candidate_proxy} 可用 (延迟: {delay}ms)")
                        if self.switch_proxy(group_name, candidate_proxy):
                            current_proxy = candidate_proxy
                            self.logger.info(f"成功切换到节点: {candidate_proxy} (延迟: {delay}ms)")
                            self.logger.info(f"{interval}秒后进行下一次切换...")
                            time.sleep(interval)
                            break
                    else:
                        self.logger.warning(f"节点 {candidate_proxy} 不可用，尝试下一个节点")
                        time.sleep(0.5)  # 短暂等待，避免请求过快
                    
                    # 移动到下一个节点
                    current_index = (current_index + 1) % len(proxies)
                    nodes_tried += 1
                
                if nodes_tried >= len(proxies):
                    self.logger.error("所有节点都不可用，等待3秒后重试...")
                    time.sleep(3)
                
            except KeyboardInterrupt:
                self.logger.info("收到停止信号，程序结束")
                break
            except Exception as e:
                self.logger.error(f"发生错误: {str(e)}")
                self.logger.info("3秒后重试...")
                time.sleep(3)

def main():
    """主函数"""
    controller = ClashController()
    
    # 打印当前可用的代理组
    proxies = controller.get_proxies()
    if proxies:
        print("\n可用的代理组:")
        for name, info in proxies.get("proxies", {}).items():
            if info.get("type") == "Selector":
                print(f"- {name}")
    
    # 启动自动切换
    print("\n按 Ctrl+C 停止切换")
    controller.auto_switch(group_name="🎮 Game", interval=20)  # 使用20秒间隔

if __name__ == "__main__":
    main() 