# -*- coding: utf-8 -*-
"""PNG 转 JPG 小工具 —— 简洁的批量转换器

三步走：选文件（支持直接拖拽）→ 拖滑块设置压缩质量 → 点「开始转换」
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from pathlib import Path
from threading import Thread
from tkinter import filedialog, messagebox, ttk

from PIL import Image

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    HAVE_DND = True
except Exception:
    HAVE_DND = False

APP_TITLE = "PNG 转 JPG"

# 接受常见图片格式作为「转换 / 压缩」的输入
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".tga"}


# ---------------- 核心转换 ----------------

def resource_dir() -> Path:
    """资源目录（兼容 PyInstaller 打包后的路径）。"""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def convert_one(src: Path, dst: Path, quality: int) -> None:
    """把单张图片转成 JPG（透明区域填白）；JPG 重新编码即压缩。"""
    img = Image.open(src)
    img.load()
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A"))
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=quality, optimize=True)


def fmt_bytes(n: float) -> str:
    if n < 1024:
        return f"{int(n)} B"
    n /= 1024
    if n < 1024:
        return f"{n:.0f} KB"
    return f"{n / 1024:.1f} MB"


def file_size(p: Path) -> str:
    try:
        return fmt_bytes(float(p.stat().st_size))
    except OSError:
        return "?"


# ---------------- 界面 ----------------

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("700x680")
        self.root.minsize(520, 400)

        ico = resource_dir() / "icon.ico"
        if ico.exists():
            try:
                self.root.iconbitmap(str(ico))
            except tk.TclError:
                pass

        self.files: list[Path] = []
        self.converting = False

        self._build_style()
        self._build_ui()
        self._on_quality()
        if HAVE_DND:
            self._enable_dnd()
        # 布局完成后再校准一次，避免启动瞬间内容未排版导致滚动区域计算偏小
        self.root.after(50, self._sync_scroll)

    def _build_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Big.TButton", font=("Microsoft YaHei UI", 11, "bold"), padding=(20, 8))
        style.configure("TLabelframe.Label", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Body.TFrame", background="#f4f5f7")

    def _build_ui(self) -> None:
        self.root.configure(bg="#f4f5f7")

        # ---- 可滚动容器：窗口够大时与原布局一致，缩小后自动出现滚动条 ----
        self.canvas = tk.Canvas(self.root, bg="#f4f5f7", highlightthickness=0, bd=0)
        page_sb = ttk.Scrollbar(self.root, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=page_sb.set)
        page_sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.body = ttk.Frame(self.canvas, style="Body.TFrame")
        self.body_win = self.canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._sync_scroll)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel, add="+")

        header = ttk.Frame(self.body, padding=(18, 14, 18, 4))
        header.pack(fill="x")
        ttk.Label(header, text="PNG → JPG", font=("Microsoft YaHei UI", 16, "bold")).pack(side="left")
        ttk.Label(header, text="  选图片 → 调质量 → 一键转换 / 压缩",
                  foreground="#8a8f99").pack(side="left", pady=(6, 0))

        hint_text = ("提示：可以直接把图片（PNG / JPG 等）或整个文件夹拖进窗口"
                     if HAVE_DND else "提示：点击下方按钮选择图片（PNG / JPG 等）")
        ttk.Label(self.body, text=hint_text, foreground="#9aa0a8",
                  padding=(20, 0)).pack(anchor="w")

        bar = ttk.Frame(self.body, padding=(18, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text="选择文件", command=self.add_files).pack(side="left")
        ttk.Button(bar, text="选择文件夹", command=self.add_folder).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="移除选中", command=self.remove_selected).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text="清空", command=self.clear_files).pack(side="left", padx=(8, 0))

        wrap = ttk.Frame(self.body, padding=(18, 4))
        wrap.pack(fill="both", expand=True)
        self.file_list = tk.Listbox(
            wrap, selectmode="extended", font=("Microsoft YaHei UI", 10),
            bg="white", relief="flat", highlightthickness=1,
            highlightbackground="#dcdfe6", activestyle="none",
        )
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=sb.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")

        self.count_label = ttk.Label(self.body, text="尚未选择文件",
                                     foreground="#8a8f99", padding=(20, 2))
        self.count_label.pack(anchor="w")

        # ---- 压缩质量 ----
        qf = ttk.LabelFrame(self.body, text=" 压缩质量 ", padding=(16, 8))
        qf.pack(fill="x", padx=18, pady=(6, 2))
        row = ttk.Frame(qf)
        row.pack(fill="x")
        self.quality = tk.DoubleVar(value=85)
        self.q_value_label = ttk.Label(row, text="85",
                                       font=("Microsoft YaHei UI", 12, "bold"), width=4)
        self.qslider = ttk.Scale(row, from_=10, to=100,
                                 variable=self.quality, command=self._on_quality)
        self.q_hint_label = ttk.Label(row, text="", foreground="#8a8f99")
        self.q_value_label.pack(side="left")
        self.qslider.pack(side="left", fill="x", expand=True, padx=(8, 0))
        self.q_hint_label.pack(side="left", padx=(10, 0))
        ttk.Label(qf, text="参考：60 左右适合网页 / 聊天分享，85 左右适合日常照片存档",
                  foreground="#9aa0a8").pack(anchor="w", pady=(2, 0))

        # ---- 保存位置 ----
        sf = ttk.LabelFrame(self.body, text=" 保存位置 ", padding=(16, 8))
        sf.pack(fill="x", padx=18, pady=(6, 2))
        self.save_mode = tk.StringVar(value="same")
        ttk.Radiobutton(sf, text="保存在原文件所在文件夹", variable=self.save_mode,
                        value="same", command=self._toggle_outdir).pack(anchor="w")
        row2 = ttk.Frame(sf)
        row2.pack(fill="x", pady=(4, 0))
        ttk.Radiobutton(row2, text="统一保存到：", variable=self.save_mode,
                        value="custom", command=self._toggle_outdir).pack(side="left")
        self.outdir_entry = ttk.Entry(row2, state="disabled")
        self.outdir_entry.pack(side="left", fill="x", expand=True, padx=(6, 0))
        ttk.Button(row2, text="浏览…", command=self.browse_outdir, width=8).pack(side="left", padx=(6, 0))
        self.open_after = tk.BooleanVar(value=True)
        ttk.Checkbutton(sf, text="转换完成后自动打开输出文件夹",
                        variable=self.open_after).pack(anchor="w", pady=(3, 0))

        # ---- 底部 ----
        bottom = ttk.Frame(self.body, padding=(18, 10, 18, 12))
        bottom.pack(fill="x")
        self.convert_btn = ttk.Button(bottom, text="开始转换", style="Big.TButton",
                                      command=self.start_convert)
        self.convert_btn.pack(side="left")
        self.status_label = ttk.Label(bottom, text="就绪", foreground="#8a8f99")
        self.status_label.pack(side="left", padx=(14, 0))

    # ---------------- 页面滚动 ----------------

    def _sync_scroll(self, _event=None) -> None:
        """窗口或内容尺寸变化后：适配内容高度 + 更新滚动区域。

        可视区够高 → 内容撑满（文件列表可伸展，与原布局一致）；
        可视区不够高 → 内容保持自然高度，由右侧滚动条接管。
        """
        canvas_h = self.canvas.winfo_height()
        if canvas_h > 1:
            need = max(canvas_h, self.body.winfo_reqheight())
            try:
                cur = int(float(self.canvas.itemcget(self.body_win, "height")))
            except (tk.TclError, ValueError):
                cur = -1
            if cur != need:
                self.canvas.itemconfigure(self.body_win, height=need)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event) -> None:
        self.canvas.itemconfigure(self.body_win, width=event.width)
        self._sync_scroll()

    def _on_mousewheel(self, event) -> None:
        """滚轮滚动页面；悬停在文件列表等自带滚轮交互的控件上时不接管。"""
        w = event.widget
        if not isinstance(w, tk.Widget):
            try:
                w = self.root.nametowidget(str(w))
            except Exception:
                w = None
        if isinstance(w, (tk.Listbox, ttk.Scale, ttk.Scrollbar)):
            return
        self.canvas.yview_scroll(-int(event.delta / 120), "units")

    # ---------------- 拖拽 ----------------

    def _enable_dnd(self) -> None:
        for widget in (self.root, self.canvas, self.file_list):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._on_drop)

    def _on_drop(self, event) -> None:
        self._add_paths(self.root.tk.splitlist(event.data))

    # ---------------- 文件管理 ----------------

    def add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择图片文件（PNG / JPG 等）",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.tga"),
                ("PNG 图片", "*.png"),
                ("JPG 图片", "*.jpg *.jpeg"),
                ("所有文件", "*.*"),
            ],
        )
        self._add_paths(paths)

    def add_folder(self) -> None:
        d = filedialog.askdirectory(title="选择文件夹（将添加其中所有图片）")
        if d:
            self._add_paths([d])

    def _add_paths(self, paths) -> int:
        added = 0
        for p in paths:
            p = Path(p)
            if p.is_dir():
                added += self._add_paths(sorted(
                    x for x in p.rglob("*")
                    if x.is_file() and x.suffix.lower() in IMAGE_EXTS
                ))
                continue
            if p.suffix.lower() not in IMAGE_EXTS or not p.is_file():
                continue
            if p in self.files:
                continue
            self.files.append(p)
            self.file_list.insert("end", f"{p}  （{file_size(p)}）")
            added += 1
        self._refresh_count()
        return added

    def remove_selected(self) -> None:
        for i in sorted(self.file_list.curselection(), reverse=True):
            self.file_list.delete(i)
            del self.files[i]
        self._refresh_count()

    def clear_files(self) -> None:
        self.files.clear()
        self.file_list.delete(0, "end")
        self._refresh_count()

    def _refresh_count(self) -> None:
        n = len(self.files)
        if n == 0:
            self.count_label.configure(text="尚未选择文件")
            self._sync_scroll()
            return
        total = 0.0
        for f in self.files:
            try:
                total += f.stat().st_size
            except OSError:
                pass
        self.count_label.configure(text=f"共 {n} 个文件，合计 {fmt_bytes(total)}")
        self._sync_scroll()

    # ---------------- 参数 ----------------

    def _on_quality(self, _=None) -> None:
        q = int(self.quality.get())
        self.q_value_label.configure(text=str(q))
        if q <= 45:
            hint = "文件最小，画质一般"
        elif q <= 70:
            hint = "体积与画质均衡"
        else:
            hint = "画质优先，文件较大"
        self.q_hint_label.configure(text=hint)

    def _toggle_outdir(self) -> None:
        state = "normal" if self.save_mode.get() == "custom" else "disabled"
        self.outdir_entry.configure(state=state)

    def browse_outdir(self) -> None:
        d = filedialog.askdirectory(title="选择输出文件夹")
        if d:
            self.save_mode.set("custom")
            self.outdir_entry.configure(state="normal")
            self.outdir_entry.delete(0, "end")
            self.outdir_entry.insert(0, d)

    # ---------------- 转换 ----------------

    def start_convert(self) -> None:
        if self.converting:
            return
        if not self.files:
            messagebox.showinfo(APP_TITLE, "请先添加 PNG 文件。")
            return
        quality = max(10, min(100, int(self.quality.get())))

        outdir: Path | None = None
        if self.save_mode.get() == "custom":
            text = self.outdir_entry.get().strip()
            if not text:
                messagebox.showwarning(APP_TITLE, "请先选择输出文件夹，或改用「保存在原文件所在文件夹」。")
                return
            outdir = Path(text)
            if not outdir.is_dir():
                messagebox.showwarning(APP_TITLE, "输出文件夹不存在，请重新选择。")
                return

        files = list(self.files)
        open_after = self.open_after.get()
        self.converting = True
        self.convert_btn.configure(state="disabled")
        self._set_status(f"准备转换 {len(files)} 个文件…")
        Thread(target=self._worker, args=(files, quality, outdir, open_after),
               daemon=True).start()

    def _worker(self, files: list[Path], quality: int,
                outdir: Path | None, open_after: bool) -> None:
        total = len(files)
        ok = 0
        failures: list[str] = []
        used_names: set[tuple[str, str]] = set()
        first_out: Path | None = None

        for i, p in enumerate(files, 1):
            self._set_status(f"正在转换 {i}/{total}：{p.name}")
            try:
                d = outdir if outdir is not None else p.parent
                dir_key = str(d.resolve()).lower()
                name = p.stem + ".jpg"
                k = 2
                while (dir_key, name.lower()) in used_names:
                    name = f"{p.stem} ({k}).jpg"
                    k += 1
                used_names.add((dir_key, name.lower()))
                convert_one(p, d / name, quality)
                if first_out is None:
                    first_out = d
                ok += 1
            except Exception as e:
                failures.append(f"{p.name}：{e}")

        msg = f"转换完成：成功 {ok} 个"
        if failures:
            msg += f"，失败 {len(failures)} 个"
        self._set_status(msg)

        if open_after and first_out is not None:
            try:
                os.startfile(first_out)
            except Exception:
                pass

        if failures:
            text = "以下文件转换失败：\n\n" + "\n".join(failures[:10])
            if len(failures) > 10:
                text += f"\n…等共 {len(failures)} 个"
            self.root.after(0, lambda: messagebox.showwarning(APP_TITLE, text))

        self.root.after(0, self._convert_done)

    def _convert_done(self) -> None:
        self.converting = False
        self.convert_btn.configure(state="normal")

    def _set_status(self, text: str) -> None:
        self.root.after(0, lambda: self.status_label.configure(text=text))


def main() -> None:
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    if HAVE_DND:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
