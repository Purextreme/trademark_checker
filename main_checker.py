import logging
from typing import List, Dict, Any, Union
from tmdn_name_checker import TMDNNameChecker
from uk_checker_process import UKCheckerProcess
from us_checker import USChecker
from local_db_checker import LocalDBChecker
import time
import os
from config import NICE_CLASS_MAP, QUERY_STATUS

class TrademarkChecker:
    def __init__(self):
        self.setup_logging()
        self.tmdn_checker = TMDNNameChecker()
        self.us_checker = USChecker()
        self.uk_checker = UKCheckerProcess()  # 使用新的进程隔离的UK查询器
        self.local_checker = LocalDBChecker()
        self.last_tmdn_query_time = 0
        self.last_query_time = 0  # 记录上一次查询的时间
        self.min_query_interval = 5  # 最小查询间隔（秒）
        self.nice_class_map = NICE_CLASS_MAP

    def __del__(self):
        """确保在对象销毁时正确关闭UK查询进程"""
        if hasattr(self, 'uk_checker'):
            self.uk_checker.stop_process()

    def setup_logging(self):
        """配置日志输出格式"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _wait_for_rate_limit(self):
        """确保查询间隔至少为指定秒数"""
        current_time = time.time()
        time_since_last_query = current_time - self.last_query_time
        if time_since_last_query < self.min_query_interval:
            wait_time = self.min_query_interval - time_since_last_query
            self.logger.info(f"等待 {wait_time:.1f} 秒以满足最小查询间隔...")
            time.sleep(wait_time)
        self.last_query_time = time.time()

    def _check_exact_match(self, query_name: str, brand_names: List[str]) -> List[str]:
        """检查是否存在完全匹配
        按照rules.md中的规则：
        - 不区分大小写
        - 忽略首尾空格
        - 只要包含这个单词就算匹配（作为独立单词）
        - 不匹配单词的一部分（例如，查询"cat"不会匹配"catch"）
        
        Args:
            query_name: 要查询的商标名称
            brand_names: 要检查的品牌名称列表
        Returns:
            匹配的品牌名称列表
        """
        query_name = query_name.lower().strip()
        exact_matches = []
        
        for brand in brand_names:
            # 将品牌名称分割成单词并转换为小写
            brand_words = [word.lower().strip() for word in brand.split()]
            
            # 检查查询名称是否作为独立单词出现
            # 使用完全匹配确保不会匹配单词的一部分
            if any(word == query_name for word in brand_words):
                exact_matches.append(brand)
        
        return exact_matches

    def _format_nice_class_display(self, nice_classes: Union[str, List[str]]) -> str:
        """格式化类别显示文本"""
        if isinstance(nice_classes, str):
            return f"{nice_classes} - {self.nice_class_map.get(nice_classes, '')}"
        
        display_texts = []
        for nice_class in nice_classes:
            display_texts.append(f"{nice_class} - {self.nice_class_map.get(nice_class, '')}")
        return "，".join(display_texts)

    def check_trademark(self, query_name: str, nice_classes: Union[str, List[str]], regions: Union[str, List[str]]) -> Dict[str, Any]:
        """检查商标在各个系统中的状态
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别（可以是单个类别字符串或类别列表）
            regions: 查询区域（可以是单个区域字符串或区域列表）
        """
        # 等待满足最小查询间隔
        self._wait_for_rate_limit()

        if isinstance(regions, str):
            regions = [regions]
        if isinstance(nice_classes, str):
            nice_classes = [nice_classes]

        nice_class_display = self._format_nice_class_display(nice_classes)
        logging.info(f"\n开始检查商标: {query_name} (类别: {nice_class_display}, 区域: {', '.join(regions)})")

        try:
            # 1. 首先检查本地数据库
            local_result = self.local_checker.search_trademark(query_name, nice_classes, regions[0])
            if local_result["status"] == "error":
                return local_result
            
            if local_result["in_local_db"]:
                local_result["status_message"] = QUERY_STATUS["LOCAL_MATCH"]
                if "matched_classes" in local_result:
                    local_result["status_message"] += f" (类别: {', '.join(local_result['matched_classes'])})"
                return local_result

            # 2. 确定查询顺序和范围（根据todo.md要求）
            search_steps = []
            
            # 2.1 总是先查询TMDN（支持多区域）
            search_steps.append({
                "source": "TMDN",
                "checker": self.tmdn_checker,
                "regions": regions.copy()
            })
            
            # 2.2 然后查询美国（如果选中）
            if "美国" in regions:
                search_steps.append({
                    "source": "US",
                    "checker": self.us_checker,
                    "regions": ["美国"]
                })
            
            # 2.3 最后查询英国（如果选中）
            if "英国" in regions:
                search_steps.append({
                    "source": "UK",
                    "checker": self.uk_checker,
                    "regions": ["英国"]
                })
            
            # 3. 按顺序执行查询（TMDN -> US -> UK）
            searched_sources = []
            for step in search_steps:
                source_name = step["source"]
                checker = step["checker"]
                target_regions = step["regions"]
                
                logging.info(f"正在查询 {source_name} (区域: {', '.join(target_regions)})...")
                searched_sources.append(source_name)
                
                # 查询，如果失败则重试一次
                for attempt in range(2):  # 最多尝试2次
                    try:
                        # 统一查询接口
                        if source_name == "TMDN":
                            result = checker.search_trademark(query_name, nice_classes, target_regions)
                        else:
                            result = checker.search_trademark(query_name, nice_classes)
                        
                        # 处理查询结果
                        if not result["success"]:
                            error_msg = result.get('error', '未知错误')
                            if attempt == 0:  # 第一次失败
                                logging.error(f"{source_name}查询出错: {error_msg}，5秒后重试...")
                                time.sleep(5)  # 等待5秒后重试
                                continue
                            else:  # 第二次失败
                                logging.error(f"{source_name}第二次查询仍然出错: {error_msg}")
                                return {
                                    "query_name": query_name,
                                    "status": "error",
                                    "error_message": f"{source_name}查询失败: {error_msg}",
                                    "brands": [],
                                    "total_found": 0,
                                    "has_exact_match": False,
                                    "exact_matches": [],
                                    "search_source": searched_sources,
                                    "search_params": {
                                        "region": ", ".join(target_regions),
                                        "nice_class": nice_class_display,
                                        "status": "查询出错"
                                    }
                                }
                        
                        # 查询成功，显示结果
                        logging.info(f"\n{source_name}查询结果:")
                        
                        if result["data"] == "NO_RESULTS":
                            logging.info("未找到任何商标")
                            break  # 退出重试循环，继续下一个查询源
                        
                        # 显示找到的商标
                        trademarks = result["data"]
                        logging.info(f"找到 {len(trademarks)} 个商标:")
                        for trademark in trademarks:
                            logging.info(f"  - {trademark}")
                        logging.info("")  # 空行分隔
                        
                        # 进行匹配检查
                        exact_matches = self._check_exact_match(query_name, trademarks)
                        if exact_matches:
                            logging.info(f"{source_name}匹配结果:")
                            logging.info(f"找到 {len(exact_matches)} 个匹配:")
                            for match in exact_matches:
                                logging.info(f"  - {match}")
                            logging.info("")  # 空行分隔
                            
                            return {
                                "query_name": query_name,
                                "status": "success",
                                "status_message": QUERY_STATUS["EXACT_MATCH"],
                                "brands": trademarks,
                                "total_found": len(trademarks),
                                "has_exact_match": True,
                                "exact_matches": exact_matches,
                                "search_source": [source_name],
                                "search_params": {
                                    "region": ", ".join(target_regions),
                                    "nice_class": nice_class_display,
                                    "status": "已注册或待审"
                                }
                            }
                        else:
                            logging.info(f"{source_name}匹配结果: 未找到匹配")
                            logging.info("")  # 空行分隔
                            break  # 退出重试循环，继续下一个查询源
                            
                    except Exception as e:
                        error_msg = str(e)
                        if attempt == 0:  # 第一次失败
                            logging.error(f"{source_name}查询出错: {error_msg}，5秒后重试...")
                            time.sleep(5)  # 等待5秒后重试
                            continue
                        else:  # 第二次失败
                            return {
                                "query_name": query_name,
                                "status": "error",
                                "error_message": f"{source_name}查询失败: {error_msg}",
                                "brands": [],
                                "total_found": 0,
                                "has_exact_match": False,
                                "exact_matches": [],
                                "search_source": searched_sources,
                                "search_params": {
                                    "region": ", ".join(target_regions),
                                    "nice_class": nice_class_display,
                                    "status": "查询出错"
                                }
                            }

            logging.info(f"当前查询顺序：{[step['source'] for step in search_steps]}")
            logging.info("所有系统查询完成，未找到匹配")

            # 所有系统都查询完成，未找到匹配
            return {
                "query_name": query_name,
                "status": "success",
                "status_message": QUERY_STATUS["NO_MATCH"],
                "brands": [],
                "total_found": 0,
                "has_exact_match": False,
                "exact_matches": [],
                "search_source": searched_sources,
                "search_params": {
                    "region": ", ".join(regions),
                    "nice_class": nice_class_display,
                    "status": "已注册或待审"
                }
            }

        except Exception as e:
            error_msg = f"查询过程中出错: {str(e)}"
            logging.error(error_msg)
            return {
                "query_name": query_name,
                "status": "error",
                "error_message": error_msg,
                "brands": [],
                "total_found": 0,
                "has_exact_match": False,
                "exact_matches": [],
                "search_source": [],
                "search_params": {
                    "region": ", ".join(regions),
                    "nice_class": nice_class_display,
                    "status": "查询出错"
                }
            }

def main():
    """主函数，用于测试"""
    checker = TrademarkChecker()
    
    # 测试多个区域和类别
    print("\n测试多个区域和类别查询:")
    result = checker.check_trademark("wangguan", ["14", "20"], ["美国", "欧盟", "英国"])
    print(f"找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")

if __name__ == "__main__":
    main()