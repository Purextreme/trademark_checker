import logging
from typing import Dict, Any, Union, List
import requests
from config import US_CONFIG
import json
import time
import random

class USChecker:
    def __init__(self):
        """初始化美国商标查询器"""
        self.config = US_CONFIG
        self.logger = logging.getLogger("USChecker")
        self.logger.setLevel(logging.INFO)
        self.waf_token = None
        self.session_storage = None
        self.last_telemetry_time = 0

    def _build_query_payload(self, query_name: str, nice_classes: List[str]) -> Dict[str, Any]:
        """构建查询请求体
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别列表
        Returns:
            Dict: 查询请求体
        """
        # 将类别编号格式化为三位数字字符串
        formatted_classes = [self.config["nice_classes"][cls] for cls in nice_classes if cls in self.config["nice_classes"]]
        
        return {
            "query": {
                "bool": {
                    "must": [{
                        "bool": {
                            "should": [
                                {
                                    "match_phrase": {
                                        "WM": {
                                            "query": query_name,
                                            "boost": 5
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "WM": {
                                            "query": query_name,
                                            "boost": 2
                                        }
                                    }
                                },
                                {
                                    "match_phrase": {
                                        "PM": {
                                            "query": query_name,
                                            "boost": 2
                                        }
                                    }
                                }
                            ]
                        }
                    }],
                    "filter": [
                        {
                            "term": {
                                "LD": "true"
                            }
                        },
                        {
                            "terms": {
                                "IC": formatted_classes
                            }
                        }
                    ]
                }
            },
            "size": 200,
            "from": 0,
            "track_total_hits": True,
            "_source": ["wordmark"]  # 只获取商标名
        }

    def _send_telemetry(self):
        """发送telemetry数据到AWS WAF"""
        try:
            if not self.waf_token or not self.session_storage:
                return
            
            current_time = time.time()
            # 每10秒发送一次telemetry
            if current_time - self.last_telemetry_time < 10:
                return
                
            headers = {
                'accept': '*/*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'content-type': 'text/plain;charset=UTF-8',
                'dnt': '1',
                'origin': 'https://tmsearch.uspto.gov',
                'priority': 'u=1, i',
                'referer': 'https://tmsearch.uspto.gov/',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
            }
            
            data = {
                "existing_token": self.waf_token,
                "awswaf_session_storage": self.session_storage,
                "client": "Browser",
                "signals": [],
                "metrics": [
                    {"name": "12", "value": 0.1, "unit": "2"},
                    {"name": "13", "value": 0.3, "unit": "2"},
                    {"name": "9", "value": 8, "unit": "4"},
                    {"name": "11", "value": 0.5, "unit": "2"}
                ]
            }
            
            response = requests.post(
                'https://tmsearch.uspto.gov/api-v1-0-0/telemetry',
                headers=headers,
                json=data,
                timeout=10
            )
            
            self.last_telemetry_time = current_time
            
        except Exception as e:
            self.logger.error(f"发送telemetry失败: {str(e)}")

    def _update_waf_token(self, response):
        """从响应中更新WAF token"""
        try:
            cookies = response.cookies
            for cookie in cookies:
                if cookie.name == 'aws-waf-token':
                    self.waf_token = cookie.value
                elif cookie.name == 'awswaf_session_storage':
                    self.session_storage = cookie.value
        except Exception as e:
            self.logger.error(f"更新WAF token失败: {str(e)}")

    def search_trademark(self, query_name: str, nice_classes: Union[str, List[str]]) -> Dict[str, Any]:
        """搜索美国商标
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别（可以是单个类别字符串或类别列表）
        Returns:
            Dict: 查询结果
        """
        if isinstance(nice_classes, str):
            nice_classes = [nice_classes]

        try:
            self.logger.info(f"开始查询美国商标: {query_name} (类别: {', '.join(nice_classes)})")
            
            # 构建请求体
            payload = self._build_query_payload(query_name, nice_classes)
            
            # 构建请求头
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'content-type': 'application/json',
                'dnt': '1',
                'origin': 'https://tmsearch.uspto.gov',
                'priority': 'u=1, i',
                'referer': 'https://tmsearch.uspto.gov/search/search-results',
                'sec-ch-ua': '"Not A(Brand";v="8", "Chromium";v="132", "Google Chrome";v="132"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
            }
            
            # 发送telemetry
            self._send_telemetry()
            
            # 发送请求（使用一次性连接）
            response = requests.post(
                'https://tmsearch.uspto.gov/api-v1-0-0/tmsearch',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            # 更新WAF token
            self._update_waf_token(response)
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            
            # 提取匹配结果
            hits = result.get("hits", {})
            hits_list = hits.get("hits", [])
            total = hits.get("totalValue", 0)
            
            # 只提取商标名称
            brand_names = []
            for hit in hits_list:
                if 'source' in hit and 'wordmark' in hit['source']:
                    brand_name = hit['source']['wordmark']
                    if brand_name:
                        brand_names.append(brand_name)
                elif '_source' in hit and 'wordmark' in hit['_source']:
                    brand_name = hit['_source']['wordmark']
                    if brand_name:
                        brand_names.append(brand_name)
            
            self.logger.info(f"查询完成，找到 {total} 个商标名称")
            
            if brand_names:
                return {
                    "success": True,
                    "data": brand_names
                }
            
            return {
                "success": True,
                "data": "NO_RESULTS"
            }
            
        except requests.RequestException as e:
            error_msg = f"查询美国商标时发生错误: {str(e)}"
            self.logger.error(error_msg)
            if hasattr(e.response, 'text'):
                print(f"错误响应内容: {e.response.text[:500]}")
            return {
                "success": False,
                "error": error_msg
            }
        except Exception as e:
            error_msg = f"处理查询结果时发生错误: {str(e)}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }

def test_continuous_query():
    """测试连续查询的稳定性
    - 每次查询间隔5秒
    - 每次查询都是新的会话（模拟重新打开页面）
    """
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 测试词列表
    test_words = [
        # 常见英文名
        'monica', 'james', 'david', 'sarah', 'emma',
        # 科技公司
        'apple', 'google', 'tesla', 'oracle', 'cisco',
        # 希腊字母
        'alpha', 'beta', 'delta', 'sigma', 'omega',
        # 颜色和自然
        'azure', 'coral', 'forest', 'river', 'stone'
    ]
    
    logger = logging.getLogger("US_TEST")
    query_interval = 5  # 查询间隔5秒
    
    logger.info(f"\n开始连续查询测试:")
    logger.info(f"总测试词数: {len(test_words)}")
    logger.info(f"查询间隔: {query_interval}秒")
    logger.info("测试词列表（按类别）:")
    logger.info("常见英文名:")
    for word in test_words[0:5]:
        logger.info(f"  - {word}")
    logger.info("科技公司:")
    for word in test_words[5:10]:
        logger.info(f"  - {word}")
    logger.info("希腊字母:")
    for word in test_words[10:15]:
        logger.info(f"  - {word}")
    logger.info("颜色和自然:")
    for word in test_words[15:20]:
        logger.info(f"  - {word}")
    logger.info("=" * 50)
    
    success_count = 0
    error_count = 0
    total_wait_time = 0
    
    # 遍历每个测试词
    for i, current_word in enumerate(test_words):
        try:
            logger.info(f"\n第 {i + 1} 个词开始查询...")
            logger.info(f"查询词: {current_word}")
            start_time = time.time()
            
            # 每次查询都创建新的查询器实例（模拟新开页面）
            checker = USChecker()
            
            # 执行查询
            result = checker.search_trademark(current_word, "20")
            
            # 记录查询结果
            if result["success"]:
                success_count += 1
                if result["data"] == "NO_RESULTS":
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

def main():
    """主函数，用于测试"""
    # 运行连续查询测试
    test_continuous_query()

if __name__ == "__main__":
    main() 