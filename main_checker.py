import logging
from typing import List, Dict, Any
from WIPO_name_checker import WIPOChecker
from tmdn_name_checker import TMDNNameChecker
import time

class TrademarkChecker:
    def __init__(self):
        self.setup_logging()
        self.wipo_checker = WIPOChecker()
        self.tmdn_checker = TMDNNameChecker()
        self.last_tmdn_query_time = 0

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _wait_for_tmdn_rate_limit(self):
        """确保TMDN查询间隔至少1秒"""
        current_time = time.time()
        time_since_last_query = current_time - self.last_tmdn_query_time
        if time_since_last_query < 1:
            time.sleep(1 - time_since_last_query)
        self.last_tmdn_query_time = time.time()

    def _check_exact_match(self, query_name: str, brand_names: List[str]) -> List[str]:
        """检查是否存在完全匹配"""
        return [name for name in brand_names 
                if query_name.lower() in name.lower().split()]

    def check_trademark(self, query_name: str) -> Dict[str, Any]:
        """检查商标在两个系统中的状态"""
        logging.info(f"\n开始检查商标: {query_name}")
        result = {
            "query_name": query_name,
            "status": "success",
            "brands": [],
            "total_found": 0,
            "total_displayed": 0,
            "has_exact_match": False,
            "exact_matches": [],
            "status_message": "",
            "search_source": [],
            "error_details": []  # 用于记录详细错误信息
        }

        try:
            # 首先查询 TMDN
            self._wait_for_tmdn_rate_limit()
            logging.info("正在查询 TMDN...")
            tmdn_result = self.tmdn_checker.search_trademark(query_name)
            
            if tmdn_result["status"] != "success":
                # TMDN 查询失败，直接返回错误
                error_msg = f"TMDN查询失败: {tmdn_result.get('error_message', '未知错误')}"
                logging.error(error_msg)
                result["status"] = "error"
                result["error_message"] = error_msg
                result["error_details"].append(error_msg)
                return result

            # TMDN 查询成功，处理结果
            result["brands"].extend(tmdn_result["brands"])
            result["total_found"] += tmdn_result.get("total_found", 0)
            result["search_source"].append("TMDN")
            logging.info(f"TMDN 找到 {tmdn_result.get('total_found', 0)} 个结果")

            # 检查 TMDN 结果中是否有完全匹配
            exact_matches = self._check_exact_match(query_name, tmdn_result["brands"])
            
            if not exact_matches:
                # 没有完全匹配，继续查询 WIPO
                logging.info("TMDN未找到完全匹配，继续查询WIPO...")
                try:
                    wipo_result = self.wipo_checker.search_trademark(query_name)
                    if wipo_result["status"] == "success":
                        result["brands"].extend(wipo_result["brands"])
                        result["total_found"] += wipo_result["total_found"]
                        result["search_source"].append("WIPO")
                        logging.info(f"WIPO 找到 {wipo_result['total_found']} 个结果")
                        # 更新完全匹配检查，包含 WIPO 的结果
                        exact_matches.extend(self._check_exact_match(query_name, wipo_result["brands"]))
                    else:
                        error_msg = f"WIPO查询失败: {wipo_result.get('error_message', '未知错误')}"
                        logging.error(error_msg)
                        result["error_details"].append(error_msg)
                        result["status"] = "error"
                        result["error_message"] = error_msg
                        return result
                except Exception as e:
                    error_msg = f"WIPO查询出错: {str(e)}"
                    logging.error(error_msg)
                    result["error_details"].append(error_msg)
                    result["status"] = "error"
                    result["error_message"] = error_msg
                    return result
            else:
                logging.info("TMDN已找到完全匹配，跳过WIPO查询")

            # 更新显示的结果数量和匹配状态
            result["total_displayed"] = len(result["brands"])
            result["has_exact_match"] = len(exact_matches) > 0
            result["exact_matches"] = list(set(exact_matches))  # 去重
            
            # 生成状态消息
            if result["total_found"] == 0:
                result["status_message"] = "未找到相关商标记录"
            else:
                result["status_message"] = f"找到 {result['total_found']} 个相关商标"
                if result["has_exact_match"]:
                    result["status_message"] += "，包含完全匹配项"
                result["status_message"] += f" (数据来源: {', '.join(result['search_source'])})"

        except Exception as e:
            error_msg = f"查询过程出错: {str(e)}"
            logging.error(error_msg)
            result["status"] = "error"
            result["error_message"] = error_msg
            result["error_details"].append(error_msg)

        return result

    def check_trademarks(self, names: List[str]) -> List[Dict[str, Any]]:
        """批量检查多个商标名称"""
        if len(names) > 20:
            raise ValueError("每次最多可查询20个名称")
            
        results = []
        for name in names:
            try:
                result = self.check_trademark(name)
                results.append(result)
            except Exception as e:
                error_msg = f"检查商标 {name} 时出错: {str(e)}"
                logging.error(error_msg)
                results.append({
                    "query_name": name,
                    "status": "error",
                    "error_message": error_msg,
                    "brands": [],
                    "total_found": 0,
                    "total_displayed": 0,
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": [],
                    "error_details": [error_msg]
                })
        return results 