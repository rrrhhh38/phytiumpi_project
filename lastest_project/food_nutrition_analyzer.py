import argparse
import requests
import json
import os
import time
import sys
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
import base64

# 硬编码API密钥
DEEPSEEK_API_KEY = "************" #加密API 

def load_prompt_template() -> str:
    """加载提示词模板（增加文件检查）"""
    try:
        with open("prompt_template.txt", "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content
    except FileNotFoundError:
        print("\n=== 错误：未找到 prompt_template.txt ===")
        # 创建默认提示词模板
        default_template = """请分析图中食物的营养成分，该食物是{food}，重量为{weight}。请给出以下信息：
1. 精确的食物名称
2. 热量（千卡）
3. 碳水化合物（克）
4. 蛋白质（克）
5. 脂肪（克）
6. 基于上述营养成分的饮食建议

请以JSON格式回复，格式如下：
{{"food": "食物名称", "calories": "热量", "carbohydrates": "碳水化合物", "protein": "蛋白质", "fat": "脂肪", "advice": "饮食建议"}}"""
        
        with open("prompt_template.txt", "w", encoding="utf-8") as f:
            f.write(default_template)
        
        print("已创建默认提示词模板文件")
        return default_template

def encode_image_to_base64(image_path: str) -> Optional[str]:
    """
    将本地图片编码为Base64字符串。

    :param image_path: 本地图片路径
    :return: Base64编码的图片字符串或None
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return encoded_string
    except Exception as e:
        print(f"图片编码失败: {e}")
        return None

def call_deepseek_api(prompt_content: str, image_base64: str) -> Optional[Dict]:
    """调用doubao Vision API"""
    url = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    # 构建消息内容
    messages = [
        {
            "content": [
                {"text": prompt_content, "type": "text"},
                {
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    },
                    "type": "image_url"
                }
            ],
            "role": "user"
        }
    ]

    # 根据API文档调整请求体
    payload = {
        "model": "ep-20250515232926-cfjtd",
        "messages": messages
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求失败: {e}")
        return None
    except Exception as e:
        print(f"请求处理异常: {e}")
        return None

def parse_nutrition_response(api_response: Dict) -> Optional[Dict]:
    """解析API返回的营养数据"""
    if not api_response:
        print("\n=== 调试：API响应为空 ===")
        return None

    try:
        # 假设API返回的内容在choices[0].message.content中，并且是JSON字符串
        content = api_response["choices"][0]["message"]["content"]
        
        # 尝试直接解析内容为JSON（如果API返回的是JSON字符串）
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 如果不是JSON字符串，则需要从文本中提取
            print("API返回的内容不是有效的JSON字符串，尝试解析文本...")
            # 返回原始内容
            return {"raw_response": content}
    except (KeyError, json.JSONDecodeError) as e:
        print(f"解析API响应失败: {e}")
        print(f"原始响应: {api_response}")
        return None

def wait_for_data(max_wait_time=60):
    """等待摄像头和重量数据准备好"""
    start_time = time.time()
    image_path = None
    weight_grams = None
    
    print("等待数据准备...")
    
    while time.time() - start_time < max_wait_time:
        # 检查摄像头数据
        if os.path.exists("capture_status.json"):
            try:
                with open("capture_status.json", "r") as f:
                    status = json.load(f)
                    if status.get("image_ready", False):
                        image_path = status.get("image_path")
                        print(f"发现图像文件: {image_path}")
            except json.JSONDecodeError:
                pass
        
        # 检查重量数据
        if os.path.exists("weight_data.txt"):
            try:
                with open("weight_data.txt", "r") as f:
                    weight_str = f.read().strip()
                    weight_grams = float(weight_str)
                    print(f"发现重量数据: {weight_grams} 克")
            except (ValueError, IOError):
                pass
        
        # 如果两个数据都准备好了，就可以继续
        if image_path and weight_grams is not None:
            return image_path, weight_grams
        
        time.sleep(1)
    
    return image_path, weight_grams

def set_cpu_affinity(cpu_id):
    """设置CPU亲和性"""
    try:
        os.system(f"taskset -cp {cpu_id} {os.getpid()}")
        print(f"已将进程绑定到CPU {cpu_id}")
        return True
    except Exception as e:
        print(f"设置CPU亲和性失败: {e}")
        return False

def main():
    # 设置CPU亲和性，绑定到CPU 0（主核）
    set_cpu_affinity(0)
    
    image_path, weight_grams = wait_for_data()
    
    if not image_path:
        print("错误：未能获取图像数据")
        return
    

        

    
    template = load_prompt_template()
    
    food_name = os.path.splitext(os.path.basename(image_path))[0]  # 获取文件名（不含扩展名）
    
    prompt = template.format(food=food_name, weight=f"{weight_grams}克")

    # 将图片编码为Base64
    image_base64 = encode_image_to_base64(image_path)
    if not image_base64:
        print("\n=== 错误：无法将图片编码为Base64 ===")
        return

    # 调用 API
    print("\n正在调用API分析食物营养成分...")
    api_response = call_deepseek_api(prompt, image_base64)

    if not api_response:
        print("API请求失败，请检查网络或API密钥。")
        return

    # 解析并打印结果
    nutrition_data = parse_nutrition_response(api_response)
    if isinstance(nutrition_data, dict):
        if "calories" in nutrition_data and "carbohydrates" in nutrition_data and \
           "protein" in nutrition_data and "fat" in nutrition_data and "advice" in nutrition_data:
            result = nutrition_data
        else:
            raw_response = nutrition_data.get("raw_response", "{}")
            try:
                extracted_data = json.loads(raw_response)
                # 根据实际返回的数据结构进行调整
                result = {
                    "calories": extracted_data.get("calories", "N/A"),
                    "carbohydrates": extracted_data.get("carbohydrates", "N/A"),
                    "protein": extracted_data.get("protein", "N/A"),
                    "fat": extracted_data.get("fat", "N/A"),
                    "advice": extracted_data.get("advice", "N/A"),
                    "food": extracted_data.get("food", "N/A")
                }
            except json.JSONDecodeError:
                # 如果无法解析，则返回默认值
                result = {
                    "calories": "N/A",
                    "carbohydrates": "N/A",
                    "protein": "N/A",
                    "fat": "N/A",
                    "advice": "无法解析营养数据",
                    "food": "无法识别"
                }
    else:
        result = {
            "calories": "N/A",
            "carbohydrates": "N/A",
            "protein": "N/A",
            "fat": "N/A",
            "advice": "无法解析营养数据",
            "food": "未识别食物"
        }

    output = {
        "food": result.get("food", "未知食物"),
        "weight": f"{weight_grams}克",
        "calories": result.get("calories", "N/A"),
        "carbohydrates": result.get("carbohydrates", "N/A"),
        "protein": result.get("protein", "N/A"),
        "fat": result.get("fat", "N/A"),
        "advice": result.get("advice", "N/A")
    }

    # 打印JSON格式的输出
    print("\n=== 食物营养分析结果 ===")
    print(f"食物: {output['food']}")
    print(f"重量: {output['weight']}")
    print(f"热量: {output['calories']} 千卡")
    print(f"碳水化合物: {output['carbohydrates']} 克")
    print(f"蛋白质: {output['protein']} 克")
    print(f"脂肪: {output['fat']} 克")
    print(f"饮食建议: {output['advice']}\n")
    
    with open("nutrition_result.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("分析结果已保存到 nutrition_result.json")

if __name__ == "__main__":
    main()

