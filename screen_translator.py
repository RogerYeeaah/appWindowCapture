#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
import json
import os
import sys
import time

from AppKit import NSRunningApplication
from PIL import Image, ImageTk
from Quartz import (
    CGRectNull, CGWindowListCreateImage,
    kCGWindowListOptionIncludingWindow, CGImageGetWidth, CGImageGetHeight,
    CGImageGetDataProvider, CGDataProviderCopyData, CGImageGetBytesPerRow,
    kCGWindowImageBoundsIgnoreFraming,
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionAll,
    kCGWindowListExcludeDesktopElements,
    kCGNullWindowID
)

TARGET_APP_NAME = "音樂"
DEFAULT_PREVIEW_WIDTH = 140
MIN_PREVIEW_WIDTH = 80
BUTTON_SIZE = (16, 16)
DEFAULT_ALPHA = 1.0
MIN_ALPHA_VALUE = 20
DEFAULT_X_POS = 50
DEFAULT_Y_POS = 50
REFRESH_RATE_MS = 40
CONFIG_FILE = "monitor_config.json"
MANUAL_CROP_TOP = 100
MANUAL_CROP_BOTTOM = 240
MANUAL_CROP_LEFT = 1360
MANUAL_CROP_RIGHT = 0

# --- 新增：健康檢查相關設定 ---
HEALTH_CHECK_INTERVAL_MS = 5000  # 每 5 秒檢查一次
HEALTH_CHECK_TIMEOUT_SECONDS = 10  # 超過 10 秒沒有成功更新視為異常


def activate_app_by_name(app_name):
    """ 使用原生 API 啟用應用程式 """
    apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(app_name)
    if apps:
        apps[0].activateWithOptions_(0)
        return True
    
    all_apps = NSRunningApplication.runningApplications()
    for app in all_apps:
        if app.localizedName() == app_name:
            app.activateWithOptions_(0)
            return True
            
    print(f"找不到名為 '{app_name}' 的應用程式。")
    return False

def get_window_id_by_app_name(app_name):
    options = kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    
    if app_name.lower() in ["音樂", "music", "com.apple.music"]:
        for window in window_list:
            owner_name = window.get('kCGWindowOwnerName', '').lower()
            window_name = window.get('kCGWindowName', '').lower()
            if owner_name in ["music", "音樂"] and window_name:
                return window.get('kCGWindowNumber')
    
    target_app_name_lower = app_name.lower()
    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName', '').lower()
        if owner_name == target_app_name_lower:
            return window.get('kCGWindowNumber')
            
    return None

class WindowMonitor:
    def __init__(self, root, start_x, start_y, start_width, start_alpha):
        self.root = root
        self.initial_x = start_x
        self.initial_y = start_y
        self.current_width = start_width
        self.current_alpha = start_alpha
        self.target_id = None
        self.activated_this_cycle = False
        
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.resize_start_x = 0
        self.resize_start_width = 0
        self.last_aspect_ratio = 16 / 9

        # --- 新增：心跳計時器 ---
        self.last_successful_update = time.time()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", self.current_alpha)
        
        initial_height = int(start_width / self.last_aspect_ratio)
        self.root.geometry(f"{start_width}x{initial_height}+{start_x}+{start_y}")

        self.preview_label = tk.Label(root, bg="black", fg="white", text=f"正在搜尋\n'{TARGET_APP_NAME}'...")
        self.preview_label.pack(fill="both", expand=True)

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "assets", "img", "btn-close.png")
            img = Image.open(image_path).resize(BUTTON_SIZE, Image.Resampling.LANCZOS)
            self.close_button_image = ImageTk.PhotoImage(img)
        except FileNotFoundError:
            self.close_button_image = None
        
        self.close_button = tk.Button(self.root, command=self.root.destroy, relief="flat", borderwidth=0, highlightthickness=0)
        if self.close_button_image:
            self.close_button.config(image=self.close_button_image, width=BUTTON_SIZE[0], height=BUTTON_SIZE[1], bg="black", activebackground="black")
        else:
            self.close_button.config(text="✕", font=("Arial", 9), fg="white", bg="#333333")

        self.resize_grip = tk.Label(self.root, bg="#555555", cursor="sizing")
        
        self.alpha_slider = tk.Scale(
            self.root, from_=MIN_ALPHA_VALUE, to=100, orient=tk.HORIZONTAL,
            command=self.set_alpha, showvalue=0, relief="flat", borderwidth=0,
            highlightthickness=0, sliderlength=10, width=2, bg="#222222", troughcolor="#555555"
        )
        self.alpha_slider.set(self.current_alpha * 100)

        self.root.bind("<Enter>", self.show_controls)
        self.root.bind("<Leave>", self.hide_controls)
        self.preview_label.bind("<ButtonPress-1>", self.start_drag)
        self.preview_label.bind("<B1-Motion>", self.do_drag)
        self.preview_label.bind("<ButtonRelease-1>", self.stop_drag)
        self.resize_grip.bind("<ButtonPress-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.do_resize)
        self.resize_grip.bind("<ButtonRelease-1>", self.stop_resize)

        print(f"懸浮視窗已啟動，正在尋找 '{TARGET_APP_NAME}'...")
        self.hide_controls(None)
        self.root.after(REFRESH_RATE_MS, self.update_preview)
        # --- 新增：啟動健康狀況檢查迴圈 ---
        self.root.after(HEALTH_CHECK_INTERVAL_MS, self.check_health)

    def show_controls(self, event):
        self.close_button.place(relx=1.0, rely=0.0, anchor='ne')
        self.resize_grip.place(relx=1.0, rely=1.0, anchor='se', width=9, height=9)
        self.alpha_slider.place(relx=0.5, rely=1.0, y=-3, x=-4.2, anchor='s', relwidth=0.88)
        self.close_button.lift()
        self.resize_grip.lift()

    def hide_controls(self, event):
        self.close_button.place_forget()
        self.resize_grip.place_forget()
        self.alpha_slider.place_forget()

    def start_drag(self, event): self.drag_start_x, self.drag_start_y = event.x, event.y
    def do_drag(self, event):
        self.root.geometry(f"+{self.root.winfo_x() + (event.x - self.drag_start_x)}+{self.root.winfo_y() + (event.y - self.drag_start_y)}")
    def stop_drag(self, event): self.save_config()

    def start_resize(self, event):
        self.resize_start_x = event.x_root
        self.resize_start_width = self.root.winfo_width()
    def do_resize(self, event):
        delta_x = event.x_root - self.resize_start_x
        new_width = self.resize_start_width + delta_x
        if new_width >= MIN_PREVIEW_WIDTH:
            new_height = int(new_width / self.last_aspect_ratio)
            self.root.geometry(f"{new_width}x{new_height}")
    def stop_resize(self, event): self.save_config()
    
    def set_alpha(self, value):
        alpha_value = int(value) / 100.0
        self.root.attributes("-alpha", alpha_value)
        self.current_alpha = alpha_value
    
    def save_config(self):
        config = {'x': self.root.winfo_x(), 'y': self.root.winfo_y(), 'width': self.root.winfo_width(), 'alpha': self.current_alpha}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"儲存設定失敗: {e}")

    def capture_window(self, window_id):
        try:
            cg_image = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, window_id, kCGWindowImageBoundsIgnoreFraming)
            if not cg_image: return None
            width = CGImageGetWidth(cg_image); height = CGImageGetHeight(cg_image)
            if width <= (MANUAL_CROP_LEFT + MANUAL_CROP_RIGHT) or height <= (MANUAL_CROP_TOP + MANUAL_CROP_BOTTOM): return None
            provider = CGImageGetDataProvider(cg_image)
            data = CGDataProviderCopyData(provider)
            stride = CGImageGetBytesPerRow(cg_image)
            return Image.frombytes("RGBA", (width, height), data, "raw", "BGRA", stride)
        except Exception as e:
            print(f"擷取視窗時發生錯誤: {e}")
            return None
    
    def update_preview(self):
        if self.target_id is None:
            self.target_id = get_window_id_by_app_name(TARGET_APP_NAME)
            if self.target_id is None:
                self.preview_label.config(image=None, text=f"正在搜尋\n'{TARGET_APP_NAME}'...", fg="white", bg="black")
                self.root.after(2000, self.update_preview)
                return
            else:
                print(f"成功找到 '{TARGET_APP_NAME}' 的視窗 ID: {self.target_id}")

        pil_image = self.capture_window(self.target_id)
        
        if pil_image:
            self.activated_this_cycle = False
            try:
                box = (MANUAL_CROP_LEFT, MANUAL_CROP_TOP, pil_image.width - MANUAL_CROP_RIGHT, pil_image.height - MANUAL_CROP_BOTTOM)
                cropped_image = pil_image.crop(box)
                img_w, img_h = cropped_image.size
                
                if img_w > 0 and img_h > 0:
                    self.last_aspect_ratio = img_w / img_h
                    current_win_width = self.root.winfo_width()
                    new_height = int(current_win_width / self.last_aspect_ratio)
                    if abs(new_height - self.root.winfo_height()) > 1:
                        self.root.geometry(f"{current_win_width}x{new_height}")

                preview_width, preview_height = self.root.winfo_width(), self.root.winfo_height()
                if preview_width > 0 and preview_height > 0:
                    cropped_image.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(cropped_image)
                    self.preview_label.config(image=photo, text="")
                    self.preview_label.image = photo
                    
                    # --- 修改：更新心跳時間戳 ---
                    self.last_successful_update = time.time()

            except (ValueError, SystemError) as e:
                print(f"裁切或顯示圖片時發生錯誤: {e}")
            
            self.root.after(REFRESH_RATE_MS, self.update_preview)
        
        else:
            if not self.activated_this_cycle:
                print(f"--- 擷取失敗，嘗試啟用 '{TARGET_APP_NAME}' ---")
                if activate_app_by_name(TARGET_APP_NAME):
                    self.activated_this_cycle = True; self.root.after(500, self.update_preview)
                else:
                    self.root.after(2000, self.update_preview)
            else:
                self.target_id = None; self.root.after(2000, self.update_preview)

    # --- 新增：健康檢查方法 ---
    def check_health(self):
        """定期檢查程式是否仍在正常更新，若否則觸發重啟。"""
        time_since_last_update = time.time() - self.last_successful_update
        
        if time_since_last_update > HEALTH_CHECK_TIMEOUT_SECONDS:
            print(f"警告: 距離上次成功更新已超過 {time_since_last_update:.1f} 秒。觸發程式重啟...")
            self.restart_application()
        else:
            # 若正常，則預約下一次檢查
            self.root.after(HEALTH_CHECK_INTERVAL_MS, self.check_health)

    # --- 新增：重啟應用程式方法 ---
    def restart_application(self):
        """儲存目前設定並重啟程式。"""
        self.save_config()
        
        # 取得 python 直譯器路徑和腳本參數
        python = sys.executable
        os.execv(python, ['python'] + sys.argv)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return (config.get('x', DEFAULT_X_POS), config.get('y', DEFAULT_Y_POS),
                        config.get('width', DEFAULT_PREVIEW_WIDTH), config.get('alpha', DEFAULT_ALPHA))
        except (json.JSONDecodeError, IOError):
            pass
    return DEFAULT_X_POS, DEFAULT_Y_POS, DEFAULT_PREVIEW_WIDTH, DEFAULT_ALPHA

def main():
    start_x, start_y, start_width, start_alpha = load_config()
    root = tk.Tk()
    app = WindowMonitor(root, start_x, start_y, start_width, start_alpha)
    root.mainloop()

if __name__ == '__main__':
    main()