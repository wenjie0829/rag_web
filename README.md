智言知识库（RAG Knowledge Base）
📌 项目介绍
智言知识库是一款基于 RAG（Retrieval-Augmented Generation，检索增强生成）架构 的智能知识库问答系统。
用户可以上传个人文档，系统自动完成文档解析、文本切片、向量化处理，并结合大语言模型实现基于私有知识库的智能问答。
项目解决了传统大模型无法访问用户私有数据的问题，实现：
“让大模型基于自己的知识回答问题”
✨ 核心功能
1. 多格式文档上传
支持：
PDF
TXT
Markdown
DOCX
用户上传文件后，系统自动进行：
文件上传
    ↓
文本解析
    ↓
内容切片
    ↓
Embedding向量化
    ↓
建立知识索引

2. RAG智能问答
用户输入问题：
例如：
“这份文档主要讲了什么？”
系统流程：
用户问题
↓
问题Embedding
↓
向量相似度搜索
↓
召回相关文本片段
↓
构造Prompt
↓
大语言模型生成答案
↓
返回回答+引用来源

3. 知识库管理
支持：
文件列表管理
文件搜索
文件预览
删除文件
回收站管理

4. AI对话交互
提供类似 ChatGPT 的交互方式：
支持：
多轮上下文
历史问题
连续追问

🛠 技术架构
                 用户
                  |
                  |
              Vue3前端
                  |
              FastAPI接口
                  |
        --------------------
        |                  |
    文档处理模块        对话模块
        |
        |
    Embedding模型
        |
        |
    向量数据库
        |
        |
    大语言模型API
    
📷 项目截图（部分）
<img width="2880" height="1750" alt="image" src="https://github.com/user-attachments/assets/6c935aa2-07f0-404b-b701-746fa34e3a7c" />
<img width="2872" height="1600" alt="image" src="https://github.com/user-attachments/assets/cd666bed-6035-4374-9826-9a943cd8bd27" />
<img width="2880" height="1590" alt="image" src="https://github.com/user-attachments/assets/e4545d48-0387-411e-b3d0-28f168e69a14" />
<img width="1172" height="740" alt="image" src="https://github.com/user-attachments/assets/c4b86633-d54f-477d-af19-ea92d80d41c9" />
<img width="2876" height="1616" alt="image" src="https://github.com/user-attachments/assets/3957eda8-5007-4368-a1b8-18f98eb49eb6" />

🚀 项目部署
线上地址：
https://rag-production-18b0.up.railway.app/

📚 项目收获
通过本项目：
掌握RAG系统开发流程
理解LLM应用架构
熟悉AI应用前后端开发流程
积累大模型应用工程实践经验

🙋 联系我
邮箱：3535605546@qq.com
