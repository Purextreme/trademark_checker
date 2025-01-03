import pandas as pd
import logging
from typing import Dict, Any, Optional, Tuple
from config import LOCAL_DB_CONFIG, NICE_CLASS_MAP, QUERY_STATUS

class LocalDBChecker:
    def __init__(self):
        self.setup_logging()
        self.csv_file = LOCAL_DB_CONFIG["csv_file"]
        self.encoding = LOCAL_DB_CONFIG["encoding"]
        self.columns = LOCAL_DB_CONFIG["columns"]
        self.nice_class_map = NICE_CLASS_MAP
        self.df = None
        self.load_database()

    def setup_logging(self):
        """配置日志输出格式"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    def load_database(self) -> None:
        """加载CSV数据库"""
        try:
            self.df = pd.read_csv(self.csv_file, encoding=self.encoding)
            logging.info(f"成功加载本地数据库，共 {len(self.df)} 条记录")
        except Exception as e:
            logging.error(f"加载本地数据库失败: {str(e)}")
            self.df = pd.DataFrame(columns=[
                self.columns["name"],
                self.columns["region"],
                self.columns["nice_class"]
            ])

    def search_trademark(self, query_name: str, nice_class: str = "20", region: str = "美国") -> Dict[str, Any]:
        """在本地数据库中搜索商标
        Args:
            query_name: 要查询的商标名称
            nice_class: 商标类别（14/20/21）
            region: 查询区域（美国/美国+欧洲）- 本地查询不考虑区域
        """
        try:
            logging.info(f"开始本地数据库查询: {query_name} (类别: {nice_class} - {self.nice_class_map.get(nice_class, '')})")
            
            if self.df is None or self.df.empty:
                logging.warning("本地数据库为空")
                return self._create_response(query_name, nice_class, region, False)
            
            # 转换为小写进行比较
            query_name = query_name.lower().strip()
            
            # 在数据库中查找匹配项，只考虑名称和类别的完全匹配
            mask = (
                self.df[self.columns["name"]].str.lower().str.strip() == query_name
            ) & (
                self.df[self.columns["nice_class"]].astype(str) == str(nice_class)
            )
            
            matches = self.df[mask]
            
            if not matches.empty:
                logging.info(f"在本地数据库中找到匹配: {query_name}")
                return self._create_response(query_name, nice_class, region, True)
            
            logging.info(f"本地数据库中未找到匹配: {query_name}")
            return self._create_response(query_name, nice_class, region, False)
            
        except Exception as e:
            error_msg = f"本地数据库查询出错: {str(e)}"
            logging.error(error_msg)
            return {
                "query_name": query_name,
                "status": "error",
                "error_message": error_msg,
                "in_local_db": False,
                "brands": [],
                "total_found": 0,
                "has_exact_match": False,
                "exact_matches": [],
                "search_source": ["本地数据库"],
                "search_params": {
                    "region": region,
                    "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                    "status": "本地数据库查询"
                }
            }

    def _create_response(self, query_name: str, nice_class: str, region: str, found: bool) -> Dict[str, Any]:
        """创建标准的响应格式"""
        return {
            "query_name": query_name,
            "status": "success",
            "in_local_db": found,
            "brands": [query_name] if found else [],
            "total_found": 1 if found else 0,
            "has_exact_match": found,
            "exact_matches": [query_name] if found else [],
            "search_source": ["本地数据库"],
            "search_params": {
                "region": region,
                "nice_class": f"{nice_class} - {self.nice_class_map.get(nice_class, '')}",
                "status": "本地数据库查询"
            }
        } 