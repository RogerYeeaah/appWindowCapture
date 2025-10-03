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
    kCGWindowImageBoundsIgnoreFraming
)

# ===================================================================
# --- 使用者設定 ---
# ===================================================================
TARGET_WINDOW_ID = 20540
PREVIEW_BASE_WIDTH = 130
DEFAULT_X_POS = 50
DEFAULT_Y_POS = 50
REFRESH_RATE_MS = 50
CONFIG_FILE = "monitor_config.json"

# --- 手動修正設定 ---
MANUAL_CROP_VERTICAL = 0
MANUAL_CROP_HORIZONTAL = 0 
# ===================================================================

class WindowMonitor:
    def __init__(self, root, start_x, start_y):
        self.root = root
        # *** 核心修正 1：將讀取到的初始位置儲存起來 ***
        self.initial_x = start_x
        self.initial_y = start_y
        
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.last_known_adjusted_width = 0
        self.last_known_adjusted_height = 0

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.geometry(f"10x10+{start_x}+{start_y}") # 初始放置在讀取到的位置

        self.preview_label = tk.Label(root, bg="black")
        self.preview_label.pack(fill="both", expand=True)

        self.preview_label.bind("<ButtonPress-1>", self.start_drag)
        self.preview_label.bind("<B1-Motion>", self.do_drag)
        self.preview_label.bind("<ButtonRelease-1>", self.stop_drag)

        print("懸浮視窗已啟動。")
        self.update_preview()

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
        # ... (儲存邏輯不變) ...
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        config = {'x': current_x, 'y': current_y}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"儲存位置失敗: {e}")

    def capture_window(self):
        # ... (擷取邏輯不變) ...
        try:
            cg_image = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, TARGET_WINDOW_ID, kCGWindowImageBoundsIgnoreFraming)
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
        pil_image = self.capture_window()
        if pil_image:
            # ... (裁切邏輯不變) ...
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
            except ValueError:
                self.root.after(REFRESH_RATE_MS, self.update_preview)
                return

            img_w, img_h = cropped_image.size
            
            if img_w != self.last_known_adjusted_width or img_h != self.last_known_adjusted_height:
                is_first_resize = (self.last_known_adjusted_width == 0)
                
                self.last_known_adjusted_width = img_w
                self.last_known_adjusted_height = img_h
                
                if img_h > 0:
                    aspect_ratio = img_w / img_h
                    new_height = int(PREVIEW_BASE_WIDTH / aspect_ratio)
                    
                    # *** 核心修正 2：判斷是否為第一次調整尺寸 ***
                    if is_first_resize:
                        # 第一次，強制使用從檔案讀取的位置
                        x_pos = self.initial_x
                        y_pos = self.initial_y
                    else:
                        # 非第一次 (是使用者縮放了Music視窗)，使用當前位置以維持拖動效果
                        x_pos = self.root.winfo_x()
                        y_pos = self.root.winfo_y()
                        
                    self.root.geometry(f"{PREVIEW_BASE_WIDTH}x{new_height}+{x_pos}+{y_pos}")

            # ... (顯示圖片的邏輯不變) ...
            preview_width = self.root.winfo_width()
            preview_height = self.root.winfo_height()
            cropped_image.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(cropped_image)
            self.preview_label.config(image=photo, text="")
            self.preview_label.image = photo
        else:
            self.preview_label.config(image=None, text=f"找不到視窗\nID: {TARGET_WINDOW_ID}", fg="white", bg="black")
        
        self.root.after(REFRESH_RATE_MS, self.update_preview)

def load_config():
    # ... (讀取邏輯不變) ...
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