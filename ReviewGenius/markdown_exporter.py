from typing import List, Dict, Any

def _format_question(question: Dict[str, Any], question_number: int) -> str:
    """Formats a single question into Markdown."""
    q_type_map = {
        "multiple_choice": "选择题",
        "fill_in_the_blank": "填空题",
        "short_answer": "简答题",
    }
    question_type = q_type_map.get(question.get("question_type"), "未知题型")
    score = question.get("score", 0)
    
    # 替换题目中的填空符为 Markdown 的下划线，以获得更好的视觉效果
    stem = question.get('stem', '').replace('___', '____')

    md = f"### {question_number}. {question_type} ({score}分)\n\n"
    md += f"{stem}\n\n"
    
    if question.get('question_type') == 'multiple_choice' and 'options' in question:
        for key, value in question['options'].items():
            md += f"- {key}. {value}\n"
        md += "\n"
        
    return md

def _format_answer(question: Dict[str, Any]) -> str:
    """Formats the answer and explanation for a single question."""
    answer = question.get('answer')
    explanation = question.get('explanation')
    
    md = "**答案：**\n"
    if isinstance(answer, list):
        # 将列表答案格式化为更易读的形式
        md += "、".join(map(str, answer)) + "\n\n"
    else:
        md += f"{answer}\n\n"
        
    if explanation:
        md += f"**解析：**\n{explanation}\n\n"
        
    return md

def export_to_markdown(questions: List[Dict[str, Any]], answers_placement: str = 'inline') -> str:
    """
    将题目列表导出为 Markdown 格式的字符串。

    :param questions: 包含题目信息的字典列表。
    :param answers_placement: 答案位置, 'inline' 或 'end'。
                              'inline' 表示答案紧跟在每道题后面。
                              'end' 表示所有答案集中在文档末尾。
    :return: 包含 Markdown 文档的字符串。
    """
    if not questions:
        return "# 您的试卷为空"

    title = "# 生成的试卷\n\n"
    markdown_parts = [title]
    answers_part = ["---\n\n# 参考答案\n\n"]
    
    for i, q in enumerate(questions, 1):
        # 格式化题目
        markdown_parts.append(_format_question(q, i))
        
        # 处理答案
        answer_md = _format_answer(q)
        if answers_placement == 'inline':
            markdown_parts.append(answer_md)
            markdown_parts.append("---\n\n")
        else: # 'end'
            answers_part.append(f"### 题目 {i}\n\n")
            answers_part.append(answer_md)

    if answers_placement == 'end':
        markdown_parts.extend(answers_part)
        
    return "".join(markdown_parts) 