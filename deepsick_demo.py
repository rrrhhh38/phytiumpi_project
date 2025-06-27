import argparse
import requests
import json
from typing import Dict, Optional

def load_prompt_template() -> str:
    """加载提示词模板（增加文件检查）"""
    try:
        with open("prompt_template.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content
    except FileNotFoundError:
        print("\n=== 错误：未找到 prompt_template.txt ===")
        exit(1)

def call_deepseek_api(prompt: str, api_key: str) -> Optional[Dict]:
    """调用 DeepSeek API"""
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"  # 替换为火山引擎提供的API地址
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "deepseek-r1-250120",  # 根据实际模型名称调整
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 500
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()  # 检查HTTP错误
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
        print(f"\n=== 调试：API请求失败 ===")  # 调试信息
        print(f"Error: {e}")
        return None

def parse_nutrition_response(api_response: Dict) -> Optional[Dict]:
    if not api_response:
        print("\n=== 调试：API响应为空 ===")
        return None
    """解析API返回的营养数据"""
    try:
        content = api_response["choices"][0]["message"]["content"]
        return json.loads(content)  # 假设API返回的是JSON字符串
    except (KeyError, json.JSONDecodeError) as e:
        print(f"解析API响应失败: {e}")
        return None

def main():
    # 1. 解析命令行参数
    parser = argparse.ArgumentParser(description="食物营养分析工具（基于DeepSeek API）")
    parser.add_argument("food", type=str, help="食物名称（中文，如 '草莓蛋糕'）")
    parser.add_argument("weight", type=str, help="重量（如 '300克'）")
    args = parser.parse_args()

    # 2. 加载提示词模板
    template = load_prompt_template()
    prompt = template.format(food=args.food, weight=args.weight)

    # 3. 调用DeepSeek API（API_KEY需替换为你的实际密钥）
    API_KEY = "41de79ad-2515-430c-8efe-4a17c8027cd7"  # 建议改用环境变量或配置文件
    api_response = call_deepseek_api(prompt, API_KEY)

    if not api_response:
        print("API请求失败，请检查网络或API密钥。")
        return

    # 4. 解析并打印结果
    nutrition_data = parse_nutrition_response(api_response)
    if nutrition_data:
        print("\n=== 营养分析结果 ===")
        print(f"食物: {args.food} {args.weight}")
        print(f"热量: {nutrition_data.get('calories', 'N/A')} 大卡")
        print(f"碳水: {nutrition_data.get('carbohydrates', 'N/A')} 克")
        print(f"蛋白质: {nutrition_data.get('protein', 'N/A')} 克")
        print(f"脂肪: {nutrition_data.get('fat', 'N/A')} 克")
        print("\n饮食建议:")
        print(nutrition_data.get("advice", "N/A"))
    else:
        print("解析营养数据失败，请检查API返回格式。")

if __name__ == "__main__":
    main()
