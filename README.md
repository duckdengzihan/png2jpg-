# PNG 转 JPG

一个极简的 Windows 批量图片转换小工具：把 PNG 一键转成 JPG，压缩质量可自己调。

界面只有三件事——选文件、拖滑块、点开始转换，没有 Lightroom 那种层层叠叠的面板。

![界面风格](https://img.shields.io/badge/UI-极简-blue) ![平台](https://img.shields.io/badge/Windows-10%2F11-lightgrey) ![Python](https://img.shields.io/badge/Python-3.10%2B-yellow)

## 功能

- **批量转换**：一次选多个文件，或直接选整个文件夹（会递归查找所有 PNG）
- **拖拽导入**：把 PNG 文件 / 文件夹直接拖进窗口即可
- **压缩质量可调**：滑块 10–100（默认 85），实时提示「文件最小 / 均衡 / 画质优先」
- **透明背景自动填白**：PNG 的透明区域转成 JPG 时填充为白色，不会变黑块
- **保存位置可选**：保存在原文件夹，或统一输出到指定文件夹
- **小窗口可滚动**：窗口缩小时页面自动出现滚动条，不会看不到底部按钮
- **完成后自动打开输出文件夹**；同批次重名文件自动加 `(2)` 后缀

## 使用

1. 从 [Releases](../../releases) 下载 `PNG转JPG.exe`
2. 双击运行（首次可能触发 Windows SmartScreen，点「更多信息 → 仍要运行」）
3. 添加 PNG → 调质量 → 点「开始转换」

## 从源码运行

```bash
python -m venv venv
venv\Scripts\pip install pillow tkinterdnd2 -i https://mirrors.aliyun.com/pypi/simple/
venv\Scripts\python png2jpg.py
```

> 需要自带 tkinter 的 Python（python.org 官方安装包默认包含）。

## 打包为单文件 exe

```bash
venv\Scripts\pip install pyinstaller -i https://mirrors.aliyun.com/pypi/simple/
venv\Scripts\python -m PyInstaller --noconfirm --onefile --windowed ^
  --name "PNG转JPG" --icon icon.ico ^
  --add-data "icon.ico;." --collect-all tkinterdnd2 ^
  --distpath . --workpath _build --specpath _build png2jpg.py
```

## 目录结构

```
png2jpg.py          # 主程序（tkinter 界面 + Pillow 转换逻辑）
icon.ico            # 应用图标
_make_icon.py       # 图标生成脚本（Pillow 绘制）
_selftest.py        # 转换逻辑自测：透明填白、质量参数验证
_make_shortcut.py   # 创建桌面快捷方式（pywin32）
```

## 技术说明

- 界面：tkinter（标准库，无需额外 GUI 框架）
- 转换：Pillow，`quality` 参数直接对应 JPEG 压缩质量
- 拖拽：tkinterdnd2
- 滚动：Canvas + 内部 Frame，按内容高度动态计算 `scrollregion`

## License

MIT
