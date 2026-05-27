"""
AI 分析服务
"""
import requests

from api.models import AIConfig


def replace_placeholders(template: str, context_data: dict) -> str:
    """替换模板中的占位符。"""
    for key, value in context_data.items():
        template = template.replace(f'{{{{{key}}}}}', str(value) if value is not None else '')
    return template


def run_ai_analysis(user, template, context_data) -> str:
    """调用 OpenAI 协议接口并返回分析正文。"""
    ai_config = AIConfig.objects.filter(user=user).first()
    if not ai_config:
        raise ValueError('未配置AI接口，请先在设置中配置')

    system_prompt = replace_placeholders(template.system_prompt, context_data)
    user_prompt = replace_placeholders(template.user_prompt, context_data)

    endpoint = ai_config.api_endpoint.rstrip('/')
    resp = requests.post(
        f'{endpoint}/chat/completions',
        headers={
            'Authorization': f'Bearer {ai_config.api_key}',
            'Content-Type': 'application/json',
        },
        json={
            'model': ai_config.model_name,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt},
            ],
        },
        timeout=60,
    )
    resp.raise_for_status()
    result = resp.json()
    return result['choices'][0]['message']['content']
