import cv2
import base64
import os
import time
import json
from multiprocessing import Process

def capture_photo():
    cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    
    if not cap.isOpened():
        print("错误：无法通过 V4L2 打开摄像头！")
        return
    
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    print("摄像头已就绪，拍摄照片...")
    
    for i in range(5):
        ret, frame = cap.read()
        time.sleep(0.1)
    
    ret, frame = cap.read()
    if not ret:
        print("错误：无法获取视频帧！")
        return False
    
    timestamp = int(time.time())
    image_path = f"food_{timestamp}.jpg"
    cv2.imwrite(image_path, frame)
    print(f"照片已保存为 {image_path}")
    
    status = {
        "image_ready": True,
        "image_path": image_path,
        "timestamp": timestamp
    }
    
    with open("capture_status.json", "w") as f:
        json.dump(status, f)
    
    cap.release()
    cv2.destroyAllWindows()
    print("摄像头程序已完成")
    return True

if __name__ == "__main__":
    camera_process = Process(target=capture_photo)
    
    os.system(f"taskset -cp 1 {os.getpid()}")
    
    # 启动进程
    camera_process.start()
    camera_process.join()

