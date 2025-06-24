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


def grade_multiple_choice_comment(question, user_answer, is_correct, api_key, temperature=0.7):
    """
    使用LLM为选择题生成反馈评语。
    """
    prompt = _get_grading_prompt(question, user_answer, is_correct)
    messages = [{"role": "user", "content": prompt}]

    try:
        # 为简单起见，使用非流式调用
        response = siliconflow_client.invoke_llm(
            api_key=api_key,
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            stream=False,
            temperature=temperature,
        )
        
        # invoke_llm在非流式模式下直接返回内容字符串
        full_response = response
        # 响应应该是一个JSON对象字符串，如 {"feedback": "..."}
        parsed_json = json.loads(full_response)
        return parsed_json.get("feedback", "AI评语生成失败。")

    except Exception as e:
        print(f"获取选择题评语时出错: {e}")
        return "因发生错误，无法生成AI评语。"


def grade_exam_stream(questions, user_answers, api_key, temperature=0.7):
    """
    批改整份试卷，为每道题的批改过程生成事件。
    这是一个生成器函数。
    """
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

                # 从LLM获取评语 (非流式)
                feedback = grade_multiple_choice_comment(
                    question, user_answer, is_correct, api_key, temperature
                )

                # 直接生成最终结果事件
                final_data = {"score": score, "feedback": feedback}
                yield json.dumps(
                    {"type": "end", "question_index": i, "data": final_data}
                ) + "\\n"

            elif q_type in ["fill_in_the_blank", "short_answer"]:
                prompt = _get_grading_prompt(question, user_answer)
                messages = [{"role": "user", "content": prompt}]

                llm_stream = siliconflow_client.invoke_llm(
                    api_key=api_key,
                    model="Qwen/Qwen2.5-72B-Instruct",
                    messages=messages,
                    stream=True,
                    temperature=temperature,
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
