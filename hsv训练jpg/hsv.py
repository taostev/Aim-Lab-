import cv2
import numpy as np

# 图片路径列表
image_paths = [
    'C:/Users/tao/Desktop/aim-rush/hsv训练jpg/1.jpg',
    'C:/Users/tao/Desktop/aim-rush/hsv训练jpg/2.jpg',
    'C:/Users/tao/Desktop/aim-rush/hsv训练jpg/3.jpg',
    'C:/Users/tao/Desktop/aim-rush/hsv训练jpg/4.jpg'
]

h_list, s_list, v_list = [], [], []

for path in image_paths:
    image = cv2.imread(path)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    h_list.append(h.flatten())
    s_list.append(s.flatten())
    v_list.append(v.flatten())

# 合并所有图片的通道数据
h_all = np.concatenate(h_list)
s_all = np.concatenate(s_list)
v_all = np.concatenate(v_list)

print(f"H通道范围: {h_all.min()} ~ {h_all.max()}")
print(f"S通道范围: {s_all.min()} ~ {s_all.max()}")
print(f"V通道范围: {v_all.min()} ~ {v_all.max()}")

print(f"H通道均值: {h_all.mean():.2f}")
print(f"S通道均值: {s_all.mean():.2f}")
print(f"V通道均值: {v_all.mean():.2f}")