import os
import json
from flask import (
    Flask,
    request,
    Response,
    render_template,
    jsonify,
)
from openai import AuthenticationError
from werkzeug.utils import secure_filename
from filter import sanitizer
import prompt_manager
import siliconflow_client
from llm_json_parser import stream_json_with_events
from question_types import Question # Import base class for validation

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

        # 合并简答题和计算题
        short_answer_count = int(request.form.get("short_count", "0")) + int(
            request.form.get("calc_count", "0")
        )

        question_settings = {
            "选择题": request.form.get("choice_count", "0"),
            "填空题": request.form.get("blank_count", "0"),
            "简答题": str(short_answer_count),
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

        def generate_question_stream():
            try:
                # 使用我们创建的客户端进行流式调用
                llm_stream = siliconflow_client.invoke_llm(
                    api_key=api_key,
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=messages,
                    stream=True,
                )
                
                # 使用新的事件生成器
                event_stream = stream_json_with_events(llm_stream)

                for event in event_stream:
                    if event["type"] == "end":
                        # 在结束后验证数据结构
                        try:
                            question_obj = Question.from_dict(event["data"])
                            # 将验证和转换后的数据放回事件中
                            event["data"] = question_obj.to_dict()
                        except (ValueError, KeyError) as e:
                            # 如果数据格式错误，可以跳过或发送一个错误事件
                            print(f"Skipping invalid question object: {e}, data: {event['data']}")
                            continue # 不发送这个 'end' 事件
                    
                    yield json.dumps(event) + "\\n"

            except AuthenticationError:
                yield json.dumps({"type": "error", "error": "API Key 无效或已过期，请检查您的输入。", "error_type": "authentication"}) + "\\n"
            except Exception as e:
                # 捕获其他流式过程中的错误
                yield json.dumps({"type": "error", "error": f"生成过程中发生错误: {str(e)}", "error_type": "generation"}) + "\\n"

        return Response(generate_question_stream(), mimetype="application/x-ndjson")

    except Exception as e:
        error_msg = f"处理时出错: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
