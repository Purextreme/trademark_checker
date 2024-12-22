# -*- coding: utf-8 -*-
import gradio as gr
from validator import validate_name
from main_checker import TrademarkChecker
import time
import webbrowser
from threading import Timer
import logging
from logging.handlers import RotatingFileHandler
import threading

# 清空日志文件
with open('debug.log', 'w', encoding='utf-8') as f:
    f.write('')  # 清空文件内容

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        RotatingFileHandler(
            'debug.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=1,  # 只保留一个备份文件
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger(__name__)
logger.info("Starting application...")

# 实例化 TrademarkChecker
checker = TrademarkChecker()

# 全局查询锁
query_lock = threading.Lock()
# 记录当前查询状态
current_query = {"is_querying": False, "start_time": 0}

def reset_query_state():
    """重置查询状态"""
    global current_query
    current_query["is_querying"] = False
    current_query["start_time"] = 0

def parse_input_names(text: str) -> list[str]:
    """解析输入的多个名称"""
    names = [name.strip() for name in text.split('\n') if name.strip()]
    return names

def format_detailed_results(results: list[dict]) -> dict[str, str]:
    """为每个查询结果创建详细信息"""
    detailed_info = {}
    
    for result in results:
        query_name = result["query_name"]
        output = []
        
        if result["status"] == "error":
            output.append("❌ 查询出错")
            if "error_details" in result and result["error_details"]:
                output.append("错误详情：")
                for error in result["error_details"]:
                    output.append(f"- {error}")
            else:
                output.append(f"错误信息：{result.get('error_message', '未知错误')}")
        else:
            # 显示查询参数
            if "search_params" in result:
                params = result["search_params"]
                output.append("查询条件：")
                output.append(f"- 地区: {params['region']}")
                output.append(f"- 类别: {params['nice_class']}")
                output.append(f"- 状态: {params['status']}")
                output.append("")
            
            if "search_source" in result:
                output.append(f"🔍 数据来源: {', '.join(result['search_source'])}")
            output.append(f"查询状态: {result['status_message']}")
            
            if result["total_found"] > 0:
                output.append("\n找到的品牌:")
                for i, name in enumerate(result["brands"], 1):
                    output.append(f"{i}. {name}")
                
                if result["has_exact_match"]:
                    output.append("\n⚠️ 警告：发现完全匹配的品牌名称：")
                    for match in result["exact_matches"]:
                        output.append(f"- {match}")
                    output.append("\n该名称可能无法使用，建议选择其他名称。")
                elif result["has_similar_match"]:
                    output.append("\n⚠️ 警告：发现相似的品牌名称（长度相同且仅一个字母不同）：")
                    for match in result["similar_matches"]:
                        output.append(f"- {match}")
                    output.append("\n该名称可能无法使用，建议选择其他名称。")
                elif result["total_found"] > 15 and "WIPO" in result.get("search_source", []):
                    output.append(f"\n⚠️ 注意：WIPO查询到{result['total_found']}个结果，但只能显示15个，请仔细核查。")
                else:
                    output.append("\n✅ 未发现完全匹配或相似的品牌名称，但请仔细复核名称。")
        
        detailed_info[query_name] = "\n".join(output)
    
    return detailed_info

def format_summary(results: list[dict]) -> str:
    """格式化所有查询结果的摘要"""
    existing_names = []
    similar_names = []
    available_names = []
    warning_names = []
    error_names = []
    local_match_names = []  # 本地数据库匹配的列表
    
    for result in results:
        name = result["query_name"]
        
        # 优先检查本地数据库匹配
        if result.get("in_local_db", False):
            local_match_names.append(name)
        elif result["status"] == "error":
            error_names.append(f"{name}")
        elif result["has_exact_match"]:
            existing_names.append(name)
        elif result["has_similar_match"]:
            similar_names.append(name)
        elif result["total_found"] > 15 and "WIPO" in result.get("search_source", []):
            # 只有WIPO查询超过15个结果且没有完全或相似匹配时才提示需要注意
            warning_names.append(f"{name} (WIPO查询到{result['total_found']}个结果，但只能显示15个，请仔细核查)")
        else:
            available_names.append(name)
    
    summary = []
    if local_match_names:
        summary.append("😊 以下名称之前已经查询过啦：")
        summary.extend(f"- {name}" for name in local_match_names)
        summary.append("")
    
    if existing_names:
        summary.append("❌ 以下名称存在完全匹配：")
        summary.extend(f"- {name}" for name in existing_names)
        summary.append("")
    
    if similar_names:
        summary.append("❌ 以下名称存在相似匹配（长度相同且仅一个字母不同）：")
        summary.extend(f"- {name}" for name in similar_names)
        summary.append("")
    
    if available_names:
        summary.append("✅ 以下名称未查询到匹配或相近结果：")
        summary.extend(f"- {name}" for name in available_names)
        summary.append("")
    
    if warning_names:
        summary.append("🤔 需要注意的名称：")
        summary.extend(f"- {name}" for name in warning_names)
        summary.append("")
    
    if error_names:
        summary.append("❗ 查询出错的名称：")
        summary.extend(f"- {name}" for name in error_names)
    
    return "\n".join(summary)

def show_details(choice: str, detailed_info: dict) -> str:
    """显示选中名称的详细信息"""
    return detailed_info.get(choice, "请选择要查看的查询结果")

def process_query(names: str, nice_class: str, progress=gr.Progress()) -> tuple[str, gr.Dropdown, dict]:
    """处理查询请求"""
    global current_query
    lock_acquired = False
    
    try:
        # 检查是否有其他用户正在查询
        if current_query["is_querying"]:
            # 如果查询时间超过5分钟，认为是异常情况，重置锁
            if time.time() - current_query["start_time"] > 300:
                logger.warning("检测到异常的长时间查询，重置状态")
                reset_query_state()
            else:
                logger.info("其他用户正在查询，拒绝新的查询请求")
                return "有其他用户正在查询，请稍后再试", gr.Dropdown(choices=[]), {}
        
        # 尝试获取查询锁
        if not query_lock.acquire(blocking=False):
            logger.info("无法获取查询锁，可能有其他用户正在查询")
            return "有其他用户正在查询，请稍后再试", gr.Dropdown(choices=[]), {}
        
        lock_acquired = True
        logger.info("成功获取查询锁")
        
        # 设置查询状态
        current_query["is_querying"] = True
        current_query["start_time"] = time.time()
        
        # 处理查询请求
        name_list = parse_input_names(names)
        if not name_list:
            return "请输入要查询的名称", gr.Dropdown(choices=[]), {}
        
        if len(name_list) > 100:
            return "为避免服务器压力，每次最多查询100个名称", gr.Dropdown(choices=[]), {}
        
        total = len(name_list)
        valid_names = []
        results = []
        
        # 验证输入
        for i, name in enumerate(name_list, 1):
            is_valid, validated_name = validate_name(name)
            if not is_valid:
                results.append({
                    "query_name": name,
                    "status": "error",
                    "error_message": validated_name,
                    "brands": [],
                    "total_found": 0,
                    "total_displayed": 0,
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": []
                })
            else:
                valid_names.append(validated_name)
        
        if valid_names:
            # 查询每个名称
            for i, name in enumerate(valid_names, 1):
                progress(i/total, desc=f"正在查询第 {i} 个，共 {total} 个")
                result = checker.check_trademark(name, nice_class)
                results.append(result)
        
        detailed_info = format_detailed_results(results)
        dropdown_choices = list(detailed_info.keys())
        
        if all(result["status"] == "error" for result in results):
            error_msg = "所有查询都失败了，可能网络问题或服务器故障，请稍后重试"
            return error_msg, gr.Dropdown(choices=[]), {}
        
        return (
            format_summary(results),
            gr.Dropdown(choices=dropdown_choices, value=dropdown_choices[0] if dropdown_choices else None),
            detailed_info
        )
        
    except Exception as e:
        logger.error(f"查询过程发生异常: {str(e)}", exc_info=True)
        error_msg = str(e)
        if "net::" in error_msg:
            error_msg = "网络连接失败，请检查网络连接"
        elif "Target closed" in error_msg:
            error_msg = "浏览器连接已断开，请重试"
        elif "timeout" in error_msg.lower():
            error_msg = "查询超时，请稍后重试"
        elif "asyncio loop" in error_msg.lower():
            error_msg = "系统繁忙，请稍后重试"
        
        return f"查询过程中出错: {error_msg}", gr.Dropdown(choices=[]), {}
        
    finally:
        # 确保在所有情况下都重置状态并释放锁
        if lock_acquired:
            try:
                reset_query_state()
                query_lock.release()
                logger.info("查询锁已释放")
            except Exception as e:
                logger.error(f"释放查询锁时发生错误: {str(e)}", exc_info=True)

# 创建Gradio界面
with gr.Blocks() as demo:
    with gr.Tabs():
        with gr.Tab("商标查询 🔍"):
            gr.Markdown("""
            # 🤖 商标名称查询工具
            
            **使用说明：**
            1. 在下方输入框中输入要查询的名称（每行1个）
            2. 由于 WIPO 服务器位于欧洲，部分查询可能较慢
            """)
            
            with gr.Column():
                input_names = gr.Textbox(
                    label="输入要查询的商标名称（每行一个）",
                    placeholder="例如：\nmonica\nnova\njohn",
                    lines=5
                )
                region = gr.Radio(
                    choices=["美国"],
                    value="美国",
                    label="选择查询区域 🌍"
                )
                nice_class = gr.Radio(
                    choices=["14", "20", "21"],
                    value="20",
                    label="选择商标类别 📋",
                    info="14类-贵重金属及合金等；20类-家具镜子相框等；21类-家庭或厨房用具及容器等"
                )
                submit_btn = gr.Button("开始查询 🚀", interactive=True)
            
            with gr.Row():
                summary_output = gr.Textbox(label="查询结果摘要 📊", lines=10)
                with gr.Column():
                    name_dropdown = gr.Dropdown(
                        label="选择要查看详情的名称 👇",
                        choices=[],
                        value=None,
                        interactive=True
                    )
                    detailed_output = gr.Textbox(label="详细结果 📝", lines=15)
            
            gr.Examples(
                examples=[
"""monica
nova
john"""],
                inputs=input_names
            )
            
        with gr.Tab("工具说明 📖"):
            # 读取外部Markdown文件
            with open('rules.md', 'r', encoding='utf-8') as f:
                rules_content = f.read()
            gr.Markdown(rules_content)
    
    # 存储详细信息的状态
    detailed_info_state = gr.State({})
    
    # 设置查询按钮点击事件
    submit_btn.click(
        fn=lambda: gr.Button(value="查询中...", interactive=False),
        outputs=submit_btn,
        queue=False
    ).then(
        fn=process_query,
        inputs=[input_names, nice_class],
        outputs=[summary_output, name_dropdown, detailed_info_state],
        api_name="query"
    ).then(
        fn=lambda: gr.Button(value="开始查询 🚀", interactive=True),
        outputs=submit_btn,
        queue=False
    )
    
    # 设置下拉选单变化事件
    name_dropdown.change(
        fn=show_details,
        inputs=[name_dropdown, detailed_info_state],
        outputs=detailed_output
    )

if __name__ == "__main__":
    # 启动服务器
    demo.queue(max_size=10).launch(
        server_name="127.0.0.1",  # 只监听本地地址
        server_port=3000,         # 使用3000端口
        show_error=True
    )