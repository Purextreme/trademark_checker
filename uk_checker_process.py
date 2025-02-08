import multiprocessing
import logging
import traceback
import queue
from typing import Dict, Any
from uk_checker import UKChecker

def setup_logging():
    """配置日志输出格式"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def uk_checker_process(input_queue: multiprocessing.Queue, output_queue: multiprocessing.Queue):
    """在独立进程中运行UK查询
    
    Args:
        input_queue: 用于接收查询请求的队列
        output_queue: 用于发送查询结果的队列
    """
    setup_logging()
    checker = None
    
    try:
        checker = UKChecker()
        logging.info("UK查询进程初始化成功")
        
        while True:
            try:
                # 从输入队列获取查询参数（设置1秒超时）
                query_data = input_queue.get(timeout=1)
                
                # 检查是否需要停止进程
                if query_data == "STOP":
                    logging.info("UK查询进程收到停止信号")
                    break
                
                # 解析查询参数
                query_name = query_data["query_name"]
                nice_classes = query_data["nice_classes"]
                
                # 执行查询
                logging.info(f"UK查询进程开始查询: {query_name}")
                result = checker.search_trademark(query_name, nice_classes)
                
                # 将结果放入输出队列
                output_queue.put(result)
                logging.info(f"UK查询进程完成查询: {query_name}")
                
            except queue.Empty:
                # 队列超时，继续等待
                continue
            except Exception as e:
                # 获取完整的错误堆栈
                error_stack = traceback.format_exc()
                error_msg = f"UK查询进程出错: {str(e)}\n{error_stack}"
                logging.error(error_msg)
                # 发送错误结果
                output_queue.put({
                    "success": False,
                    "message": error_msg,
                    "data": {
                        "total": 0,
                        "hits": []
                    }
                })
    except Exception as e:
        # 进程初始化错误
        error_stack = traceback.format_exc()
        error_msg = f"UK查询进程初始化失败: {str(e)}\n{error_stack}"
        logging.error(error_msg)
        output_queue.put({
            "success": False,
            "message": error_msg,
            "data": {
                "total": 0,
                "hits": []
            }
        })
    finally:
        # 确保资源被正确释放
        if checker:
            try:
                # 这里可以添加清理代码
                pass
            except Exception as e:
                logging.error(f"清理资源时出错: {str(e)}")

def run_uk_process():
    """启动UK查询进程的入口点"""
    multiprocessing.freeze_support()
    input_queue = multiprocessing.Queue()
    output_queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=uk_checker_process,
        args=(input_queue, output_queue)
    )
    process.start()
    return process, input_queue, output_queue

class UKCheckerProcess:
    """UK查询进程管理器"""
    
    def __init__(self):
        self.input_queue = None
        self.output_queue = None
        self.process = None
        self._is_stopping = False  # 新增状态标记
        # 不在初始化时启动进程
    
    def start_process(self):
        """启动UK查询进程"""
        if self._is_stopping:
            logging.warning("进程正在停止中，请稍后再试")
            return
            
        if self.process is None or not self.process.is_alive():
            try:
                self.process, self.input_queue, self.output_queue = run_uk_process()
                # 等待进程初始化完成（最多等待5秒）
                try:
                    init_result = self.output_queue.get(timeout=5)
                    if not init_result["success"]:
                        raise RuntimeError(init_result["message"])
                except queue.Empty:
                    pass  # 没有错误消息就继续
                logging.info("UK查询进程已启动")
            except Exception as e:
                error_stack = traceback.format_exc()
                error_msg = f"启动UK查询进程失败: {str(e)}\n{error_stack}"
                logging.error(error_msg)
                raise RuntimeError(error_msg)
    
    def stop_process(self):
        """停止UK查询进程"""
        if self._is_stopping:  # 防止重复停止
            return
            
        self._is_stopping = True
        try:
            if self.process and self.process.is_alive():
                try:
                    self.input_queue.put("STOP")
                    for _ in range(3):  # 最多等待3次
                        if self.process.join(timeout=2):  # 每次等待2秒
                            break
                    if self.process.is_alive():
                        logging.warning("UK查询进程未能正常停止，将在下次查询时重新创建")
                    else:
                        logging.info("UK查询进程已正常停止")
                except Exception as e:
                    logging.error(f"停止UK查询进程时出错: {str(e)}")
        finally:
            self._is_stopping = False
    
    def search_trademark(self, query_name: str, nice_classes: Any) -> Dict[str, Any]:
        """发送查询请求并等待结果
        
        Args:
            query_name: 要查询的商标名称
            nice_classes: 商标类别（可以是字符串或列表）
            
        Returns:
            查询结果字典
        """
        if self._is_stopping:
            return {
                "success": False,
                "error": "进程正在停止中，请稍后重试"
            }
            
        try:
            # 确保进程在运行
            self.start_process()
            
            # 发送查询请求
            self.input_queue.put({
                "query_name": query_name,
                "nice_classes": nice_classes
            })
            
            # 等待结果（设置60秒超时，因为UK查询可能比较慢）
            try:
                result = self.output_queue.get(timeout=60)
                # 确保返回格式一致
                if isinstance(result, dict) and "success" in result:
                    return result
                return {
                    "success": False,
                    "error": "返回格式错误"
                }
            except queue.Empty:
                error_msg = "UK查询超时（60秒）"
                logging.error(error_msg)
                # 超时后重启进程
                self.stop_process()
                self.start_process()
                return {
                    "success": False,
                    "message": error_msg,
                    "data": {
                        "total": 0,
                        "hits": []
                    }
                }
            
        except Exception as e:
            error_stack = traceback.format_exc()
            error_msg = f"UK查询请求出错: {str(e)}\n{error_stack}"
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "data": {
                    "total": 0,
                    "hits": []
                }
            }
    
    def __del__(self):
        """确保进程在对象销毁时正确关闭"""
        self.stop_process()

if __name__ == '__main__':
    multiprocessing.freeze_support() 