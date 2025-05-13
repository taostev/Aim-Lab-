import time
from utils.controls.mouse.win32 import MouseControls
# 如果有键盘控制模块可以引入，比如：
# from utils.controls.keyboard.win32 import KeyboardControls
import pyautogui  # 备用键盘模拟

mouse = MouseControls()

# 定义WASD按键列表
wasd_keys = ['w', 'a', 's', 'd']

# 循环5次
for i in range(5):
    print(f"第{i+1}轮开始")
    # 依次按下WASD
    for key in wasd_keys:
        print(f"按下 {key.upper()} 键")
        pyautogui.keyDown(key)
        time.sleep(0.3)
        pyautogui.keyUp(key)
        time.sleep(0.2)
    # 鼠标左右移动（模拟视角转动）
    print("鼠标向右移动100像素")
    mouse.move_relative(100, 0)
    time.sleep(0.3)
    print("鼠标向左移动100像素")
    mouse.move_relative(-100, 0)
    time.sleep(0.3)
    # 鼠标左键点击（射击）
    print("模拟鼠标左键射击")
    mouse.hold_mouse()
    time.sleep(0.1)
    mouse.release_mouse()
    time.sleep(0.5)
    print(f"第{i+1}轮结束\n")

print("测试完成！")
