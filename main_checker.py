import logging
from typing import List, Dict, Any, Tuple
from WIPO_name_checker import WIPOChecker
from tmdn_name_checker import TMDNNameChecker
import time
import os

class TrademarkChecker:
    def __init__(self):
        self.setup_logging()
        self.wipo_checker = WIPOChecker()
        self.tmdn_checker = TMDNNameChecker()
        self.last_tmdn_query_time = 0
        self.nice_class_map = {
            "14": "贵重金属及合金等",
            "20": "家具镜子相框等",
            "21": "家庭或厨房用具及容器等"
        }
        self.checked_names_file = "checked_name.txt"

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
        query_name = query_name.lower().strip()
        return [name for name in brand_names 
                if query_name in [word.lower().strip() for word in name.split()]]

    def _check_similar_match(self, query_name: str, brand_names: List[str]) -> List[str]:
        """检查是否存在相似匹配（仅一个字母不同）"""
        query_name = query_name.lower().strip()
        similar_matches = []
        
        for brand in brand_names:
            # 对每个品牌名称进行分词
            for word in brand.split():
                word = word.lower().strip()
                # 只比较长度相同的单词
                if len(word) == len(query_name):
                    # 计算不同字母的数量
                    diff_count = sum(1 for a, b in zip(word, query_name) if a != b)
                    if diff_count == 1:
                        similar_matches.append(brand)
                        break
        
        return similar_matches

    def _check_local_database(self, query_name: str) -> Tuple[bool, str, List[str], List[str]]:
        """检查本地数据库
        Returns:
            (是否找到匹配, 匹配类型, 完全匹配列表, 相似匹配列表)
        """
        if not os.path.exists(self.checked_names_file):
            return False, "", [], []

        try:
            with open(self.checked_names_file, 'r', encoding='utf-8') as f:
                checked_names = [line.strip() for line in f.readlines()]

            # 检查完全匹配
            exact_matches = self._check_exact_match(query_name, checked_names)
            if exact_matches:
                return True, "exact", exact_matches, []

            # 检查相似匹配
            similar_matches = self._check_similar_match(query_name, checked_names)
            if similar_matches:
                return True, "similar", [], similar_matches

            return False, "", [], []

        except Exception as e:
            logging.error(f"读取本地数据库出错: {str(e)}")
            return False, "", [], []

    def check_trademark(self, query_name: str, nice_class: str = "20") -> Dict[str, Any]:
        """检查商标在两个系统中的状态
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
        """
        logging.info(f"\n开始检查商标: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')})")
        result = {
            "query_name": query_name,
            "status": "success",
            "brands": [],
            "total_found": 0,
            "total_displayed": 0,
            "has_exact_match": False,
            "has_similar_match": False,  # 新增：是否有相似匹配
            "exact_matches": [],
            "similar_matches": [],  # 新增：相似匹配列表
            "status_message": "",
            "search_source": ["本地数据库"],  # 默认包含本地数据库
            "error_details": [],
            "search_params": {
                "region": "US",
                "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                "status": "已注册或待审"
            }
        }

        try:
            # 首先检查本地数据库
            found, match_type, exact_matches, similar_matches = self._check_local_database(query_name)
            if found:
                if match_type == "exact":
                    result["has_exact_match"] = True
                    result["exact_matches"].extend(exact_matches)
                    result["status_message"] = "在本地数据库中发现完全匹配"
                    return result
                elif match_type == "similar":
                    result["has_similar_match"] = True
                    result["similar_matches"].extend(similar_matches)
                    result["status_message"] = "在本地数据库中发现相似匹配"
                    return result

            # 本地未找到，查询 TMDN
            self._wait_for_tmdn_rate_limit()
            logging.info("正在查询 TMDN...")
            tmdn_result = self.tmdn_checker.search_trademark(query_name, nice_class)
            
            if tmdn_result["status"] != "success":
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

            # 检查 TMDN 结果中的匹配
            exact_matches = self._check_exact_match(query_name, tmdn_result["brands"])
            similar_matches = self._check_similar_match(query_name, tmdn_result["brands"])
            
            if not exact_matches and not similar_matches:
                # 没有任何匹配，继续查询 WIPO
                logging.info("TMDN未找到匹配，继续查询WIPO...")
                try:
                    wipo_result = self.wipo_checker.search_trademark(query_name, nice_class)
                    if wipo_result["status"] == "success":
                        result["brands"].extend(wipo_result["brands"])
                        result["total_found"] += wipo_result["total_found"]
                        result["search_source"].append("WIPO")
                        logging.info(f"WIPO 找到 {wipo_result['total_found']} 个结果")
                        # 更新匹配检查，包含 WIPO 的结果
                        exact_matches.extend(self._check_exact_match(query_name, wipo_result["brands"]))
                        similar_matches.extend(self._check_similar_match(query_name, wipo_result["brands"]))
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
                if exact_matches:
                    logging.info("TMDN已找到完全匹配，跳过WIPO查询")
                else:
                    logging.info("TMDN已找到相似匹配，跳过WIPO查询")

            # 更新显示的结果数量和匹配状态
            result["total_displayed"] = len(result["brands"])
            result["has_exact_match"] = len(exact_matches) > 0
            result["exact_matches"] = list(set(exact_matches))  # 去重
            result["has_similar_match"] = len(similar_matches) > 0
            result["similar_matches"] = list(set(similar_matches))  # 去重
            
            # 生成状态消息
            if result["total_found"] == 0:
                result["status_message"] = "未找到相关商标记录"
            else:
                result["status_message"] = f"找到 {result['total_found']} 个相关商标"
                if result["has_exact_match"]:
                    result["status_message"] += "，包含完全匹配项"
                elif result["has_similar_match"]:
                    result["status_message"] += "，包含相似匹配项"
                result["status_message"] += f" (数据来源: {', '.join(result['search_source'])})"

        except Exception as e:
            error_msg = f"查询过程出错: {str(e)}"
            logging.error(error_msg)
            result["status"] = "error"
            result["error_message"] = error_msg
            result["error_details"].append(error_msg)

        return result

    def check_trademarks(self, names: List[str], nice_class: str = "20") -> List[Dict[str, Any]]:
        """批量检查多个商标名称"""
        if len(names) > 20:
            raise ValueError("每次最多可查询20个名称")
            
        results = []
        for name in names:
            try:
                result = self.check_trademark(name, nice_class)
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
                    "has_similar_match": False,
                    "exact_matches": [],
                    "similar_matches": [],
                    "search_source": ["本地数据库"],
                    "error_details": [error_msg],
                    "search_params": {
                        "region": "US",
                        "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                        "status": "已注册或待审"
                    }
                })
        return results