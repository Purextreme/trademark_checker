import logging
from uk_checker_process import UKCheckerProcess

def setup_logging():
    """配置日志输出格式"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('uk_debug.log', mode='w', encoding='utf-8')
        ]
    )

def test_uk_checker():
    """测试UK查询进程"""
    setup_logging()
    logging.info("开始测试UK查询进程")
    
    try:
        # 创建UK查询进程
        checker = UKCheckerProcess()
        
        # 测试单个类别查询
        query_name = "test"
        nice_classes = "20"
        logging.info(f"测试单个类别查询: {query_name} (类别: {nice_classes})")
        
        result = checker.search_trademark(query_name, nice_classes)
        logging.info(f"查询结果: {result}")
        
        # 测试多个类别查询
        query_name = "test"
        nice_classes = ["14", "20"]
        logging.info(f"测试多个类别查询: {query_name} (类别: {nice_classes})")
        
        result = checker.search_trademark(query_name, nice_classes)
        logging.info(f"查询结果: {result}")
        
        # 确保进程正确关闭
        checker.stop_process()
        logging.info("测试完成")
        
    except Exception as e:
        logging.error(f"测试过程中出错: {str(e)}", exc_info=True)

if __name__ == "__main__":
    test_uk_checker() 