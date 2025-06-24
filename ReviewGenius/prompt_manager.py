import os
from jinja2 import Template

def get_prompt(prompt_name: str, is_template=False, **kwargs) -> str:
    """
    从prompts文件夹中读取一个prompt模板文件，并用传入的参数渲染它。

    :param prompt_name: prompt文件的名称（不含扩展名）。
    :param kwargs: 用于渲染模板的键值对。
    :return: 渲染后的prompt字符串。
    """
    # 构建prompts文件夹的路径
    prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
    prompt_file_path = os.path.join(prompts_dir, f"{prompt_name}.txt")

    if not os.path.exists(prompt_file_path):
        raise FileNotFoundError(f"Prompt a '{prompt_name}' not found at '{prompt_file_path}'")

    with open(prompt_file_path, "r", encoding="utf-8") as f:
        prompt_template_str = f.read()
    
        template = Template(prompt_template_str)
    if is_template:
        return template
    else:
        return template.render(**kwargs)


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