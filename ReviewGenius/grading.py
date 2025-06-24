import json
from openai import AuthenticationError
import prompt_manager
import siliconflow_client
from llm_json_parser import stream_json_with_events


def _get_grading_prompt(question, user_answer, is_correct=None):
    """
    准备用于批改的提示词，手动将复杂数据转换为JSON字符串以避免Jinja2版本问题。
    """
    prompt_question_data = question.copy()
    if 'options' in prompt_question_data:
        prompt_question_data['options'] = json.dumps(prompt_question_data.get('options'), ensure_ascii=False)
    
    prompt_question_data['answer'] = json.dumps(prompt_question_data.get('answer'), ensure_ascii=False)
    prompt_user_answer_data = json.dumps(user_answer, ensure_ascii=False)

    prompt_context = {
        "question": prompt_question_data,
        "user_answer": prompt_user_answer_data,
    }
    if is_correct is not None:
        prompt_context["is_correct"] = is_correct

    return prompt_manager.get_prompt("grading_prompt", **prompt_context)


def grade_exam_stream(questions, user_answers, api_key, temperature=0.7, enhanced_structured_output: bool = False):
    """
    批改整份试卷，为每道题的批改过程生成事件。
    这是一个生成器函数。
    """
    formatting_prompt = None
    if enhanced_structured_output:
        formatting_prompt = prompt_manager.get_prompt("grading_prompt_formatting")
        
    for i, (question, user_answer) in enumerate(zip(questions, user_answers)):
        q_type = question.get("question_type")

        # 为每道题的开始发送一个事件
        yield json.dumps({"type": "start", "question_index": i}) + "\\n"

        try:
            if q_type == "multiple_choice":
                # 本地判分
                correct_answer = question.get("answer")
                is_correct = user_answer == correct_answer
                score = question.get("score", 0) if is_correct else 0
                
                prompt = _get_grading_prompt(question, user_answer, is_correct)
                messages = [{"role": "user", "content": prompt}]

                llm_stream = siliconflow_client.invoke_llm(
                    api_key=api_key,
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=messages,
                    stream=True,
                    temperature=temperature,
                    enhanced_structured_output=enhanced_structured_output,
                    formatting_prompt=formatting_prompt,
                )

                event_stream = stream_json_with_events(llm_stream)
                
                for event in event_stream:
                    event["question_index"] = i
                    if event["type"] == "end":
                        # 注入本地判定的分数
                        event["data"]["score"] = score
                    yield json.dumps(event) + "\\n"

            elif q_type in ["fill_in_the_blank", "short_answer"]:
                prompt = _get_grading_prompt(question, user_answer)
                messages = [{"role": "user", "content": prompt}]

                llm_stream = siliconflow_client.invoke_llm(
                    api_key=api_key,
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=messages,
                    stream=True,
                    temperature=temperature,
                    enhanced_structured_output=enhanced_structured_output,
                    formatting_prompt=formatting_prompt,
                )

                # 使用事件生成器来处理JSON解析
                event_stream = stream_json_with_events(llm_stream)

                for event in event_stream:
                    # 为每个事件添加题目索引
                    event["question_index"] = i
                    yield json.dumps(event) + "\\n"

            else:
                # 处理未知题型
                error_data = {"score": 0, "feedback": "未知题型，无法批改。"}
                yield json.dumps(
                    {"type": "end", "question_index": i, "data": error_data}
                ) + "\\n"

        except AuthenticationError:
            yield json.dumps(
                {
                    "type": "error",
                    "question_index": i,
                    "error": "API Key 无效或已过期。",
                }
            ) + "\\n"
        except Exception as e:
            yield json.dumps(
                {
                    "type": "error",
                    "question_index": i,
                    "error": f"批改过程中发生错误: {str(e)}",
                }
            ) + "\\n"
