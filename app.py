import gradio as gr
from validator import validate_name
from WIPO_name_checker import NameChecker
import time
import webbrowser
from threading import Timer
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def open_browser():
    webbrowser.open('http://127.0.0.1:7860')

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
            output.append(f"查询出错：{result['error_message']}")
        else:
            output.append(f"搜索结果状态: {result['status_message']}")
            
            if result["total_found"] > 0:
                output.append("\n找到的品牌:")
                for i, name in enumerate(result["brands"], 1):
                    output.append(f"{i}. {name}")
                
                if result["has_exact_match"]:
                    output.append("\n⚠️ 警告：发现完全匹配的品牌名称：")
                    for match in result["exact_matches"]:
                        output.append(f"- {match}")
                    output.append("\n该名称可能无法使用，建议选择其他名称。")
                elif result["total_displayed"] != result["total_found"]:
                    output.append(f"\n⚠️ 注意：总共有{result['total_found']}个结果，但只显示了{result['total_displayed']}个。")
                    output.append("建议手动复核完整结果。")
                else:
                    output.append("\n✅ 未发现完全匹配的品牌名称，但请仔细审查相似名称。")
        
        detailed_info[query_name] = "\n".join(output)
    
    return detailed_info

def format_summary(results: list[dict]) -> str:
    """格式化所有查询结果的摘要"""
    existing_names = []
    available_names = []
    warning_names = []
    error_names = []
    
    for result in results:
        name = result["query_name"]
        if result["status"] == "error":
            error_names.append(name)
        elif result["has_exact_match"]:
            existing_names.append(name)
        elif result["total_displayed"] != result["total_found"]:
            warning_names.append(f"{name} (查询到{result['total_found']}个结果，但仅显示{result['total_displayed']}个，需手动复核)")
        elif result["total_found"] == 0:
            available_names.append(name)
        else:
            warning_names.append(f"{name} (找到{result['total_found']}个相关结果，请查看详情)")
    
    summary = []
    if existing_names:
        summary.append("❌ 以下名称已存在完全匹配：")
        summary.extend(f"- {name}" for name in existing_names)
        summary.append("")
    
    if available_names:
        summary.append("✅ 以下名称未查询到相关结果：")
        summary.extend(f"- {name}" for name in available_names)
        summary.append("")
    
    if warning_names:
        summary.append("⚠️ 需要注意的名称：")
        summary.extend(f"- {name}" for name in warning_names)
        summary.append("")
    
    if error_names:
        summary.append("❗ 查询出错的名称：")
        summary.extend(f"- {name}" for name in error_names)
    
    return "\n".join(summary)

def process_query(names: str, progress=gr.Progress()) -> tuple[str, gr.Dropdown, dict]:
    logging.info("开始解析输入的名称")
    name_list = parse_input_names(names)
    if not name_list:
        return "请输入要查询的名称", gr.Dropdown(choices=[]), {}
    
    if len(name_list) > 10:
        return "为避免服务器压力，每次最多查询10个名称", gr.Dropdown(choices=[]), {}
    
    try:
        total = len(name_list)
        # 首先验证所有输入
        valid_names = []
        results = []
        
        for i, name in enumerate(name_list, 1):
            progress(i/total, desc=f"验证输入: {name}")
            is_valid, validated_name = validate_name(name)
            if not is_valid:
                logging.warning(f"名称验证失败: {name} - {validated_name}")
                results.append({
                    "query_name": name,
                    "status": "error",
                    "error_message": validated_name
                })
            else:
                valid_names.append(validated_name)
        
        if valid_names:
            progress(0.3, desc="正在查询，请稍候...")
            # 执行查询（这会创建新的浏览器实例，查询完成后自动清理）
            query_results = NameChecker.check_names(valid_names)
            results.extend(query_results)
        
        logging.info("开始生成查询报告")
        detailed_info = format_detailed_results(results)
        dropdown_choices = list(detailed_info.keys())
        logging.info("查询任务完成")
        
        # 检查是否所有查询都失败了
        all_failed = all(result["status"] == "error" for result in results)
        if all_failed:
            error_msg = "所有查询都失败了，可能是网络问题或服务器故障，请稍后重试"
            logging.error(error_msg)
            return error_msg, gr.Dropdown(choices=[]), {}
        
        return (
            format_summary(results),
            gr.Dropdown(choices=dropdown_choices, value=dropdown_choices[0] if dropdown_choices else None),
            detailed_info
        )
    except Exception as e:
        error_msg = str(e)
        if "net::" in error_msg:
            error_msg = "网络连接失败，请检查网络连接"
        elif "Target closed" in error_msg:
            error_msg = "浏览器连接已断开，请重试"
        elif "timeout" in error_msg.lower():
            error_msg = "查询超时，请稍后重试"
        elif "asyncio loop" in error_msg.lower():
            error_msg = "系统繁忙，请稍后重试"
        
        logging.error(f"处理查询时出错: {error_msg}")
        return f"查询过程中出错: {error_msg}", gr.Dropdown(choices=[]), {}

def show_details(choice: str, detailed_info: dict) -> str:
    """显示选中名称��详细信息"""
    return detailed_info.get(choice, "请选择要查看的查询结果")

# 创建Gradio界面
with gr.Blocks() as demo:
    gr.Markdown("""
    # 商标名称查询工具
    
    这个工具可以帮助您查询商标名称是否已被注册。
    
    **使用说明：**
    1. 在下方输入框中输入要查询的名称（每行一个）
    2. 名称只能包含英文字母
    3. 不支持数字、空格和特殊字符
    4. 系统会检查完全匹配的情况
    """)
    
    with gr.Row():
        input_names = gr.Textbox(
            label="输入要查询的商标名称（每行一个）",
            placeholder="例如：\nmonica\nnova\njohn",
            lines=5
        )
    
    with gr.Row():
        summary_output = gr.Textbox(label="查询结果摘要", lines=10)
        with gr.Column():
            name_dropdown = gr.Dropdown(
                label="选择要查看详情的名称",
                choices=[],
                value=None,
                interactive=True
            )
            detailed_output = gr.Textbox(label="详细结果", lines=15)
    
    submit_btn = gr.Button("查询")
    
    # 存储详细信息的状态
    detailed_info_state = gr.State({})
    
    # 设置查询按钮点击事件
    submit_btn.click(
        fn=process_query,
        inputs=[input_names],
        outputs=[summary_output, name_dropdown, detailed_info_state]
    )
    
    # 设置下拉选单变化事件
    name_dropdown.change(
        fn=show_details,
        inputs=[name_dropdown, detailed_info_state],
        outputs=detailed_output
    )
    
    gr.Examples(
        examples=[
"""monica
nova
john"""],
        inputs=input_names
    )

if __name__ == "__main__":
    # 启动服务器并自动打开浏览器
    Timer(2, open_browser).start()
    demo.launch()