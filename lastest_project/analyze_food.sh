#!/bin/bash

# food_nutrition_analyzer.sh
# 食物营养分析系统总控脚本

echo "=========================================="
echo "食物营养分析系统启动中..."
echo "=========================================="

# 检查系统CPU核心数
CPU_CORES=$(nproc)
echo "检测到系统CPU核心数: $CPU_CORES"

if [ $CPU_CORES -lt 3 ]; then
    echo "警告: 系统核心数不足3个，可能无法正确分配进程到不同核心！"
    echo "将继续执行，但不保证核心分配效果。"
fi

# 清理之前的临时文件
echo "清理临时文件..."
rm -f capture_status.json weight_data.txt nutrition_result.json

# 编译HX711程序
echo "编译HX711重量传感器程序..."
gcc -o weight_sensor hx711_weight.c -lgpiod

# 检查是否已创建提示词模板
if [ ! -f "prompt_template.txt" ]; then
    echo "创建默认提示词模板..."
    cat > prompt_template.txt << 'EOF'
请分析图中食物的营养成分，该食物是{food}，重量为{weight}。请给出以下信息：
1. 精确的食物名称
2. 热量（千卡）
3. 碳水化合物（克）
4. 蛋白质（克）
5. 脂肪（克）
6. 基于上述营养成分的饮食建议

请以JSON格式回复，格式如下：
{"food": "食物名称", "calories": "热量", "carbohydrates": "碳水化合物", "protein": "蛋白质", "fat": "脂肪", "advice": "饮食建议"}
EOF
fi

# 在后台启动摄像头程序（分配到从核1）
echo "启动摄像头程序..."
taskset -c 1 python3 camera_capture.py &
CAMERA_PID=$!

# 在后台启动HX711重量传感器程序（分配到从核2）
echo "启动重量传感器程序..."
taskset -c 2 ./weight_sensor &
WEIGHT_PID=$!

# 等待数据收集完成
echo "等待数据收集..."
MAX_WAIT=60
START_TIME=$(date +%s)

while [ $(($(date +%s) - START_TIME)) -lt $MAX_WAIT ]; do
    # 检查摄像头进程是否运行
    if ! ps -p $CAMERA_PID > /dev/null; then
        echo "摄像头程序已完成"
        CAMERA_DONE=1
    fi
    
    # 检查重量传感器进程是否运行
    if ! ps -p $WEIGHT_PID > /dev/null; then
        echo "重量传感器程序已完成"
        WEIGHT_DONE=1
    fi
    
    # 检查两个进程是否都完成
    if [ ! -z "$CAMERA_DONE" ] && [ ! -z "$WEIGHT_DONE" ]; then
        break
    fi
    
    # 检查是否已生成所需文件
    if [ -f "capture_status.json" ] && [ -f "weight_data.txt" ]; then
        echo "数据已准备就绪"
        break
    fi
    
    # 等待1秒
    sleep 1
    echo -n "."
done

echo ""
echo "数据收集阶段完成"

# 在主核上运行API分析程序
echo "在主核上运行API分析程序..."
taskset -c 0 python3 food_nutrition_analyzer.py

echo "=========================================="
echo "食物营养分析完成！"
echo "=========================================="

# 清理进程
kill $CAMERA_PID 2>/dev/null
kill $WEIGHT_PID 2>/dev/null

