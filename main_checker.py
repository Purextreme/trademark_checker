import logging
from typing import List, Dict, Any, Tuple
from WIPO_name_checker import WIPOChecker
from tmdn_name_checker import TMDNNameChecker
from local_db_checker import LocalDBChecker
import time
import os
from config import NICE_CLASS_MAP, QUERY_STATUS

class TrademarkChecker:
    def __init__(self):
        self.setup_logging()
        self.wipo_checker = WIPOChecker()
        self.tmdn_checker = TMDNNameChecker()
        self.local_checker = LocalDBChecker()
        self.last_tmdn_query_time = 0
        self.nice_class_map = NICE_CLASS_MAP

    def setup_logging(self):
        """配置日志输出格式"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _wait_for_tmdn_rate_limit(self):
        """确保TMDN查询间隔至少1秒"""
        current_time = time.time()
        time_since_last_query = current_time - self.last_tmdn_query_time
        if time_since_last_query < 1:
            time.sleep(1 - time_since_last_query)
        self.last_tmdn_query_time = time.time()

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

    def check_trademark(self, query_name: str, nice_class: str = "20", region: str = "美国") -> Dict[str, Any]:
        """检查商标在各个系统中的状态
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
            region: 查询区域（美国/美国+欧洲）
        """
        logging.info(f"\n开始检查商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')}, 区域: {region})")

        try:
            # 1. 首先检查本地数据库
            local_result = self.local_checker.search_trademark(query_name, nice_class, region)
            if local_result["status"] == "error":
                return local_result
            
            if local_result["in_local_db"]:
                local_result["status_message"] = QUERY_STATUS["LOCAL_MATCH"]
                return local_result

            # 2. 本地未找到，查询 TMDN
            self._wait_for_tmdn_rate_limit()
            logging.info("正在查询 TMDN...")
            tmdn_result = self.tmdn_checker.search_trademark(query_name, nice_class, region)
            
            if tmdn_result["status"] != "success":
                error_msg = f"TMDN查询失败: {tmdn_result.get('error_message', '未知错误')}"
                logging.error(error_msg)
                return {
                    "query_name": query_name,
                    "status": "error",
                    "error_message": error_msg,
                    "brands": [],
                    "total_found": 0,
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": ["TMDN"],
                    "search_params": tmdn_result["search_params"]
                }

            # 检查 TMDN 结果的匹配
            exact_matches = self._check_exact_match(query_name, tmdn_result["brands"])
            
            if exact_matches:
                # TMDN 找到完全匹配，返回结果
                return {
                    "query_name": query_name,
                    "status": "success",
                    "status_message": QUERY_STATUS["EXACT_MATCH"],
                    "brands": tmdn_result["brands"],
                    "total_found": tmdn_result["total_found"],
                    "has_exact_match": True,
                    "exact_matches": exact_matches,
                    "search_source": ["TMDN"],
                    "search_params": tmdn_result["search_params"]
                }

            # 3. TMDN 未找到完全匹配，继续查询 WIPO
            logging.info("TMDN未找到匹配，继续查询WIPO...")
            wipo_result = self.wipo_checker.search_trademark(query_name, nice_class, region)
            
            if wipo_result["status"] != "success":
                error_msg = f"WIPO查询失败: {wipo_result.get('error_message', '未知错误')}"
                logging.error(error_msg)
                return {
                    "query_name": query_name,
                    "status": "error",
                    "error_message": error_msg,
                    "brands": tmdn_result["brands"],
                    "total_found": tmdn_result["total_found"],
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": ["TMDN", "WIPO"],
                    "search_params": wipo_result["search_params"]
                }

            # 合并结果
            all_brands = list(set(tmdn_result["brands"] + wipo_result["brands"]))
            total_found = tmdn_result["total_found"] + wipo_result["total_found"]
            
            # 检查 WIPO 结果的完全匹配
            wipo_exact_matches = self._check_exact_match(query_name, wipo_result["brands"])
            all_exact_matches = list(set(exact_matches + wipo_exact_matches))

            if wipo_exact_matches:
                status_message = QUERY_STATUS["EXACT_MATCH"]
            elif wipo_result["total_found"] > 15:
                status_message = QUERY_STATUS["NEED_ATTENTION"]
            else:
                status_message = QUERY_STATUS["NO_MATCH"]

            return {
                "query_name": query_name,
                "status": "success",
                "status_message": status_message,
                "brands": sorted(all_brands),
                "total_found": total_found,
                "has_exact_match": bool(all_exact_matches),
                "exact_matches": sorted(all_exact_matches),
                "search_source": ["TMDN", "WIPO"],
                "search_params": wipo_result["search_params"]
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
                    "region": region,
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "查询出错"
                }
            }