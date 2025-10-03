# macOS 即時視窗擷取工具 (Real-time Window Capture for macOS)

這是一個 macOS 專用的 Python 工具，它可以鎖定一個特定應用程式的視窗（即使它在背景或其他桌面），並將其內容即時投射到一個可拖動、置頂的懸浮視窗中。

此工具特別適用於需要監控特定視窗內容的場景，例如：
* 監控歌詞軟體的即時歌詞。
* 觀看影片時，將字幕區域單獨擷取出來。
* 監控背景執行的程式狀態。



---

## ✨ 功能特色

* **背景擷取**：可擷取不在前景、被遮擋或位於其他虛擬桌面 (Space) 的視窗內容。
* **即時預覽**：以高更新率將擷取內容顯示在一個懸浮視窗中。
* **精確裁切**：支援手動設定裁切參數，可從原始視窗中精確提取特定區域。
* **動態適應**：懸浮視窗的長寬比會自動根據擷取內容的尺寸變化而調整。
* **自由拖動**：懸浮視窗沒有邊框，但可以用滑鼠自由拖動到螢幕任何位置。
* **位置記憶**：自動儲存懸浮視窗的最後位置，下次啟動時會自動恢復。

---

## 🛠️ 安裝與設定指南

本專案建議在 Python 虛擬環境中執行。

### 1. 環境準備

* **macOS 作業系統** (必要)
* **Python 3.9+** (建議)

首先，打開您的終端機 (Terminal)，進入專案目錄，並建立一個虛擬環境。

```bash
# 進入您的專案資料夾
cd /path/to/your/project

# 建立一個名為 .venv 的虛擬環境
python3 -m venv .venv

# 啟用虛擬環境
source .venv/bin/activate
```

### 2. 安裝依賴套件

在啟用虛擬環境的狀態下，安裝所有必要的 Python 套件。

```bash
pip install pyobjc pillow
```

### 3. 設定系統權限

由於此工具涉及螢幕擷取，您必須手動授予執行它的應用程式（通常是**終端機 Terminal.app** 或您的程式碼編輯器如 **VS Code**)「**螢幕錄製 (Screen Recording)**」的權限。

* 前往 **系統設定 (System Settings)** > **隱私權與安全性 (Privacy & Security)**。
* 在右側找到並點擊 **螢幕錄製 (Screen Recording)**。
* 將您的**終端機 (Terminal)** 或其他執行工具加入列表並啟用開關。

**注意：若未設定此權限，擷取到的畫面將會是空白或只有桌面背景。**

---

## 🚀 使用方法

### 1. 設定腳本參數

打開主程式檔案 ( `screen_translator.py`)，修改最上方的「使用者設定」區塊。

```python
# ===================================================================
# --- 使用者設定 ---
# ===================================================================
# !!【必要】請填入您想監控的視窗 ID (Apple Music: 20540)
TARGET_WINDOW_ID = 20540

# 懸浮視窗的「基礎寬度」，高度將依此自動調整
PREVIEW_BASE_WIDTH = 120

# 首次啟動時的預設位置
DEFAULT_X_POS = 50
DEFAULT_Y_POS = 50

# 更新頻率 (毫秒)，數值越小越流暢，也越耗 CPU
REFRESH_RATE_MS = 50

# --- 手動修正設定 ---
# 透過反覆測試來微調這些數值，以裁切掉多餘的邊緣
# 從垂直方向總共要裁切掉的像素
MANUAL_CROP_VERTICAL = 240
# 從水平方向總共要裁切掉的像素
MANUAL_CROP_HORIZONTAL = 230 

# 您在程式碼中使用的非對稱裁切邏輯，也可以在此說明
# 例如：box = (left_crop, top_crop, right_crop, bottom_crop)
# ...
# ===================================================================
```

* **`TARGET_WINDOW_ID`**：**最重要**的參數，請務必填寫正確。
* **`PREVIEW_BASE_WIDTH`**：決定了懸浮視窗的基礎寬度。
* **`MANUAL_CROP_*`**：用於精確裁切。如果擷取畫面周圍有多餘的內容，請調整這些數值。

### 3. 執行程式

在終端機中（確保虛擬環境已啟用），執行主程式。

```bash
python3 your_script_name.py
```

### 4. 操作懸浮視窗

* **移動**：用滑鼠左鍵按住懸浮視窗即可拖動。
* **儲存位置**：放開滑鼠後，視窗的目前位置會自動儲存到 `monitor_config.json` 檔案中。
* **關閉**：切換到執行腳本的終端機，按下 `Control` + `C`。

---

## 📦 打包方法
### 步驟一：建立並啟用虛擬環境

為您的專案建立一個獨立的 Python 環境，以隔離打包所需的依賴套件。

```bash
# 1. 建立 venv (使用您的 Python 3.11)
python3.11 -m venv .venv-py311

# 2. 啟用 venv (macOS / Linux)
source .venv-py311/bin/activate
```
啟用成功後，您的終端機提示字元前會出現 `(.venv-py311)`。

### 步驟二：安裝套件 (包含 py2app)

在已啟用的環境中，安裝 `py2app` 以及您應用程式需要的所有其他套件。

```bash
# 將 YourPackage1 YourPackage2 換成您專案的實際依賴
pip install py2app YourPackage1 YourPackage2
```

### 步驟三：建立 `setup.py` 設定檔

`py2app` 透過 `setup.py` 檔案來獲取打包設定。在您的專案根目錄建立此檔案。

```python
# setup.py
from setuptools import setup

APP = ['main.py'] # 您的主程式檔案
DATA_FILES = [] # 需要包含的額外檔案 (如圖片、設定檔)
OPTIONS = {
    'packages': ['requests', 'numpy'], # 明確需要包含的套件
    'iconfile': 'app_icon.icns', # 應用程式圖示 (可選)
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

### 步驟四：執行打包指令

一切就緒後，執行 `py2app` 指令來建立您的應用程式。

```bash
# 確保您仍在啟用的 venv 環境中
python setup.py py2app
```

打包成功後，您會在專案目錄下看到新增的 `build/` 和 `dist/` 資料夾。您最終的獨立應用程式 `.app` 檔案就在 `dist/` 資料夾中。

## 📝 授權

本專案採用 MIT 授權。