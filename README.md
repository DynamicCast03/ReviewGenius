# ReviewGenius

ReviewGenius 是一个智能试卷生成工具，可以根据您提供的学习资料（如 `.txt`, `.pdf`, `.pptx` 文件），利用大语言模型（LLM）自动生成多种题型的试卷，并支持自动批改和用户画像功能。

## 主要功能

- **多种文档格式支持**: 支持上传 `.txt`, `.pdf`, `.pptx` 格式的文档作为知识库。
- **灵活的题型配置**: 可自定义生成选择题、填空题和简答题的数量与分值。
- **AI 驱动**: 调用强大的大语言模型（基于 SiliconFlow 的 `Qwen/Qwen2.5-72B-Instruct`）生成高质量的试题。
- **智能批改与反馈**: 对生成的试卷进行作答后，系统可以自动批改并给出评分和作答评价。
- **个性化用户画像**: 根据用户的答题历史，自动生成和更新用户画像，以便后续生成更具针对性的题目。
- **一键导出**: 支持将生成的试卷和答案导出为 Markdown 格式，方便本地保存和查阅。

## 部署方案

### 1. 环境准备

- 安装 [Python 3.8+](https://www.python.org/downloads/)。
- (推荐) 创建并激活一个 Python 虚拟环境来隔离项目依赖。

  ```bash
  # 创建虚拟环境
  python -m venv venv

  # 激活虚拟环境 (Windows)
  .\venv\Scripts\activate

  # 激活虚拟环境 (macOS/Linux)
  source venv/bin/activate
  ```

### 2. 安装依赖

克隆本项目到本地，然后进入项目目录，通过 `pip` 安装所有必需的库。

```bash
git clone https://github.com/DynamicCast03/ReviewGenius.git
cd ReviewGenius
pip install -r requirements.txt
```

### 3. 获取 API Key

本应用需要调用 SiliconFlow 提供的云端大模型服务，因此您需要一个有效的 API Key。

请访问 [SiliconFlow 官方网站](https://www.siliconflow.cn/) 注册并获取您的 API Key。

### 4. 启动应用

在项目根目录下运行以下命令来启动后端服务：

```bash
python app.py
```

服务启动后，您会看到类似以下的输出，表明应用正在 `5000` 端口上运行：

```
 * Serving Flask app 'app'
 * Debug mode: on
INFO:werkzeug:[31m[1mWARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.[0m
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:5000
 * Running on http://<your-local-ip>:5000
INFO:werkzeug:Press CTRL+C to quit
```

### 5. 使用方法

1.  打开浏览器并访问 `http://127.0.0.1:5000`。
2.  在页面的 "API Key" 输入框中填入您从 SiliconFlow 获取的 API Key。
3.  通过 "上传知识库" 区域上传您的学习资料文件。
4.  在 "题型设置" 部分，根据需要设置选择题、填空题、简答题的数量和分值。
5.  点击 "开始生成试卷" 按钮，AI 将开始根据您的文档和要求出题。
6.  生成完成后，您可以在页面上直接答题或将试卷导出为 Markdown 文件。

## 配置文件

应用首次启动或保存设置后，会在项目根目录创建一个 `config.json` 文件，用于保存您的偏好设置。

- `temperature`: 控制 AI 模型输出的随机性，值越高，输出越具创造性；值越低，输出越稳定。
- `user_profile`: 自动生成的用户画像文本。
- `user_profile_enabled`: 是否启用用户画像功能。

您可以直接修改此文件，也可以通过应用界面的 "高级设置" 进行更改。 