# 商标名称查询工具说明 🔍

这个工具可以帮助您查询商标名称是否已被注册。

## 注意事项 ⚠️
- 每次最多可以查询100个名称

## 商标名称验证规则 📋
本系统对商标名称的验证包括以下几个方面：

### 1. 基本规则 ✨
- 商标名称需要是单个英文单词
- 只能包含英文字母（A-Z, a-z）
- 不能包含特殊字符（如 !@#$% 等）
- 如果输入时不小心带有前后空格，系统会自动处理，不用担心 😊

### 2. 查询顺序 🔄
系统会按照以下顺序进行查询：
1. 首先检查本地数据库（查看是否之前查询过）
2. 如果本地没有记录，则查询 TMDN 数据库
3. 如果 TMDN 没有找到匹配，继续查询 WIPO 数据库
4. 如果 TMDN 找到了匹配（完全或相似），则不再查询 WIPO

### 3. 本地数据库匹配规则 📝
本地数据库用于记录之前查询过的名称：
- 只检查完全相同的名称（去除首尾空格后）
- 不区分大小写
- 必须是完全相同的单词

例如：
- "nova" 和 "nova" 匹配
- "Nova" 和 "nova" 匹配（不区分大小写）
- " nova " 和 "nova" 匹配（忽略首尾空格）
- "nova red" 和 "nova" 不匹配（必须完全相同）

### 4. 在线数据库完全匹配规则 🎯
在 TMDN 和 WIPO 数据库中的完全匹配规则：
- 不区分大小写
- 忽略首尾空格
- 只要包含这个单词就算匹配
- 作为独立单词匹配（不匹配单词的一部分）

例如：
- "nova" 匹配 "nova"（完全相同）
- "nova" 匹配 "NOVA"（不区分大小写）
- "nova" 匹配 "nova red"（包含这个单词就算匹配）
- "nova" 匹配 "red nova blue"（包含这个单词就算匹配）
- "nova" 不匹配 "novation"（必须是独立单词）

### 6. 查询结果分类 📋
查询结果会被分为以下几类：
- 😊 以下名称之前已经查询过啦：在本地数据库中找到完全相同的名称
- ❌ 存在完全匹配：名称已被注册，建议选择其他名称
- 🤔 需要注意：由于返回限制未找到，但需要进一步审查
- ✅ 未查询到匹配或相近结果：该名称可能可用
- ❗ 查询出错：查询过程中出现错误