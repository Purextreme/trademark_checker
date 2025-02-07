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
        self.session = requests.Session()
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
            
            response = self.session.post(
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
            
            # 发送请求
            response = self.session.post(
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
    - 分两批查询，每批5个词
    - 每批内查询间隔30秒
    - 两批之间间隔5分钟
    - 每次查询都是新的会话（模拟重新打开页面）
    """
    # 设置日志级别为DEBUG以查看详细信息
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # 测试词列表（分两批）
    batch1 = ['monica', 'james', 'apple', 'orange', 'delta']
    batch2 = ['sigma', 'alpha', 'beta', 'gamma', 'omega']
    batches = [batch1, batch2]
    
    logger = logging.getLogger("US_TEST")
    query_interval = 10    # 批内查询间隔10秒
    batch_interval = 300   # 批次间隔5分钟
    
    logger.info(f"\n开始分批次查询测试:")
    logger.info(f"第一批词: {', '.join(batch1)}")
    logger.info(f"第二批词: {', '.join(batch2)}")
    logger.info(f"批内查询间隔: {query_interval}秒")
    logger.info(f"批次间隔: {batch_interval}秒（5分钟）")
    logger.info("=" * 50)
    
    success_count = 0
    error_count = 0
    total_wait_time = 0
    
    # 遍历每一批
    for batch_index, words in enumerate(batches, 1):
        logger.info(f"\n开始第 {batch_index} 批查询...")
        
        # 遍历批内的每个词
        for i, current_word in enumerate(words):
            try:
                logger.info(f"\n第 {batch_index} 批 - 第 {i + 1} 个词开始查询...")
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
                    logger.error(f"查询失败 ({current_word}): {result['error']}")
                
                # 计算实际用时
                elapsed = time.time() - start_time
                logger.info(f"本次查询耗时: {elapsed:.2f}秒")
                
                # 如果不是批内最后一个词，等待查询间隔
                if i < len(words) - 1:
                    wait_time = max(0, query_interval - elapsed)
                    logger.info(f"等待 {wait_time:.2f} 秒后进行下一次查询...")
                    logger.info(f"下一个查询词将是: {words[i+1]}")
                    time.sleep(wait_time)
                    total_wait_time += wait_time
                
            except Exception as e:
                error_count += 1
                logger.error(f"发生异常 ({current_word}): {str(e)}")
                if i < len(words) - 1:
                    logger.info(f"等待 {query_interval} 秒后继续...")
                    time.sleep(query_interval)
                    total_wait_time += query_interval
        
        # 如果不是最后一批，等待批次间隔
        if batch_index < len(batches):
            logger.info(f"\n第 {batch_index} 批查询完成，等待 {batch_interval} 秒（5分钟）后开始下一批...")
            logger.info(f"下一批词: {', '.join(batches[batch_index])}")
            time.sleep(batch_interval)
            total_wait_time += batch_interval
    
    # 输出统计信息
    total_words = sum(len(batch) for batch in batches)
    logger.info("\n测试完成!")
    logger.info("=" * 50)
    logger.info(f"总批次数: {len(batches)}")
    logger.info(f"总查询次数: {total_words}")
    logger.info(f"成功次数: {success_count}")
    logger.info(f"失败次数: {error_count}")
    logger.info(f"成功率: {(success_count/total_words)*100:.1f}%")
    logger.info(f"批内查询间隔: {query_interval}秒")
    logger.info(f"批次间隔: {batch_interval}秒（5分钟）")
    logger.info(f"平均等待时间: {total_wait_time/(total_words-1):.1f}秒")
    logger.info("\n查询词统计:")
    for batch_index, words in enumerate(batches, 1):
        logger.info(f"第{batch_index}批: {', '.join(words)}")

def main():
    """主函数，用于测试"""
    # 运行连续查询测试
    test_continuous_query()

if __name__ == "__main__":
    main() 