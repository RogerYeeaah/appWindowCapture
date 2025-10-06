from setuptools import setup
from glob import glob

APP = ['screen_translator.py']
APP_NAME = "APMLyrics"

DATA_FILES = [
    ('assets/img', glob('assets/img/*.png'))
]

# --- py2app 選項設定 ---
OPTIONS = {
    'argv_emulation': False,
    'iconfile': 'assets/img/icon.png',
    'packages': ['PIL'],
    'includes': ['jaraco.text', 'imp'],
    'excludes': [
        'pytest', 'IPython', 'PyQt6', 'PySide6', 'numpy', 
        'jaraco.tests', 
        'pkg_resources.tests'
    ],
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleGetInfoString': "Monitors a specific window",
        'CFBundleIdentifier': "com.Roger.osx.aplyrics",
        'CFBundleVersion': "0.1.0",
        'CFBundleShortVersionString': "0.1.0",
        'NSHumanReadableCopyright': u"Copyright © 2025, Roger, All Rights Reserved",
        'NSScreenCaptureDescription': 'This app needs to capture the screen to display the window preview.',
        'NSAppleEventsUsageDescription': '本應用程式需要控制「音樂」App，以確保其視窗內容可供擷取。',
    }
}

# --- 主設定函式 ---
setup(
    app=APP,
    name=APP_NAME,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)