import random

def grade_multiple_choice(question, user_answer):
    """
    批改选择题
    """
    correct_answer = question.get("answer")
    is_correct = user_answer == correct_answer

    # Mock feedback
    if is_correct:
        feedback = "回答正确，干得漂亮！"
    else:
        feedback = f"回答错误。这道题考察了相关的知识点，正确答案是 {correct_answer}，请再回顾一下哦。"

    return {
        "score": question.get("score", 0) if is_correct else 0,
        "is_correct": is_correct,
        "feedback": feedback,
    }


def grade_fill_in_the_blank(question, user_answer):
    """
    批改填空题
    """
    correct_answers = question.get("answer", [])
    user_answers = [ans.strip() for ans in user_answer] if isinstance(user_answer, list) else [user_answer.strip()]
    
    # 目前简单实现：全对才得分
    score = 0
    if len(correct_answers) == len(user_answers) and all(ua == ca for ua, ca in zip(user_answers, correct_answers)):
        score = question.get("score", 0)
    
    # Mock feedback
    feedback = random.choice([
        "这道题旨在检验你对基础概念的掌握程度，继续努力！",
        "填空题需要注意细节，再接再厉。",
        "做得不错，但可以试着思考更多可能性。"
    ])

    return {
        "score": score,
        "feedback": feedback,
    }


def grade_short_answer(question, user_answer):
    """
    批改简答题/计算题
    """
    # 目前简单实现：mock一个分数和评论
    # 随机给一个分数
    earned_score = random.randint(0, question.get("score", 10))

    # Mock feedback
    if earned_score == question.get("score", 10):
        feedback = "回答得非常全面，要点突出，结构清晰，很棒！"
    elif earned_score > question.get("score", 10) / 2:
        feedback = "基本答对了要点，但可以更深入地阐述一些细节。"
    else:
        feedback = "回答偏离了核心要点，建议重新阅读相关材料，理解题目考察的知识点。"

    return {
        "score": earned_score,
        "feedback": feedback,
    }


def grade_exam(questions, user_answers):
    """
    批改整份试卷
    """
    results = []
    for i, question in enumerate(questions):
        user_answer = user_answers[i]
        q_type = question.get("question_type")
        
        result = None
        if q_type == "multiple_choice":
            result = grade_multiple_choice(question, user_answer)
        elif q_type == "fill_in_the_blank":
            result = grade_fill_in_the_blank(question, user_answer)
        elif q_type == "short_answer":
            result = grade_short_answer(question, user_answer)
        else:
            result = {"score": 0, "feedback": "未知题型，无法批改"}
        
        results.append(result)

    return results
