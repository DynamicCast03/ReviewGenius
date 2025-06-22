import os
import time
from flask import (
    Flask,
    request,
    Response,
    render_template,
    jsonify,
)
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from filter import sanitizer

app = Flask(__name__)

# 配置上传设置
UPLOAD_FOLDER = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB限制
app.config["UPLOAD_EXTENSIONS"] = [
    ".pdf",
    ".docx",
    ".txt",
    ".pptx",
    ".doc",
    ".jpg",
    ".png",
]  # 支持的文件类型
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# 创建必要目录
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def process_files(
    uploaded_files: list[FileStorage], user_text: str, question_settings: dict
):
    """处理上传的多个文件并生成试卷内容"""
    try:
        # 确保上传目录存在
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        saved_files = []  # 处理上传文件后实际文件
        # 保存所有文件
        for uploaded_file in uploaded_files:
            if uploaded_file.filename == "":
                continue

            # 使用安全文件名
            filename = secure_filename(uploaded_file.filename)
            input_filename = os.path.join(UPLOAD_FOLDER, filename)

            # 保存文件并记录
            uploaded_file.save(input_filename)
            saved_files.append(filename)
            print(f"✅ 文件已保存: {input_filename}")

        # 生成试卷内容 - 这里使用question_settings参数
        preview_content = (
            f"根据您的需求生成的试卷预览：\n\n"
            f"上传了 {len(saved_files)} 个文件: {', '.join(saved_files)}\n"
            f"用户需求: {user_text}\n"
            f"题型设置: {question_settings}\n\n"
            "试卷题目：\n"
        )

        # 添加试题（示例，实际应基于question_settings生成）
        questions = [
            # 生成的题目，示例如下
            "1. (选择题) 在直角三角形中，斜边的平方等于两直角边的平方和，这被称为：\n   A. 勾股定理  B. 毕达哥拉斯定理  C. 以上都是\n\n",
            "2. (填空题) 中国古代数学著作《九章算术》的作者是______。\n\n",
            "3. (简答题) 请解释牛顿第一定律的内容及其在现实生活中的应用。\n\n",
            "4. (选择题) 下列哪个元素是惰性气体？\n   A. 氧  B. 氦  C. 氮  D. 碳\n\n",
            "5. (计算题) 已知圆的半径为5cm，求其周长和面积。\n\n",
            "6. (选择题) 以下哪个不是面向对象编程的特性？\n   A. 封装  B. 继承  C. 多态  D. 并发\n\n",
            "7. (填空题) DNA的双螺旋结构是由______和______发现的。\n\n",
            "8. (简答题) 请简述第二次世界大战的主要起因和结果。\n\n",
        ]  # ai生成返回的试卷内容添加至此

        # 返回预览内容和试题列表
        return preview_content, questions

    except Exception as e:
        print(f"❌ 文件处理错误: {str(e)}")
        raise  # 重新抛出异常以便在调用处处理


@app.route("/")
def index():
    return render_template("./interface.html")


@app.route("/api/process", methods=["POST"])
def generate_exam():
    # 获取上传的文件列表
    uploaded_files = []
    # 收集所有文件字段 (file0, file1, ...)
    for key in request.files:
        if key.startswith("file"):
            uploaded_files.append(request.files[key])

    # 获取表单数据
    user_text = request.form.get("user_input", "")
    user_text = sanitizer.sanitize(user_text)

    # 获取题型设置
    question_settings = {
        "choice": {
            "count": request.form.get("choice_count", "0"),
            "score": request.form.get("choice_score", "0"),
        },
        "blank": {
            "count": request.form.get("blank_count", "0"),
            "score": request.form.get("blank_score", "0"),
        },
        "short": {
            "count": request.form.get("short_count", "0"),
            "score": request.form.get("short_score", "0"),
        },
        "calc": {
            "count": request.form.get("calc_count", "0"),
            "score": request.form.get("calc_score", "0"),
        },
    }

    # 检查是否有有效文件
    valid_files = [f for f in uploaded_files if f.filename != ""]
    if not valid_files:
        return jsonify({"error": "未选择有效文件"}), 400

    # 验证所有文件的扩展名
    for file in valid_files:
        filename = file.filename
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in app.config["UPLOAD_EXTENSIONS"]:
            return (
                jsonify(
                    {
                        "error": f"不支持的文件类型: {filename}",
                        "allowed": app.config["UPLOAD_EXTENSIONS"],
                    }
                ),
                400,
            )

    # 处理文件并生成试卷内容
    try:
        preview_content, questions = process_files(
            valid_files, user_text, question_settings
        )

        # 流式输出生成器
        def generate_stream():
            # 逐题输出
            for i, question in enumerate(questions):
                # 模拟AI思考时间
                time.sleep(0.1)  # 减少等待时间

                # 逐字输出问题
                for char in question:
                    yield char
                    time.sleep(0.002)  # 加快输出速度

        return Response(generate_stream(), mimetype="text/plain")

    except Exception as e:
        error_msg = f"处理文件时出错: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    # 确保目录存在
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # 检查目录权限
    print(f"上传目录: {os.path.abspath(UPLOAD_FOLDER)}")
    print(f"当前工作目录: {os.getcwd()}")

    # 运行应用
    app.run(host="0.0.0.0", port=5000, debug=True)
