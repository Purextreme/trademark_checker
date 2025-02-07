import streamlit as st
import logging
from logging.handlers import RotatingFileHandler
import os
from validator import validate_name
from main_checker import TrademarkChecker
from config import NICE_CLASS_MAP, QUERY_PARAMS
from typing import Union, List

def setup_logging():
    """配置日志系统"""
    # 清空现有日志文件
    with open('debug.log', 'w', encoding='utf-8') as f:
        f.write('')
    
    # 移除所有现有的处理器
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # 配置新的日志处理器
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(message)s',
        datefmt='%H:%M:%S',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('debug.log', mode='w', encoding='utf-8')
        ]
    )

# 使用 Streamlit 的会话状态来存储全局变量
if 'initialized' not in st.session_state:
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 实例化 TrademarkChecker
    st.session_state.checker = TrademarkChecker()
    st.session_state.initialized = True

def parse_input_names(text: str) -> list[str]:
    """解析输入的多个名称"""
    return [name.strip() for name in text.split('\n') if name.strip()]

def format_detailed_results(results: list[dict]) -> dict[str, str]:
    """格式化查询结果的详细信息"""
    detailed_info = {}
    
    for result in results:
        query_name = result["query_name"]
        output = []
        
        # 添加查询参数信息
        output.append(f"🔍 查询参数:")
        output.append(f"- 查询名称: {query_name}")
        output.append(f"- 商标类别: {result['search_params']['nice_class']}")
        output.append(f"- 查询区域: {result['search_params']['region']}")
        output.append("")
        
        # 添加查询状态
        if result["status"] == "error":
            output.append(f"❌ 查询失败: {result.get('error_message', '未知错误')}")
        else:
            # 添加数据来源
            output.append(f"📊 数据来源: {', '.join(result['search_source'])}")
            
            # 添加查询结果
            if result.get("in_local_db", False):
                output.append("✨ 在本地数据库中找到匹配")
            elif result["has_exact_match"]:
                output.append("⚠️ 发现完全匹配的商标:")
                for match in result["exact_matches"]:
                    output.append(f"  - {match}")
            else:
                output.append(f"📝 找到 {result['total_found']} 个相关商标:")
                for brand in result["brands"]:
                    output.append(f"  - {brand}")
        
        detailed_info[query_name] = "\n".join(output)
    
    return detailed_info

def format_summary(results: list[dict]) -> str:
    """格式化所有查询结果的摘要"""
    existing_names = []
    available_names = []
    error_names = []
    local_match_names = []
    
    for result in results:
        name = result["query_name"]
        
        if result.get("in_local_db", False):
            local_match_names.append(name)
        elif result["status"] == "error":
            error_names.append(f"{name}")
        elif result["has_exact_match"]:
            existing_names.append(name)
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
    
    if available_names:
        summary.append("✅ 以下名称未查询到匹配结果：")
        summary.extend(f"- {name}" for name in available_names)
        summary.append("")
    
    if error_names:
        summary.append("❗ 查询出错的名称：")
        summary.extend(f"- {name}" for name in error_names)
    
    return "\n".join(summary)

def process_query(names: str, regions: Union[str, List[str]], nice_classes: Union[str, List[str]]) -> tuple[str, list[str], dict]:
    """处理查询请求
    Args:
        names: 要查询的商标名称（每行一个）
        regions: 查询区域（可以是单个区域字符串或区域列表）
        nice_classes: 商标类别（可以是单个类别字符串或类别列表）
    """
    try:
        # 每次查询前重新设置日志
        setup_logging()
        
        name_list = parse_input_names(names)
        if not name_list:
            return "请输入要查询的名称", [], {}
        
        if len(name_list) > QUERY_PARAMS["max_names_per_query"]:
            return "为避免服务器压力，每次最多查询100个名称", [], {}
        
        valid_names = []
        results = []
        
        # 验证输入
        for name in name_list:
            is_valid, validated_name = validate_name(name)
            if not is_valid:
                results.append({
                    "query_name": name,
                    "status": "error",
                    "error_message": f"输入格式错误: {validated_name}",
                    "brands": [],
                    "total_found": 0,
                    "has_exact_match": False,
                    "exact_matches": [],
                    "search_source": [],
                    "search_params": {
                        "region": ", ".join(regions) if isinstance(regions, list) else regions,
                        "nice_class": ", ".join(nice_classes) if isinstance(nice_classes, list) else nice_classes,
                        "status": "输入验证失败"
                    }
                })
            else:
                valid_names.append(validated_name)
        
        if not valid_names:
            return "所有输入的名称都不合法，请检查输入格式", [], {}
        
        # 查询每个名称
        with st.spinner('正在查询中...'):
            progress_bar = st.progress(0)
            for i, name in enumerate(valid_names):
                result = st.session_state.checker.check_trademark(name, nice_classes, regions)
                results.append(result)
                progress_bar.progress((i + 1) / len(valid_names))
        
        detailed_info = format_detailed_results(results)
        
        if all(result["status"] == "error" for result in results):
            return "所有查询都失败了，可能网络问题或服务器故障，请稍后重试", [], {}
        
        return format_summary(results), list(detailed_info.keys()), detailed_info
        
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
        
        return f"查询过程中出错: {error_msg}", [], {}

def main():
    st.set_page_config(
        page_title="商标名称查询工具",
        page_icon="🔍",
        layout="wide"
    )
    
    # 创建标签页
    tab1, tab2 = st.tabs(["查询工具 🔍", "使用说明 📖"])
    
    with tab1:
        st.title("🤖 商标名称查询工具")
        
        # 添加使用说明
        with st.expander("快速使用说明", expanded=False):
            st.markdown("""
            **使用说明：**
            1. 在下方输入框中输入要查询的名称（每行1个）
            2. 选择要查询的区域和商标类别（可多选）
            3. 点击查询按钮开始查询
            
            详细说明请查看右侧"使用说明"标签页
            """)
        
        # 创建两列布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # 输入区域
            input_names = st.text_area(
                "输入要查询的商标名称（每行一个）",
                placeholder="例如：\nmonica\nnova\njohn",
                height=150
            )
        
        with col2:
            # 选项区域
            st.markdown("### 查询选项")
            
            # 区域多选
            regions = st.multiselect(
                "选择查询区域 🌍",
                options=["美国", "英国", "欧盟"],
                default=["美国"],
                help="可以选择多个区域同时查询"
            )
            
            # 类别多选
            nice_classes = st.multiselect(
                "选择商标类别 📋",
                options=["14", "20", "21"],
                default=["20"],
                format_func=lambda x: f"{x} - {NICE_CLASS_MAP.get(x, '')}",
                help="可以选择多个类别同时查询"
            )
            
            # 添加验证
            if not regions:
                st.error("请至少选择一个查询区域")
            if not nice_classes:
                st.error("请至少选择一个商标类别")
        
        # 查询按钮
        button_disabled = not regions or not nice_classes
        if st.button(
            "开始查询 🚀",
            type="primary",
            use_container_width=True,
            disabled=button_disabled
        ):
            if not input_names.strip():
                st.error("请输入要查询的名称")
            else:
                # 传递所有选中的区域和类别
                summary, names, detailed_info = process_query(input_names, regions, nice_classes)
                # 保存查询结果到 session_state
                st.session_state.summary = summary
                st.session_state.names = names
                st.session_state.detailed_info = detailed_info
                # 设置默认选中的名称
                if names:
                    st.session_state.selected_name = names[0]
        
        # 显示查询结果（如果有）
        if hasattr(st.session_state, 'summary'):
            st.markdown("### 查询结果摘要 📊")
            st.markdown(st.session_state.summary)
            
            if st.session_state.names:
                st.markdown("### 详细结果 📝")
                selected_name = st.selectbox(
                    "选择要查看详情的名称 👇",
                    st.session_state.names,
                    key='name_selector'
                )
                
                # 始终显示详细信息
                st.text_area(
                    "详细信息",
                    value=st.session_state.detailed_info[selected_name],
                    height=300,
                    disabled=True
                )
    
    with tab2:
        st.title("📖 使用说明")
        
        # 读取并显示使用说明
        with open("rules.md", "r", encoding="utf-8") as f:
            rules_content = f.read()
        st.markdown(rules_content)

if __name__ == "__main__":
    main() 