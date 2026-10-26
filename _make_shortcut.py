# -*- coding: utf-8 -*-
"""在桌面为 PNG转JPG.exe 创建快捷方式（标准 IShellLink 用法）。"""
import os

import pythoncom
import win32com.client

ws = win32com.client.Dispatch("WScript.Shell")
desktop = ws.SpecialFolders("Desktop")
path = os.path.join(desktop, "PNG转JPG.lnk")
sc = ws.CreateShortcut(path)
sc.TargetPath = r"E:\png转jpg应用\PNG转JPG.exe"
sc.WorkingDirectory = r"E:\png转jpg应用"
sc.IconLocation = r"E:\png转jpg应用\PNG转JPG.exe,0"
sc.Description = "PNG 转 JPG 批量转换小工具"
sc.Save()
print("快捷方式已创建:", path, "| 存在:", os.path.exists(path))
