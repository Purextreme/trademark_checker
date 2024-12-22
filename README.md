# 商标名称查询工具 🔍

这是一个基于 Python 的商标名称查询工具，可以帮助用户检查商标名称在美国市场的注册状态。

## 功能特点 ✨

- 支持多个商标名称批量查询
- 同时查询多个数据源（TMDN、WIPO）
- 检查完全匹配和相似匹配
- 支持多个商标类别（14类、20类、21类）
- 稳定可靠的查询机制
- 友好的 Web 界面

## 技术栈 🛠️

- Python 3.10+
- Gradio (Web 界面)
- Playwright (网页自动化)
- FastAPI (后端服务)
- Nginx (反向代理)

## 安装说明 📦

1. 克隆仓库：
```bash
git clone [repository-url]
cd trademark_checker
```

2. 创建虚拟环境：
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖：
```bash
pip install -r requirements.txt
playwright install chromium
```

4. 运行程序：
```bash
python3 app.py
```

## 使用说明 📝

1. 在输入框中输入要查询的商标名称（每行一个）
2. 选择商标类别（14/20/21类）
3. 点击"开始查询"按钮
4. 等待查询结果（WIPO ��询可能需要约30秒）
5. 查看查询结果和详细信息

## 注意事项 ⚠️

- 每次最多可查询20个名称
- 商标名称必须是单个英文单词
- 同一时间只允许一个查询任务运行
- WIPO 服务器响应可能较慢，请耐心等待

## 查询结果说明 📋

- ❌ 完全匹配：名称已被注册
- ❌ 相似匹配：与已注册商标仅一字母之差
- ⚠️ 需要注意：发现相关商标
- ✅ 可用：未发现匹配或相近商标
- ❗ 查询出错：查询过程中出现错误

## 开发说明 👨‍💻

- 主程序入口：`app.py`
- 商标检查逻辑：`main_checker.py`
- WIPO 查询：`WIPO_name_checker.py`
- TMDN 查询：`tmdn_name_checker.py`
- 名称验证：`validator.py`

## 许可证 📄

MIT License 