import json
import os
import siliconflow_client
import prompt_manager

CONFIG_FILE = "config.json"

def load_config():
    """安全地加载配置，确保所有必需的键都存在，防止因文件不完整而出错。"""
    default_profile = "该用户暂无画像，请根据本次答题情况生成一份初始画像。"
    defaults = {
        "temperature": 1.0,
        "enhanced_structured_output": False,
        "user_profile": default_profile
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(defaults, f, indent=4, ensure_ascii=False)
        return defaults

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            # 先加载默认值，再用文件中的设置覆盖，确保配置完整
            config = defaults.copy()
            loaded_config = json.load(f)
            config.update(loaded_config)
            return config
    except (json.JSONDecodeError, FileNotFoundError):
        # 如果文件损坏或不存在，返回一份完整的默认配置
        return defaults

def save_config(config_data):
    """保存配置文件"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config_data, f, indent=4, ensure_ascii=False)

def get_user_profile():
    """获取当前用户画像。"""
    config = load_config()
    return config["user_profile"]

def set_user_profile(profile_text: str):
    """
    直接设置或手动修改用户画像。
    """
    config = load_config()
    config["user_profile"] = profile_text
    save_config(config)

def update_user_profile(grading_summary: str, api_key: str):
    """
    根据一次答题的总结信息，调用LLM更新用户画像。

    Args:
        grading_summary (str): 答题情况的总结文本。
        api_key (str): 用于调用LLM的API Key。

    Returns:
        str: 更新后的用户画像文本，如果更新失败则返回None。
    """
    current_profile = get_user_profile()
    
    update_prompt = prompt_manager.get_prompt(
        "update_user_profile_prompt",
        current_profile=current_profile,
        grading_summary=grading_summary
    )
    
    messages = [{"role": "user", "content": update_prompt}]
    
    try:
        # 需要一个简单的文本响应，而不是流或结构化JSON
        response = siliconflow_client.invoke_llm(
            api_key=api_key,
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=messages,
            stream=False,
            temperature=0.5, # 使用较低的温度以获得更一致的画像分析
            enhanced_structured_output=False
        )
        
        # 假设客户端返回与OpenAI客户端兼容的对象
        updated_profile = response.choices[0].message.content.strip()

        if not updated_profile:
            print("LLM返回了空的用户画像，更新操作已跳过。")
            return None

        # 将更新后的画像保存回配置文件
        set_user_profile(updated_profile)
        
        return updated_profile

    except Exception as e:
        print(f"调用LLM更新用户画像时出错: {e}")
        return None 