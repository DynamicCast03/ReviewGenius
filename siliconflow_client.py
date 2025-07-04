import os
from openai import OpenAI, APIError
from typing import List, Dict, Generator, Union
from prompt_manager import get_prompt
import logging
import time

logger = logging.getLogger(__name__)

def _call_llm_with_retry(
    client: OpenAI,
    retries: int = 3,
    **kwargs,
):
    """
    通过重试机制调用OpenAI聊天补全API。

    :param client: OpenAI客户端实例。
    :param retries: 重试次数。
    :param kwargs: 传递给 client.chat.completions.create 的参数。
    :return: API调用结果。
    """
    last_exception = None
    for attempt in range(retries):
        try:
            return client.chat.completions.create(**kwargs)
        except APIError as e:
            logger.warning(f"LLM API调用失败 (尝试 {attempt + 1}/{retries}): {e}。1秒后重试...")
            last_exception = e
            time.sleep(1)
    logger.error(f"LLM API在 {retries} 次尝试后仍然失败。")
    raise last_exception


def invoke_llm(
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    stream: bool = False,
    temperature: float = 1.0,
    max_tokens: int = 4096,
    enhanced_structured_output: bool = False,
    formatting_prompt: str = None
) -> Union[Generator[str, None, None], str]:
    """
    Invokes the SiliconFlow Large Language Model.

    :param api_key: Your SiliconFlow API key.
    :param model: The name of the model to use.
    :param messages: A list of message dictionaries.
    :param stream: Whether to return the response as a stream.
    :param temperature: The sampling temperature.
    :param max_tokens: The maximum number of tokens to generate.
    :param enhanced_structured_output: Whether to enable enhanced structured output.
    :param formatting_prompt: The formatting prompt for secondary streaming.
    :return: A generator if stream is True, otherwise a string with the full response.
    """
    if not api_key:
        raise ValueError("API Key 不能为空")

    client = OpenAI(
        api_key=api_key,
        base_url=os.environ.get("SILICONFLOW_API_BASE", "https://api.siliconflow.cn/v1"),
    )

    # 提取用户输入内容进行安全检查
    user_content = "\n".join([msg.get("content", "") for msg in messages])

    if user_content.strip():
        try:
            # 从 prompt_manager 获取安全检查提示词
            logger.info("执行内容安全检查.")
            security_prompt = get_prompt("security_check_prompt")
            security_check_messages = [
                {"role": "system", "content": security_prompt},
                {"role": "user", "content": f"请审查以下内容：\n\n---\n{user_content}\n---"}
            ]

            security_response = _call_llm_with_retry(
                client,
                model=model,
                messages=security_check_messages,
                stream=False,
                temperature=0.7,
                max_tokens=20,
            )
            security_result = security_response.choices[0].message.content.strip().lower()

            if "unsafe" in security_result:
                logger.warning(f"内容安全检查失败，模型返回: {security_result}")
                raise ValueError("输入内容被判定为不安全，已拒绝处理。")
            else:
                logger.info("内容安全检查通过.")

        except FileNotFoundError:
            # 如果提示文件不存在，可以选择是抛出异常还是记录警告后继续
            logger.warning("警告: 未找到 'security_check_prompt.txt'，跳过内容安全检查。")
        except APIError as e:
            logger.error(f"内容安全检查过程中调用模型失败: {e}")
            raise e

    # 如果启用了增强结构化输出
    if enhanced_structured_output and formatting_prompt:
        # 1. 第一次调用，非流式，获取完整输出
        logger.info(f"开始增强模式第一次LLM调用. Model: {model}, Temp: {temperature}")
        try:
            initial_response = _call_llm_with_retry(
                client,
                model=model,
                messages=messages,
                stream=False, # 强制非流式
                temperature=temperature,
                max_tokens=max_tokens,
            )
            first_call_output = initial_response.choices[0].message.content
            logger.info(f"增强模式第一次LLM调用成功. Output length: {len(first_call_output)}")
        except APIError as e:
            # 如果第一次调用失败，直接抛出异常
            logger.error(f"增强模式下，第一次调用模型失败: {e}")
            raise e

        # 2. 第二次调用，使用格式化提示词，流式返回
        reformat_messages = [
            {
                "role": "user",
                "content": f"你是一个JSON格式化专家。你的任务是将一段可能不完全符合格式的文本，严格修正为连续的、无缝拼接的JSON对象流。\n\n"
                           f"**极端重要规则**:\n"
                           f"1. **绝对禁止**在第一个JSON对象之前或最后一个JSON对象之后，输出任何说明性文字、注释或任何非JSON内容。\n"
                           f"2. 你的输出流必须**只能**是连续的、无缝拼接的JSON对象。例如: {{\"key\": \"value\"}}{{\"key\": \"value\"}}。\n"
                           f"3. 每个JSON对象都必须严格遵守JSON语法，**严禁**使用悬挂逗号（trailing commas）。\n\n"
                           f"**JSON对象结构参考**:\n"
                           f"每个JSON对象都应该像下面这个例子一样，但字段内容需根据'待格式化内容'来填充:\n"
                           f"```json\n{formatting_prompt}\n```\n\n"
                           f"**待格式化内容**:\n---\n{first_call_output}\n---\n\n"
                           f"请立即开始输出格式化后的JSON流。"
            }
        ]
        
        # 返回第二次调用的流
        logger.info("开始增强模式第二次LLM调用 (流式格式化).")
        return _call_llm_with_retry(
            client,
            model='Pro/Qwen/Qwen2.5-7B-Instruct',
            messages=reformat_messages,
            stream=stream,
            temperature=0.0,
            max_tokens=max_tokens,
        )

    # 原始逻辑：如果未启用增强模式
    logger.info(f"开始标准LLM调用. Model: {model}, Stream: {stream}, Temp: {temperature}")
    return _call_llm_with_retry(
        client,
        model=model,
        messages=messages,
        stream=stream,
        temperature=temperature,
        max_tokens=max_tokens,
    )


if __name__ == "__main__":
    # 从环境变量获取 API Key，请确保已设置 SILICONFLOW_API_KEY
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        raise ValueError("请设置 SILICONFLOW_API_KEY 环境变量")

    # ----- 非流式调用示例 -----
    logger.info("----- 非流式调用 -----")
    non_stream_messages = [
        {"role": "user", "content": "你好，请介绍一下你自己。"}
    ]
    non_stream_response = invoke_llm(
        api_key,
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=non_stream_messages,
        stream=False,
    )
    logger.info(non_stream_response)

    # ----- 流式调用示例 -----
    logger.info("\n----- 流式调用 -----")
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
        logger.info(chunk) 