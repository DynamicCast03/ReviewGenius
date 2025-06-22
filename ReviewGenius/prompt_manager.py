import os
from typing import Dict, Any

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def get_prompt(prompt_name: str, **kwargs: Any) -> str:
    """
    从 .txt 文件加载提示词模板并格式化。

    :param prompt_name: 提示词的名称 (不带 .txt 扩展名)。
    :param kwargs: 用于替换提示词中占位符的变量。
    :return: 格式化后的提示词字符串。
    """
    file_path = os.path.join(PROMPTS_DIR, f"{prompt_name}.txt")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"提示词模板文件未找到: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        prompt_template = f.read()

    return prompt_template.format(**kwargs)


if __name__ == "__main__":
    # 使用示例
    try:
        # 定义要替换的变量
        question_details = {
            "选择题": 5,
            "填空题": 5,
            "简答题": 2,
        }

        # 将字典转换为更易读的字符串
        question_types_str = "、".join(
            [f"{k}{v}道" for k, v in question_details.items()]
        )

        # 获取并格式化提示词
        formatted_prompt = get_prompt(
            "exam_generation_prompt",
            subject="高中物理",
            question_types=question_types_str,
        )

        print("----- 格式化后的提示词 -----")
        print(formatted_prompt)

    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"发生错误: {e}") 