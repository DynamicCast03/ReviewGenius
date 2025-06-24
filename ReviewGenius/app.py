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
import grading # 导入评分模块

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
CONFIG_FILE = "config.json"
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.config["UPLOAD_EXTENSIONS"] = [".txt"]  # 仅支持txt
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "temperature": 1.0,
            "enhanced_structured_output": False
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        return default_config
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {
            "temperature": 1.0,
            "enhanced_structured_output": False
        }

def save_config(config_data):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4)

@app.route("/")
def index():
    config = load_config()
    return render_template("./interface.html", config=config)

@app.route("/api/settings", methods=["GET", "POST"])
def manage_settings():
    if request.method == "GET":
        return jsonify(load_config())
    
    if request.method == "POST":
        data = request.json
        config = load_config()
        config["temperature"] = float(data.get("temperature", config["temperature"]))
        config["enhanced_structured_output"] = bool(data.get("enhanced_structured_output", config["enhanced_structured_output"]))
        save_config(config)
        return jsonify({"message": "设置已保存", "config": config})

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
        
        config = load_config()
        temperature = config.get("temperature", 1.0)

        if not api_key:
            return jsonify({"error": "API Key缺失"}), 400

        # 合并简答题和计算题
        short_answer_count = int(request.form.get("short_count", "0")) + int(
            request.form.get("calc_count", "0")
        )

        question_settings = {
            "选择题": {
                "count": request.form.get("choice_count", "0"),
                "score": request.form.get("choice_score", "5"),
            },
            "填空题": {
                "count": request.form.get("blank_count", "0"),
                "score": request.form.get("blank_score", "5"),
            },
            "简答题": {
                "count": str(short_answer_count),
                "score": request.form.get("short_score", "10"),
            },
        }

        question_types_str = "、".join(
            [
                f"{k}{v['count']}道(每题{v['score']}分)"
                for k, v in question_settings.items()
                if int(v['count']) > 0
            ]
        )
        if not question_types_str:
            return jsonify({"error": "至少需要设置一种题型"}), 400

        document_content = file.read().decode("utf-8")

        scores_data = {
            "multiple_choice": question_settings["选择题"]["score"],
            "fill_in_the_blank": question_settings["填空题"]["score"],
            "short_answer": question_settings["简答题"]["score"],
        }

        # 1. 加载静态的格式化提示词
        formatting_instructions = prompt_manager.get_prompt("exam_generation_prompt_formatting")

        # 2. 渲染主提示词，注入所有动态内容和静态格式说明
        main_prompt = prompt_manager.get_prompt("exam_generation_prompt", document_content=document_content,
        user_requirement=user_text,
        question_types=question_types_str,
        formatting_instructions=formatting_instructions,
        scores=scores_data)
        
        messages = [{"role": "user", "content": main_prompt}]

        def generate_question_stream():
            try:
                # 检查是否启用增强模式
                config = load_config()
                enhanced_mode = config.get("enhanced_structured_output", False)

                # 使用我们创建的客户端进行流式调用
                llm_stream = siliconflow_client.invoke_llm(
                    api_key=api_key,
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=messages,
                    stream=not enhanced_mode, # 如果增强模式，第一次调用就不是流式
                    temperature=temperature,
                    enhanced_structured_output=enhanced_mode,
                    formatting_prompt=formatting_instructions if enhanced_mode else None
                )
                
                # 如果是增强模式，llm_stream已经是第二次调用的流，直接处理
                if enhanced_mode:
                    event_stream = stream_json_with_events(llm_stream)
                    for event in event_stream:
                        yield json.dumps(event) + "\\n"
                    return

                # 原有逻辑，处理非增强模式下的流
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


@app.route("/api/grade", methods=["POST"])
def grade_submission():
    try:
        data = request.get_json()
        questions = data.get("questions")
        user_answers = data.get("answers")
        api_key = data.get("api_key")
        
        config = load_config()
        temperature = config.get("temperature", 0.7)
        enhanced_mode = config.get("enhanced_structured_output", False)

        if not all([questions, user_answers, api_key]):
            return jsonify({"error": "缺少题目、答案或API Key"}), 400

        def generate_grade_stream():
            try:
                grading_stream = grading.grade_exam_stream(
                    questions, user_answers, api_key, temperature,
                    enhanced_structured_output=enhanced_mode
                )
                for event in grading_stream:
                    yield event
            except Exception as e:
                error_event = {
                    "type": "error",
                    "error": f"启动批改流失败: {str(e)}",
                }
                yield json.dumps(error_event) + "\\n"

        return Response(generate_grade_stream(), mimetype="application/x-ndjson")

    except Exception as e:
        error_msg = f"评分接口出错: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
