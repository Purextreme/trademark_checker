import gradio as gr
from validator import validate_name
from main_checker import TrademarkChecker
import time
import webbrowser
from threading import Timer

# 实例化 TrademarkChecker
checker = TrademarkChecker()

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
                    output.append("\n⚠️ 警告：发现相似的品牌名称（仅一个字母不同）：")
                    for match in result["similar_matches"]:
                        output.append(f"- {match}")
                    output.append("\n该名称可能无法使用，建议选择其他名称。")
                elif result["total_displayed"] != result["total_found"]:
                    output.append(f"\n⚠️ 注意：总共有{result['total_found']}个结果，但只显示了{result['total_displayed']}个。")
                    output.append("建议手动复核完整结果")
                else:
                    output.append("\n✅ 未发现完全匹配或相似的品牌名称，但请仔细审查相似名称。")
        
        detailed_info[query_name] = "\n".join(output)
    
    return detailed_info

def format_summary(results: list[dict]) -> str:
    """格式化所有查询结果的摘要"""
    existing_names = []
    similar_names = []
    available_names = []
    warning_names = []
    error_names = []
    
    for result in results:
        name = result["query_name"]
        
        if result["status"] == "error":
            error_detail = result.get("error_message", "未知错误")
            error_names.append(f"{name}")
        elif result["has_exact_match"]:
            existing_names.append(name)
        elif result["has_similar_match"]:
            similar_names.append(name)
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
    
    if similar_names:
        summary.append("❌ 以下名称已存在相似匹配（仅一个字母不同）：")
        summary.extend(f"- {name}" for name in similar_names)
        summary.append("")
    
    if available_names:
        summary.append("✅ 以下名称未查询到匹配或相近结果：")
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

def process_query(names: str, nice_class: str, progress=gr.Progress()) -> tuple[str, gr.Dropdown, dict]:
    name_list = parse_input_names(names)
    if not name_list:
        return "请输入要查询的名称", gr.Dropdown(choices=[]), {}
    
    if len(name_list) > 20:
        return "为避免服务器压力，每次最多查询20个名称", gr.Dropdown(choices=[]), {}
    
    try:
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

def show_details(choice: str, detailed_info: dict) -> str:
    """显示选名称的详细信息"""
    return detailed_info.get(choice, "请选择要查看的查询结果")

# 创建Gradio界面
with gr.Blocks() as demo:
    with gr.Tabs():
        with gr.Tab("商标查询 🔍"):
            gr.Markdown("""
            # 🤖 商标名称查询工具
            
            这个工具可以帮助您查询商标名称是否已被注册。
            
            **使用说明：**
            1. 在下方输入框中输入要查询的名称（每行一个）
            2. 商标名称需要是单个英文单词
            3. 每次最多可以查询20个名称（避免服务器压力）
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
                    info="14类-贵重金属及合金等；20类-家具镜子框等；21类-家庭或厨房用具及容器等"
                )
                submit_btn = gr.Button("开始查询 🚀")
            
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
            
        with gr.Tab("验证规则说明 📖"):
            # 读取外部Markdown文件
            with open('rules.md', 'r', encoding='utf-8') as f:
                rules_content = f.read()
            gr.Markdown(rules_content)
    
    # 存储详细信息的状态
    detailed_info_state = gr.State({})
    
    # 设置查询按钮点击事件
    submit_btn.click(
        fn=process_query,
        inputs=[input_names, nice_class],
        outputs=[summary_output, name_dropdown, detailed_info_state],
        api_name="query",
        concurrency_limit=1
    )
    
    # 设置下拉选单变化事件
    name_dropdown.change(
        fn=show_details,
        inputs=[name_dropdown, detailed_info_state],
        outputs=detailed_output
    )

if __name__ == "__main__":
    demo.queue(max_size=20).launch(
        server_name="0.0.0.0",
        root_path="/tc",
        show_error=True
    )