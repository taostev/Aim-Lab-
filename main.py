# 导入所需模块
import math

from utils.grabbers.mss import Grabber  # 屏幕捕获模块
from utils.fps import FPS  # 帧率统计模块
import cv2  # OpenCV图像处理
import multiprocessing  # 多进程支持
import numpy as np  # 数值计算
from utils.nms import non_max_suppression_fast  # 非极大值抑制
from utils.cv2 import filter_rectangles  # 目标矩形过滤

from utils.controls.mouse.win32 import MouseControls  # 鼠标控制
from utils.win32 import WinHelper  # 窗口辅助工具
import keyboard  # 键盘监听
import time
from utils.time import sleep  # 自定义sleep函数

from screen_to_world import get_move_angle  # 屏幕坐标到游戏角度转换

# ===================== 配置区 =====================
ACTIVATION_HOTKEY = 58  # 激活热键（58 = CAPS-LOCK）
AUTO_DEACTIVATE_AFTER = 60  # 自动关闭时间（秒），None为不自动关闭
_shoot = True  # 是否自动射击
_show_cv2 = True  # 是否显示OpenCV窗口

# 精度与安全性相关参数，数值越大越安全
_pause = 0.05  # 鼠标移动后暂停时间
_shoot_interval = 0.05  # 射击间隔（秒）

# ===================== 全局变量 =====================
game_window_rect = WinHelper.GetWindowRect("Counter-Strike 2", (8, 30, 16, 39))  # 获取游戏窗口区域
_ret = None  # 鼠标回位用
_aim = False  # 是否处于瞄准状态
_activation_time = 0  # 激活时间戳

# ===================== 屏幕捕获进程 =====================
def grab_process(q):
    """
    屏幕捕获进程：不断截取游戏窗口区域的图像，放入队列供后续处理。
    """
    grabber = Grabber()

    while True:
        img = grabber.get_image({"left": int(game_window_rect[0]), "top": int(game_window_rect[1]), "width": int(game_window_rect[2]), "height": int(game_window_rect[3])})

        if img is None:
            continue

        q.put_nowait(img)
        q.join()

# ===================== 图像处理与自动瞄准进程 =====================
def cv2_process(q):
    """
    图像处理与自动瞄准进程：
    1. 从队列获取截图
    2. 进行颜色分割、轮廓检测、目标筛选
    3. 计算目标中心与准星的相对位置
    4. 控制鼠标移动并自动射击
    5. 可选显示OpenCV窗口调试
    """
    global _aim, _shoot, _ret, _pause, _shoot_interval, _show_cv2, game_window_rect, _activation_time

    fps = FPS()
    font = cv2.FONT_HERSHEY_SIMPLEX
    _last_shoot = None
    grabber = Grabber()

    mouse = MouseControls() 

    fov = [106.26, 73.74]  # 水平和垂直视场角

    x360 = 16364  # 360度旋转所需鼠标x值
    x1 = x360/360
    x_full_hor = x1 * fov[0]

    hue_point = 35  # 取你目标 H通道均值或中心值，比如33.96四舍五入

    def check_dot(hue_point):
        """
        检查准星点颜色，判断是否瞄准到目标
        """
        dot_img = grabber.get_image({"left": int(game_window_rect[0] + (game_window_rect[2]/2) + 5),
                                     "top": int(
                                         game_window_rect[1] + (game_window_rect[3]/2) + 28),
                                     "width": 6,
                                     "height": 6})
        dot_img = cv2.cvtColor(dot_img, cv2.COLOR_BGR2HSV)
        avg_color_per_row = np.average(dot_img, axis=0)
        avg_color = np.average(avg_color_per_row, axis=0)

        return (hue_point - 10 < avg_color[0] < hue_point + 20) and (avg_color[1] > 120) and (avg_color[2] > 100)

    while True:
        if not q.empty():
            img = q.get_nowait()
            q.task_done()

            # ========== 目标识别部分 ==========
            # 1. HSV颜色分割，提取目标颜色区域
            # 根据统计结果和实际观察调整
            sphere_color = ((20, 10, 100), (50, 80, 255))  # 你可以根据实际效果继续调整
            min_target_size = (40, 40)  # 目标最小尺寸
            max_target_size = (150, 150)  # 目标最大尺寸

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, np.array(sphere_color[0], dtype=np.uint8),
                               np.array(sphere_color[1], dtype=np.uint8))

            contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            rectangles = []

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if (w >= min_target_size[0] and h >= min_target_size[1])\
                        and (w <= max_target_size[0] and h <= max_target_size[1]):
                    rectangles.append((int(x), int(y), int(w), int(h)))

            if not rectangles:
                continue

            # ========== 可视化调试 ==========
            if _show_cv2:
                for rect in rectangles:
                    x, y, w, h = rect
                    cv2.rectangle(img, (x, y), (x + w, y + h), [255, 0, 0], 6)
                    img = cv2.putText(img, f"{(x + w, y + h)}", (x, y-10), font,
                                      .5, (0, 255, 0), 1, cv2.LINE_AA)

            # ========== 目标筛选与处理 ==========
            targets_count = len(rectangles)
            rectangles = np.array(non_max_suppression_fast(np.array(rectangles), overlapThresh=0.3))  # NMS去重
            rectangles = filter_rectangles(rectangles.tolist())  # 合并重叠目标

            # 选择距离准星最近的目标
            closest = 1000000
            aim_rect = None
            for rect in rectangles:
                x, y, w, h = rect
                mid_x = int((x+(x+w))/2)
                mid_y = int((y+(y+h))/2)
                dist = math.dist([960, 540], [mid_x, mid_y])

                if dist < closest:
                    closest = dist
                    aim_rect = rect

            rectangles = [aim_rect]
            for rect in rectangles:
                x, y, w, h = rect
                if _show_cv2:
                    cv2.rectangle(img, (x, y), (x + w, y + h), [0, 255, 0], 2)

                # 计算目标中心点
                mid_x = int((x+(x+w))/2)
                mid_y = int((y+(y+h))/2)
                if _show_cv2:
                    cv2.circle(img, (mid_x, mid_y), 10, (0, 0, 255), -1)

                # ========== 自动瞄准与射击 ==========
                if _aim:
                    if _last_shoot is None or time.perf_counter() > (_last_shoot + _shoot_interval):
                        rel_diff = get_move_angle((mid_x, mid_y), game_window_rect, x1, fov)

                        # 鼠标移动到目标
                        mouse.move_relative(int(rel_diff[0]), int(rel_diff[1]))
                        sleep(_pause)

                        if _shoot:
                            # 检查准星是否对准目标
                            if check_dot(hue_point):
                                # 执行鼠标点击
                                mouse.hold_mouse()
                                sleep(0.001)
                                mouse.release_mouse()
                                sleep(0.001)

                                _last_shoot = time.perf_counter()
                                break
                        else:
                            # 只瞄准一次
                            _aim = False

                    # 自动关闭功能
                    if AUTO_DEACTIVATE_AFTER is not None:
                        if _activation_time+AUTO_DEACTIVATE_AFTER < time.perf_counter():
                            _aim = False

            # ========== OpenCV窗口显示 ==========
            if _show_cv2:
                img = cv2.putText(img, f"{fps():.2f} | targets = {targets_count}", (20, 120), font,
                                  1.7, (0, 255, 0), 7, cv2.LINE_AA)
                img = cv2.resize(img, (1280, 720))
                cv2.imshow("test", img)
                cv2.waitKey(1)

# ===================== 热键切换瞄准状态 =====================
def switch_shoot_state(triggered, hotkey):
    """
    热键回调函数：切换自动瞄准/射击状态
    """
    global _aim, _ret, _activation_time
    _aim = not _aim  # 状态取反

    if not _aim:
        _ret = None
    else:
        _activation_time = time.perf_counter()

# 绑定激活热键
keyboard.add_hotkey(ACTIVATION_HOTKEY, switch_shoot_state, args=('triggered', 'hotkey'))

# ===================== 主程序入口 =====================
if __name__ == "__main__":
    # 创建进程间队列
    q = multiprocessing.JoinableQueue()

    # 启动屏幕捕获和图像处理两个进程
    p1 = multiprocessing.Process(target=grab_process, args=(q,))
    p2 = multiprocessing.Process(target=cv2_process, args=(q,))

    p1.start()
    p2.start()