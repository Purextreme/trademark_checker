# 程序模块

1. app.py 是主程序，负责启动浏览器，并调用其他模块
2. validate_name.py 是名称验证模块，负责验证用户输入的名称是否合法
3. main_checker.py 是主查询模块，负责查询商标信息
3. tmdn_name_checker.py 是tmdn欧盟商标系统查询模块
4. wipo_name_checker.py 是WIPO联合国商标系统查询模块
5. todo.md 是用户编写的需求文档，你需要根据需求文档编写代码
6. checked_name.csv 是本地数据库，用于记录已经查询过的名称

# 程序逻辑

1. app.py 启动一个gradio 界面，查询区域有“美国”或者“美国+欧洲”两个选项，商标类别则有“14”“20”“21”三个选项
2. 用户输入名称，点击查询按钮
3. validate_name.py 验证名称是否合法，用户输入的只能是1个单词，在验证前需要去除前后的空格（若有的话），不能输入符号或者多个单词，例如#￥%&*等，如果用户输入了不合法的名称，则需要提示用户输入的名称不合法
4. main_checker.py 调用查询模块查询商标信息，并需要对结果进行分类，例如是否查询到结果，或者结果属于哪种情况（参见查询结果分类），查询的顺序是先进行checked_name.csv 本地查询，如果本地查询到结果，则返回“以下名称之前已经查询过啦",本地查询需要全字匹配，如果未查询到结果，则继续查询 tmdn 系统，如果查询到完全匹配，则返回“存在完全匹配”分类，如果未查询到完全匹配，则继续查询wipo系统，如果查询到完全匹配，则返回“存在完全匹配”分类，如果未查询到完全匹配，则返回“未查询到匹配结果”分类
5. tmdn_name_checker.py 查询tmdn欧盟商标系统注册信息，是否存在和用户相同的注册名称
6. wipo_name_checker.py 查询WIPO联合国商标系统注册信息，是否存在和用户相同的注册名称
7. 将查询结果输出到gradio界面

# 匹配规则

1. 本地匹配：本地数据库中每一行都进行全字匹配以确定是否存在相同的名称，需要注意的是，CSV中包含三个类别，分别是"使用词汇","风险国家","类别",风险国家类别可以忽略，但是需要注意类别的匹配，例如用户输入的是“apple",查询类别为14，但是本地数据库中查询到的是“apple”，类别为20，则匹配失败，如果查询到的是“apple”，类别为14，则匹配成功，只考虑同类别情况
2. tmdn匹配：对tmdn找到的名称进行匹配，但是以单词为单位匹配，例如，如果用户输入的是“apple”，tmdn找到的名称是“apple pie”或“apple”，都算匹配成功，如果找到的是 appled，算匹配失败，因为它们从单词上不匹配
3. wipo匹配：规则和tmdn匹配规则相同
4. 按 本地匹配 -> tmdn匹配 -> wipo匹配 的顺序进行匹配，如果匹配成功，则停止匹配，如果匹配失败，则继续进行下一个匹配，也就是说前面如果匹配到，则不会继续匹配后面的系统
5. 特别规则：由于wipo 返回的结果有限，例如用户查询 apple，wipo 显示找到了40个结果，由于网页抓取本身的限制只会返回 15个结果，如果这15个结果都没找到完全匹配，则应该返回“需要注意”分类，而不是“未查询到匹配结果”分类，此时可能存在完全匹配的名称，但是由于wipo 返回的结果有限，因此需要提示用户“需要注意”
6. 如果某个单词在查询中出错，则该名称的查询结果为“查询出错”类别

# 查询结果分类

1. 😊 以下名称之前已经查询过啦：在本地数据库中找到完全相同的名称
2. ❌ 存在完全匹配：名称已被注册，建议选择其他名称
3. 🤔 需要注意：由于返回限制未找到，但需要进一步审查
4. ✅ 未查询到匹配结果：该名称可能可用
5. ❗ 查询出错：查询过程中出现错误