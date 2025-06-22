import os
from openai import OpenAI
from typing import List, Dict, Generator, Union

def invoke_llm(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    stream: bool = False,
) -> Union[Generator[str, None, None], str]:
    """
    调用硅基流动（SiliconFlow）的大语言模型。

    :param api_key: 你的 SiliconFlow API 密钥。
    :param model: 要使用的模型名称。
    :param messages: 对话消息列表。
    :param stream: 是否以流式方式返回响应。
    :return: 如果 stream 为 True，则返回一个生成器；否则返回一个包含完整响应的字符串。
    """
    client = OpenAI(api_key=api_key, base_url="https://api.siliconflow.cn/v1")

    if stream:
        def stream_generator():
            response = client.chat.completions.create(
                model=model, messages=messages, stream=True
            )
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        return stream_generator()
    else:
        response = client.chat.completions.create(
            model=model, messages=messages, stream=False
        )
        return response.choices[0].message.content


if __name__ == "__main__":
    # 从环境变量获取 API Key，请确保已设置 SILICONFLOW_API_KEY
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        raise ValueError("请设置 SILICONFLOW_API_KEY 环境变量")

    # ----- 非流式调用示例 -----
    print("----- 非流式调用 -----")
    non_stream_messages = [
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ]
    non_stream_response = invoke_llm(
        api_key,
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=non_stream_messages,
        stream=False,
    )
    print(non_stream_response)

    # ----- 流式调用示例 -----
    print("\n----- 流式调用 -----")
    stream_messages = [
        {"role": "user", "content": "推理模型会给市场带来哪些新的机会"}
    ]
    stream_response = invoke_llm(
        api_key,
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=stream_messages,
        stream=True,
    )
    for chunk in stream_response:
        print(chunk, end="", flush=True)
    print() 