import os
from flask import (
    Flask,
    request,
    Response,
    render_template,
    jsonify,
)
from werkzeug.utils import secure_filename
from filter import sanitizer
import prompt_manager
import siliconflow_client

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_EXTENSIONS"] = [".txt"]  # 仅支持txt
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return render_template("./interface.html")


@app.route("/api/process", methods=["POST"])
def generate_exam():
    if "file0" not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    file = request.files["file0"]
    if file.filename == "":
        return jsonify({"error": "未选择文件"}), 400

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in app.config["UPLOAD_EXTENSIONS"]:
        return jsonify({"error": f"不支持的文件类型，请上传 {app.config['UPLOAD_EXTENSIONS']} 文件"}), 400

    try:
        user_text = request.form.get("user_input", "无特定要求")
        user_text = sanitizer.sanitize(user_text)
        api_key = request.form.get("api_key")

        if not api_key:
            return jsonify({"error": "API Key缺失"}), 400

        question_settings = {
            "选择题": request.form.get("choice_count", "0"),
            "填空题": request.form.get("blank_count", "0"),
            "简答题": request.form.get("short_count", "0"),
            "计算题": request.form.get("calc_count", "0"),
        }
        
        question_types_str = "、".join(
            [f"{k}{v}道" for k, v in question_settings.items() if int(v) > 0]
        )
        if not question_types_str:
            return jsonify({"error": "至少需要设置一种题型"}), 400

        document_content = file.read().decode("utf-8")

        prompt = prompt_manager.get_prompt(
            "exam_generation_prompt",
            document_content=document_content,
            user_requirement=user_text,
            question_types=question_types_str,
        )
        
        messages = [{"role": "user", "content": prompt}]

        # 使用我们创建的客户端进行流式调用
        llm_stream = siliconflow_client.invoke_llm(
            api_key=api_key,
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            stream=True,
        )

        return Response(llm_stream, mimetype="text/plain")

    except Exception as e:
        error_msg = f"处理时出错: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
