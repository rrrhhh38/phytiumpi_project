from flask import Flask, request, jsonify, send_from_directory
import os
import subprocess
import json
import time
import threading

app = Flask(__name__, static_folder='.')
DATA_DIR = 'data'
SCRIPT_PATH = './analyze_food.sh'
current_analysis = {
    'status': 'idle',  # idle, running, completed, error
    'message': '',
    'cpu_usage': [
        {'id': 0, 'usage': 0},
        {'id': 1, 'usage': 0},
        {'id': 2, 'usage': 0}
    ],
    'start_time': None
}
analysis_lock = threading.Lock()

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

@app.route('/api/analyze', methods=['POST'])
def start_analysis():
    global current_analysis
    with analysis_lock:
        if current_analysis['status'] == 'running':
            return jsonify({'error': '分析已在进行中'}), 400
        
        # 更新状态
        current_analysis = {
            'status': 'running',
            'message': '分析开始',
            'cpu_usage': [
                {'id': 0, 'usage': 10},
                {'id': 1, 'usage': 5},
                {'id': 2, 'usage': 5}
            ],
            'start_time': time.time()
        }
    
    # 在新线程中执行分析脚本
    thread = threading.Thread(target=run_analysis_script)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'started'})

def run_analysis_script():
    global current_analysis
    try:
        # 执行分析脚本
        result = subprocess.run([SCRIPT_PATH], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE,
                               text=True)
        
        if result.returncode != 0:
            with analysis_lock:
                current_analysis['status'] = 'error'
                current_analysis['message'] = f'脚本执行失败: {result.stderr}'
            return
        
        # 检查结果文件是否生成
        result_file = os.path.join(DATA_DIR, 'nutrition_result.json')
        if not os.path.exists(result_file):
            with analysis_lock:
                current_analysis['status'] = 'error'
                current_analysis['message'] = '分析结果文件未生成'
            return
            
        with analysis_lock:
            current_analysis['status'] = 'completed'
            current_analysis['message'] = '分析完成'
            
    except Exception as e:
        with analysis_lock:
            current_analysis['status'] = 'error'
            current_analysis['message'] = f'执行异常: {str(e)}'

@app.route('/api/status')
def get_status():
    with analysis_lock:
        # 随机更新CPU使用率，模拟变化
        if current_analysis['status'] == 'running':
            import random
            current_analysis['cpu_usage'] = [
                {'id': 0, 'usage': random.randint(60, 95)},  # 主核负载高
                {'id': 1, 'usage': random.randint(30, 70)},  # 摄像头程序
                {'id': 2, 'usage': random.randint(20, 50)}   # 称重程序
            ]
        return jsonify(current_analysis)

@app.route('/api/results')
def get_results():
    result_file = os.path.join(DATA_DIR, 'nutrition_result.json')
    
    if not os.path.exists(result_file):
        return jsonify({'error': '结果文件不存在'}), 404
        
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': f'读取结果失败: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

