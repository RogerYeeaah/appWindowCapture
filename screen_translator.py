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
    # === 新增：匯入尋找視窗所需的選項 ===
    CGWindowListCopyWindowInfo, 
    kCGWindowListOptionAll,
    kCGWindowListExcludeDesktopElements, 
    kCGNullWindowID
)

# ===================================================================
# --- 使用者設定 ---
# ===================================================================
# *** 核心修改：現在只需要設定應用程式名稱 ***
TARGET_APP_NAME = "音樂" # 例如 "Music", "Google Chrome", "Spotify"
# ===================================================================
PREVIEW_BASE_WIDTH = 130
DEFAULT_X_POS = 50
DEFAULT_Y_POS = 50
REFRESH_RATE_MS = 50
CONFIG_FILE = "monitor_config.json"

# --- 手動修正設定 ---
MANUAL_CROP_VERTICAL = 0
MANUAL_CROP_HORIZONTAL = 0 
# ===================================================================


# === 新增：從 find_window_id.py 移植過來的函式 ===
def get_window_id_by_app_name(app_name):
    """
    根據應用程式名稱 (owner_name) 和視窗標題 (window_name) 尋找視窗 ID。
    """
    options = kCGWindowListOptionAll | kCGWindowListExcludeDesktopElements
    window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)
    
    target_app_name_lower = app_name.lower()

    for window in window_list:
        owner_name = window.get('kCGWindowOwnerName')
        # 新增：同時獲取視窗標題 (window_name)
        window_name = window.get('kCGWindowName')
        
        # 檢查 owner_name 和 window_name 是否存在
        if owner_name and window_name:
            
            ## --- 方案一：嚴格相等 (依您的要求，但可能因視窗標題變化而找不到) --- ##
            # 說明：要求 owner_name 和 window_name 都必須與 TARGET_APP_NAME 完全相同。
            # if owner_name.lower() == target_app_name_lower and window_name.lower() == target_app_name_lower:
            #     return window.get('kCGWindowNumber')

            ## --- 方案二：寬鬆包含 (更推薦，適應性更強) --- ##
            # 說明：要求 owner_name 必須相符，且 window_name 必須包含 TARGET_APP_NAME。
            # 例如 app_name 是 "Music"，可以成功匹配 "音樂" 或 "播放列表 - Music" 等標題。
            if owner_name.lower() == target_app_name_lower and target_app_name_lower in window_name.lower():
                return window.get('kCGWindowNumber')
            
    return None # 如果找不到，返回 None

class WindowMonitor:
    def __init__(self, root, start_x, start_y):
        self.root = root
        self.initial_x = start_x
        self.initial_y = start_y
        
        # === 新增：用來儲存動態找到的視窗 ID ===
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

        # 綁定拖曳事件
        self.preview_label.bind("<ButtonPress-1>", self.start_drag)
        self.preview_label.bind("<B1-Motion>", self.do_drag)
        self.preview_label.bind("<ButtonRelease-1>", self.stop_drag)

        print(f"懸浮視窗已啟動，正在尋找 '{TARGET_APP_NAME}'...")
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
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        config = {'x': current_x, 'y': current_y}
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"儲存位置失敗: {e}")

    # *** 核心修改：capture_window 現在接收一個 ID 作為參數 ***
    def capture_window(self, window_id):
        try:
            cg_image = CGWindowListCreateImage(CGRectNull, kCGWindowListOptionIncludingWindow, window_id, kCGWindowImageBoundsIgnoreFraming)
            if not cg_image: return None
            # ... 後續程式碼不變 ...
            width = CGImageGetWidth(cg_image)
            height = CGImageGetHeight(cg_image)
            if width <= MANUAL_CROP_HORIZONTAL or height <= MANUAL_CROP_VERTICAL: return None
            stride = CGImageGetBytesPerRow(cg_image)
            provider = CGImageGetDataProvider(cg_image)
            data = CGDataProviderCopyData(provider)
            return Image.frombytes("RGBA", (width, height), data, "raw", "BGRA", stride)
        except Exception:
            return None

    # *** 核心修改：update_preview 加入了自動搜尋和狀態管理的邏輯 ***
    def update_preview(self):
        # 步驟 1: 如果還沒有 ID，就去尋找
        if self.target_id is None:
            self.target_id = get_window_id_by_app_name(TARGET_APP_NAME)
            # 如果還是找不到，顯示提示訊息並在 2 秒後重試
            if self.target_id is None:
                self.preview_label.config(image=None, text=f"正在搜尋\n'{TARGET_APP_NAME}'...", fg="white", bg="black")
                self.root.after(2000, self.update_preview) # 找不到時，放慢更新頻率
                return
            else:
                print(f"成功找到 '{TARGET_APP_NAME}' 的視窗 ID: {self.target_id}")

        # 步驟 2: 如果有 ID，就嘗試擷取畫面
        pil_image = self.capture_window(self.target_id)
        
        # 步驟 3: 根據擷取結果更新畫面
        if pil_image:
            cropped_image = None
            try:
                # 裁切邏輯
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
            
            # 調整視窗大小
            if img_w != self.last_known_adjusted_width or img_h != self.last_known_adjusted_height:
                is_first_resize = (self.last_known_adjusted_width == 0)
                self.last_known_adjusted_width, self.last_known_adjusted_height = img_w, img_h
                if img_h > 0:
                    aspect_ratio = img_w / img_h
                    new_height = int(PREVIEW_BASE_WIDTH / aspect_ratio)
                    x_pos = self.initial_x if is_first_resize else self.root.winfo_x()
                    y_pos = self.initial_y if is_first_resize else self.root.winfo_y()
                    self.root.geometry(f"{PREVIEW_BASE_WIDTH}x{new_height}+{x_pos}+{y_pos}")

            # 顯示圖片
            preview_width, preview_height = self.root.winfo_width(), self.root.winfo_height()
            if preview_width > 0 and preview_height > 0:
                cropped_image.thumbnail((preview_width, preview_height), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(cropped_image)
                self.preview_label.config(image=photo, text="")
                self.preview_label.image = photo
        else:
            # 如果擷取失敗 (例如目標視窗被關閉)，重設 ID 並回到搜尋狀態
            print(f"視窗 ID {self.target_id} 已失效，重新開始搜尋...")
            self.target_id = None
            self.last_known_adjusted_width = 0 # 重設尺寸記錄
        
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