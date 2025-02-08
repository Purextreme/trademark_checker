import requests
import logging
from typing import Dict, Any, List, Union
from config import TMDN_CONFIG, NICE_CLASS_MAP, QUERY_PARAMS
import time

class TMDNNameChecker:
    def __init__(self):
        self.setup_logging()
        self.base_url = TMDN_CONFIG["base_url"]
        self.headers = TMDN_CONFIG["headers"]
        self.nice_class_map = NICE_CLASS_MAP
        self.request_defaults = TMDN_CONFIG["request_defaults"]

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def _format_nice_classes(self, nice_classes: Union[str, List[str]]) -> List[str]:
        """格式化商标类别列表
        如果只有一个类别，直接返回包含该类别的列表
        如果有多个类别，在类别之间添加"OR"
        """
        if isinstance(nice_classes, str):
            return [nice_classes]
        
        # 处理多个类别的情况
        formatted_classes = []
        for i, nice_class in enumerate(nice_classes):
            formatted_classes.append(nice_class)
            if i < len(nice_classes) - 1:
                formatted_classes.append("OR")
        return formatted_classes

    def _format_nice_class_display(self, nice_classes: Union[str, List[str]]) -> str:
        """格式化类别显示文本"""
        if isinstance(nice_classes, str):
            return f"{nice_classes} - {self.nice_class_map.get(nice_classes, '')}"
        
        display_texts = []
        for nice_class in nice_classes:
            display_texts.append(f"{nice_class} - {self.nice_class_map.get(nice_class, '')}")
        return "，".join(display_texts)

    def search_trademark(self, query_name: str, nice_classes: Union[str, List[str]], regions: Union[str, List[str]] = "美国") -> Dict[str, Any]:
        """搜索商标
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别（可以是单个类别字符串或类别列表）
            regions: 查询区域（可以是单个区域字符串或区域列表）
        """
        try:
            # 确保regions是列表
            if isinstance(regions, str):
                regions = [regions]
            
            nice_class_display = self._format_nice_class_display(nice_classes)
            logging.info(f"开始查询TMDN商标: {query_name} (类别: {nice_class_display}, 区域: {regions})")
            
            # 合并所有选中区域的配置
            all_offices = []
            all_territories = []
            for region in regions:
                region_config = TMDN_CONFIG["regions"].get(region, TMDN_CONFIG["regions"]["美国"])
                all_offices.extend(region_config["offices"])
                all_territories.extend(region_config["territories"])
            
            # 去重
            all_offices = list(set(all_offices))
            all_territories = list(set(all_territories))
            
            # 构建请求payload
            payload = {
                **self.request_defaults,  # 使用默认配置
                "basicSearch": query_name,
                "offices": all_offices,
                "territories": all_territories,
                "niceClass": self._format_nice_classes(nice_classes),
                "pageSize": str(QUERY_PARAMS["page_size"])
            }
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}"
                logging.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            data = response.json()
            total_results = data.get('totalResults', 0)
            
            # 提取商标信息
            brands = []
            for tm in data.get('tradeMarks', []):
                brand_name = tm.get('tmName', '')
                if brand_name:  # 确保不是空字符串
                    brands.append(brand_name)
            
            logging.info(f"TMDN查询完成，找到 {total_results} 个结果")
            
            # 使用新的返回格式
            if brands:
                return {
                    "success": True,
                    "data": brands  # 直接返回商标列表
                }
            
            return {
                "success": True,
                "data": "NO_RESULTS"
            }
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"TMDN查询出错: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }

def main():
    """主函数，用于测试连续查询"""
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 测试词列表（30个不同的词）
    test_words = [
        'monica', 'james', 'apple', 'orange', 'delta',
        'sigma', 'alpha', 'beta', 'gamma', 'omega',
        'zeta', 'theta', 'iota', 'kappa', 'lambda',
        'nike', 'adidas', 'puma', 'reebok', 'fila',
        'sony', 'samsung', 'apple', 'huawei', 'xiaomi',
        'ford', 'toyota', 'honda', 'bmw', 'audi'
    ]
    
    logger = logging.getLogger("TMDN_TEST")
    query_interval = 5  # 查询间隔5秒
    
    logger.info(f"\n开始连续查询测试:")
    logger.info(f"总测试词数: {len(test_words)}")
    logger.info(f"查询间隔: {query_interval}秒")
    logger.info("测试词列表:")
    for i, word in enumerate(test_words, 1):
        logger.info(f"{i}. {word}")
    logger.info("=" * 50)
    
    checker = TMDNNameChecker()
    success_count = 0
    error_count = 0
    total_wait_time = 0
    
    # 遍历每个测试词
    for i, current_word in enumerate(test_words):
        try:
            logger.info(f"\n第 {i + 1} 个词开始查询...")
            logger.info(f"查询词: {current_word}")
            start_time = time.time()
            
            # 执行查询（使用美国区域和类别20）
            result = checker.search_trademark(current_word, "20", "美国")
            
            # 记录查询结果
            if result["success"]:
                success_count += 1
                if result.get("data") == "NO_RESULTS":
                    logger.info(f"查询成功: {current_word} 未找到结果")
                else:
                    logger.info(f"查询成功: {current_word} 找到 {len(result['data'])} 个商标")
                    for brand in result["data"]:
                        logger.info(f"  - {brand}")
            else:
                error_count += 1
                logger.error(f"查询失败 ({current_word}): {result.get('error', '未知错误')}")
            
            # 计算实际用时
            elapsed = time.time() - start_time
            logger.info(f"本次查询耗时: {elapsed:.2f}秒")
            
            # 如果不是最后一个词，等待查询间隔
            if i < len(test_words) - 1:
                wait_time = max(0, query_interval - elapsed)
                logger.info(f"等待 {wait_time:.2f} 秒后进行下一次查询...")
                logger.info(f"下一个查询词将是: {test_words[i+1]}")
                time.sleep(wait_time)
                total_wait_time += wait_time
            
        except Exception as e:
            error_count += 1
            logger.error(f"发生异常 ({current_word}): {str(e)}")
            if i < len(test_words) - 1:
                logger.info(f"等待 {query_interval} 秒后继续...")
                time.sleep(query_interval)
                total_wait_time += query_interval
    
    # 输出统计信息
    logger.info("\n测试完成!")
    logger.info("=" * 50)
    logger.info(f"总查询次数: {len(test_words)}")
    logger.info(f"成功次数: {success_count}")
    logger.info(f"失败次数: {error_count}")
    logger.info(f"成功率: {(success_count/len(test_words))*100:.1f}%")
    logger.info(f"查询间隔: {query_interval}秒")
    logger.info(f"平均等待时间: {total_wait_time/(len(test_words)-1):.1f}秒")

if __name__ == "__main__":
    main() 