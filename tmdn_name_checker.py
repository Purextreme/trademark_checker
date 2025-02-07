import requests
import logging
from typing import Dict, Any, List, Union
from config import TMDN_CONFIG, NICE_CLASS_MAP, QUERY_PARAMS

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
                    "message": error_msg,
                    "data": {
                        "total": 0,
                        "hits": []
                    }
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
            
            return {
                "success": True,
                "message": f"找到 {total_results} 个结果",
                "data": {
                    "total": total_results,
                    "hits": brands
                }
            }
            
        except Exception as e:
            error_msg = str(e)
            logging.error(f"TMDN查询出错: {error_msg}")
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
    checker = TMDNNameChecker()
    
    # 测试单个类别查询
    print("\n测试单个类别查询:")
    result = checker.search_trademark("monica", "20", "美国")
    print(f"找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")
    
    # 测试多个类别查询
    print("\n测试多个类别查询:")
    result = checker.search_trademark("monica", ["14", "20"], "欧盟")
    print(f"找到 {result['total_found']} 个相关商标:")
    if result['brands']:
        for brand in result['brands']:
            print(f"  - {brand}")

if __name__ == "__main__":
    main() 