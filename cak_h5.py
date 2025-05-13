import h5py

h5_file = 'food_c101_n1000_r384x384x3.h5'

with h5py.File(h5_file, 'r') as f:
    print("📁 HDF5 文件内容:")
    for key in f.keys():
        data = f[key]
        print(f"- {key}: shape = {data.shape}, dtype = {data.dtype}")
