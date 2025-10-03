#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
import json
import os
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

# ===================================================================
# --- 使用者設定 ---
# ===================================================================
TARGET_APP_NAME = "音樂" 
PREVIEW_BASE_WIDTH = 140
# === 新增：按鈕大小設定 ===
BUTTON_SIZE = (16, 16)  # 按鈕的 (寬, 高)，單位是像素
# ===================================================================
DEFAULT_X_POS = 50
DEFAULT_Y_POS = 50
REFRESH_RATE_MS = 50
CONFIG_FILE = "monitor_config.json"
MANUAL_CROP_VERTICAL = 0
MANUAL_CROP_HORIZONTAL = 0 
# ===================================================================


def get_window_id_by_app_name(app_name):
    options = kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    target_app_name_lower = app_name.lower()
    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName')
        window_name = window.get('kCGWindowName')
        if owner_name and window_name:
            if owner_name.lower() == target_app_name_lower and target_app_name_lower in window_name.lower():
                return window.get('kCGWindowNumber')
    return None

class WindowMonitor:
    def __init__(self, root, start_x, start_y):
        self.root = root
        self.initial_x = start_x
        self.initial_y = start_y
        self.target_id = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_known_adjusted_width = 0
        self.last_known_adjusted_height = 0

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"{PREVIEW_BASE_WIDTH}x{int(PREVIEW_BASE_WIDTH*0.6)}+{start_x}+{start_y}")

        self.preview_label = tk.Label(root, bg="black", fg="white", text=f"正在搜尋\n'{TARGET_APP_NAME}'...")
        self.preview_label.pack(fill="both", expand=True)

        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(script_dir, "assets", "img", "btn-bg.png")
            
            img = Image.open(image_path)
            img = img.resize(BUTTON_SIZE, Image.Resampling.LANCZOS)
            self.close_button_image = ImageTk.PhotoImage(img)

        except FileNotFoundError:
            print(f"警告：找不到圖片檔案於 '{image_path}'，將使用純色背景按鈕。")
            self.close_button_image = None
        
        # === 核心修改：簡化按鈕設定，移除所有文字相關選項 ===
        self.close_button = tk.Button(
            self.root, 
            command=self.root.destroy,
            relief="flat",
            borderwidth=0,
            highlightthickness=0
        )

        if self.close_button_image:
            self.close_button.config(
                image=self.close_button_image,
                width=BUTTON_SIZE[0],
                height=BUTTON_SIZE[1],
                bg="black",
                # 將點擊時的背景也設為黑色，徹底消除白邊
                activebackground="black" 
            )
        else:
            # 備用方案，如果找不到圖片
            self.close_button.config(text="✕", font=("Arial", 9), fg="white", bg="#333333")

        self.root.bind("<Enter>", self.show_close_button)
        self.preview_label.bind("<Enter>", self.show_close_button)
        self.root.bind("<Leave>", self.hide_close_button)

        self.preview_label.bind("<ButtonPress-1>", self.start_drag)
        self.preview_label.bind("<B1-Motion>", self.do_drag)
        self.preview_label.bind("<ButtonRelease-1>", self.stop_drag)

        print(f"懸浮視窗已啟動，正在尋找 '{TARGET_APP_NAME}'...")
        self.update_preview()

    def show_close_button(self, event):
        self.close_button.place(relx=1.0, rely=0.0, anchor='ne')
        self.close_button.lift()

    def hide_close_button(self, event):
        self.close_button.place_forget()

    def start_drag(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def do_drag(self, event):
        deltax = event.x - self.drag_start_x
        deltay = event.y - self.drag_start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        config = {'x': current_x, 'y': current_y}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"儲存位置失敗: {e}")

    def capture_window(self, window_id):
        try:
            cg_image = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, window_id, kCGWindowImageBoundsIgnoreFraming)
            if not cg_image: return None
            width = CGImageGetWidth(cg_image)
            height = CGImageGetHeight(cg_image)
            if width <= MANUAL_CROP_HORIZONTAL or height <= MANUAL_CROP_VERTICAL: return None
            stride = CGImageGetBytesPerRow(cg_image)
            provider = CGImageGetDataProvider(cg_image)
            data = CGDataProviderCopyData(provider)
            return Image.frombytes("RGBA", (width, height), data, "raw", "BGRA", stride)
        except Exception:
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
            cropped_image = None
            try:
                crop_h_each_side = MANUAL_CROP_HORIZONTAL // 2
                crop_v_each_side = MANUAL_CROP_VERTICAL // 2
                box = (
                    crop_h_each_side + 1360, crop_v_each_side + 100,
                    pil_image.width - crop_h_each_side, 
                    pil_image.height - crop_v_each_side - 240
                )
                cropped_image = pil_image.crop(box)
            except (ValueError, SystemError):
                self.root.after(REFRESH_RATE_MS, self.update_preview)
                return

            img_w, img_h = cropped_image.size
            
            if img_w != self.last_known_adjusted_width or img_h != self.last_known_adjusted_height:
                is_first_resize = (self.last_known_adjusted_width == 0)
                self.last_known_adjusted_width, self.last_known_adjusted_height = img_w, img_h
                if img_h > 0:
                    aspect_ratio = img_w / img_h
                    new_height = int(PREVIEW_BASE_WIDTH / aspect_ratio)
                    x_pos = self.initial_x if is_first_resize else self.root.winfo_x()
                    y_pos = self.initial_y if is_first_resize else self.root.winfo_y()
                    self.root.geometry(f"{PREVIEW_BASE_WIDTH}x{new_height}+{x_pos}+{y_pos}")

            preview_width, preview_height = self.root.winfo_width(), self.root.winfo_height()
            if preview_width > 0 and preview_height > 0:
                cropped_image.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(cropped_image)
                self.preview_label.config(image=photo, text="")
                self.preview_label.image = photo
        else:
            print(f"視窗 ID {self.target_id} 已失效，重新開始搜尋...")
            self.target_id = None
            self.last_known_adjusted_width = 0
        
        self.root.after(REFRESH_RATE_MS, self.update_preview)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                return config.get('x', DEFAULT_X_POS), config.get('y', DEFAULT_Y_POS)
        except (json.JSONDecodeError, IOError):
            return DEFAULT_X_POS, DEFAULT_Y_POS
    return DEFAULT_X_POS, DEFAULT_Y_POS

def main():
    start_x, start_y = load_config()
    root = tk.Tk()
    app = WindowMonitor(root, start_x, start_y)
    root.mainloop()

if __name__ == '__main__':
    main()