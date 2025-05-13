import h5py
import numpy as np
import pickle
from sklearn.preprocessing import LabelEncoder

# 1. 打开 HDF5，读取 one-hot 矩阵和类别名称
h5_file = 'food_c101_n1000_r384x384x3.h5'
with h5py.File(h5_file, 'r') as f:
    category = np.array(f['category'])            # shape (1000, 101), bool one-hot
    category_names = np.array(f['category_names'])  # shape (101,), bytes strings

# 2. 将 one-hot 转成每张图的类别名称字符串
#    注意把 bytes 解码为 unicode
category_names = [n.decode('utf-8') for n in category_names]
labels_indices = np.argmax(category, axis=1)       # shape (1000,)
labels_str = [category_names[i] for i in labels_indices]

# 3. 拟合 LabelEncoder 并保存
le = LabelEncoder()
le.fit(labels_str)

with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

print("✅ 已生成并保存 label_encoder.pkl，类别数：", len(le.classes_))
