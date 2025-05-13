import h5py
import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, models
import tf2onnx
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.utils import to_categorical

# === 1. 读取 .h5 数据文件 ===
print("📂 加载 HDF5 文件...")
h5_file = 'food_c101_n1000_r384x384x3.h5'
with h5py.File(h5_file, 'r') as f:
    X = np.array(f['images'])     # shape: (1000, 384, 384, 3)
    y = np.array(f['category_names'])  # shape: (1000,)

print(f"✅ 加载成功: 图像 {X.shape}, 标签 {y.shape}, 类别数: {len(np.unique(y))}")

# === 2. 标签编码与划分数据集 ===
X = X.astype("float32") / 255.0  # 归一化

with h5py.File(h5_file, 'r') as f:
    X = np.array(f['images'])     # (1000, 384, 384, 3)
    y = np.array(f['category'])   # (1000, 101) 直接是 one-hot 格式

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

# === 3. 构建模型 ===
print("🧠 构建模型中...")
model = models.Sequential([
    layers.Input(shape=(384, 384, 3)),
    layers.Conv2D(32, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(64, (3, 3), activation='relu'),
    layers.MaxPooling2D((2, 2)),
    layers.Conv2D(128, (3, 3), activation='relu'),
    layers.GlobalAveragePooling2D(),
    layers.Dense(256, activation='relu'),
    layers.Dropout(0.5),
    layers.Dense(101, activation='softmax')  # 101 类
])

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
model.summary()

# === 4. 模型训练 ===
print("🚀 模型训练中...")
model.fit(X_train, y_train, epochs=10, batch_size=16, validation_data=(X_val, y_val))

# === 5. 保存模型 (.h5) ===
h5_path = "food101_model.h5"
model.save(h5_path)
print(f"✅ 模型保存为 {h5_path}")

# === 6. 转换为 ONNX ===
print("🔁 正在转换为 ONNX 格式...")
spec = (tf.TensorSpec((None, 384, 384, 3), tf.float32, name="input"),)
onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature=spec, opset=13)

onnx_path = "food101_model.onnx"
with open(onnx_path, "wb") as f:
    f.write(onnx_model.SerializeToString())
print(f"✅ ONNX 模型已保存: {onnx_path}")
