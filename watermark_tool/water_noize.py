import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import tkinter.colorchooser as colorchooser
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageFilter, ImageChops, ImageEnhance, ImageOps
from PIL.PngImagePlugin import PngInfo
import os
import json
import sys
import random

# PRESET_FILE = "watermark_settings.json"
# Use absolute path to ensure the JSON is saved in the script's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRESET_FILE = os.path.join(BASE_DIR, "watermark_settings.json")

class AegisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Aegis Defense Tool")
        self.root.geometry("1100x900")
        
        self.setup_ui_font()

        # load the data
        self.presets = self.load_presets()
        self.check_vars = {}
        self.current_editing_name = None
        
        # UI_settings
        self.mode_var = tk.StringVar(value="free")
        self.text_var = tk.StringVar()
        self.scale_var = tk.DoubleVar(value=5.0)
        self.opacity_var = tk.IntVar(value=200)
        self.bold_var = tk.IntVar(value=0)
        self.color_rgb = (255, 255, 255)
        self.color_hex = "#ffffff"
        self.font_path = ""
        self.pos_x = 0.95
        self.pos_y = 0.95
        
        self.mist_power = tk.IntVar(value=0)
        self.poison_var = tk.BooleanVar(value=True) 

        self.original_image = None
        self.loaded_path = ""
        self.show_noise_check = tk.BooleanVar(value=False)

        # build tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.tab_create = tk.Frame(self.notebook)
        self.notebook.add(self.tab_create, text="画像作成")
        self.build_create_ui()

        self.tab_inspect = tk.Frame(self.notebook)
        self.notebook.add(self.tab_inspect, text="メタデータ検査")
        self.build_inspect_ui()

        self.refresh_preset_list()
        
        # load the default settings
        if "Default" in self.presets:
            self.load_edit("Default")
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui_font(self):
        font_conf = ("Meiryo UI", 10) if sys.platform == "win32" else ("Hiragino Sans", 11)
        self.root.option_add("*Font", font_conf)

    def load_presets(self):
        # default setting
        default_data = {"Default": {"mode":"free", "text":"@My_ID", "scale":5.0, "opacity":200, "bold":0, "color_hex":"#fff", "color_rgb":[255,255,255], "font_path":"", "pos_x":0.95, "pos_y":0.95}}
        
        if os.path.exists(PRESET_FILE):
            try:
                # Open with encoding to prevent issues
                with open(PRESET_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # check the data
                if "Default" not in data or not isinstance(data["Default"], dict):
                    print("設定ファイルが古いか壊れているため、初期化します。")
                    return default_data
                
                return data
            except:
                return default_data
        return default_data

    #UI
    def build_create_ui(self):
        paned = tk.PanedWindow(self.tab_create, orient="horizontal", sashwidth=5, bg="#ddd")
        paned.pack(fill="both", expand=True)

        left = tk.Frame(paned, width=400, padx=15, pady=15)
        paned.add(left)

        f1 = tk.LabelFrame(left, text="1. 画像選択", padx=10, pady=10)
        f1.pack(fill="x", pady=(0, 10))
        tk.Button(f1, text="ファイルを開く", command=self.browse_image, bg="#e1e1e1").pack(fill="x")
        self.file_label = tk.Label(f1, text="（未選択）", fg="#666")
        self.file_label.pack(pady=5)

        f_def = tk.LabelFrame(left, text="2. AI阻害設定", padx=10, pady=10, fg="red")
        f_def.pack(fill="x", pady=(0, 10))
        tk.Label(f_def, text="ミスト強度 (ノイズ):").pack(anchor="w")
        tk.Scale(f_def, from_=0, to=50, orient="horizontal", variable=self.mist_power, command=lambda e: self.update_preview()).pack(fill="x")
        f_poi = tk.Frame(f_def, pady=5)
        f_poi.pack(fill="x")
        tk.Checkbutton(f_poi, text="メタデータ汚染 (Poisoning)", variable=self.poison_var, fg="red").pack(side="left")

        f2 = tk.LabelFrame(left, text="3. ウォーターマーク設定", padx=10, pady=10)
        f2.pack(fill="both", expand=True, pady=(0, 10))
        
        cv = tk.Canvas(f2, height=100)
        sc = ttk.Scrollbar(f2, command=cv.yview)
        self.scroll_frame = tk.Frame(cv)
        cv.create_window((0,0), window=self.scroll_frame, anchor="nw")
        cv.configure(yscrollcommand=sc.set)
        cv.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y")
        self.scroll_frame.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))

        b_area = tk.Frame(f2)
        b_area.pack(fill="x", pady=5)
        tk.Button(b_area, text="新規", command=self.create_new_preset, bg="#b3e5fc").pack(side="left", fill="x", expand=True)
        tk.Button(b_area, text="削除", command=self.delete_preset, fg="red").pack(side="right")

        self.f_edit = tk.LabelFrame(left, text="4. 詳細編集", padx=10, pady=10)
        self.f_edit.pack(fill="x", pady=(0, 10))
        self.lbl_editing = tk.Label(self.f_edit, text="[未選択]", fg="blue", font=("bold", 10))
        self.lbl_editing.pack()
        
        tk.Entry(self.f_edit, textvariable=self.text_var).pack(fill="x")
        
        f_mode = tk.Frame(self.f_edit)
        f_mode.pack(fill="x")
        tk.Radiobutton(f_mode, text="自由配置", variable=self.mode_var, value="free", command=self.save_edit).pack(side="left")
        tk.Radiobutton(f_mode, text="タイル", variable=self.mode_var, value="protect", command=self.save_edit).pack(side="left")
        
        tk.Scale(self.f_edit, from_=1, to=50, orient="horizontal", variable=self.scale_var, label="サイズ", command=lambda e: self.save_edit()).pack(fill="x")
        tk.Scale(self.f_edit, from_=0, to=255, orient="horizontal", variable=self.opacity_var, label="濃さ", command=lambda e: self.save_edit()).pack(fill="x")
        tk.Scale(self.f_edit, from_=0, to=10, orient="horizontal", variable=self.bold_var, label="太さ", command=lambda e: self.save_edit()).pack(fill="x")
        
        f_col = tk.Frame(self.f_edit)
        f_col.pack(fill="x")
        self.col_btn = tk.Button(f_col, text="色", width=5, command=self.pick_color)
        self.col_btn.pack(side="left")
        tk.Button(f_col, text="Font...", command=self.pick_font).pack(side="right")

        tk.Button(left, text="PNGで保存", command=self.save_image, bg="#4CAF50", fg="white", font=("bold", 12), height=2).pack(fill="x")

        right = tk.Frame(paned, bg="#333", padx=10, pady=10)
        paned.add(right)
        self.canvas = tk.Canvas(right, bg="#222", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_click)
        
        f_chk = tk.Frame(right, bg="#333")
        f_chk.pack(fill="x")
        tk.Checkbutton(f_chk, text="ノイズ確認モード", variable=self.show_noise_check, command=self.update_preview, bg="#333", fg="white", selectcolor="#555").pack(anchor="w")

    def build_inspect_ui(self):
        f = tk.Frame(self.tab_inspect, padx=20, pady=20)
        f.pack(fill="both", expand=True)
        
        tk.Label(f, text="【解析ツール】", font=("bold", 14)).pack(pady=(0,10))
        tk.Label(f, text="画像に含まれるメタデータ(タグ)を確認します。", fg="#555").pack(pady=(0,20))
        tk.Button(f, text="画像を解析...", command=self.inspect_image, height=2, bg="#FF9800", fg="white").pack(fill="x")
        self.txt_inspect = tk.Text(f, height=20, width=80, bg="#f0f0f0", font=("Consolas", 10))
        self.txt_inspect.pack(pady=20, fill="both", expand=True)
        ys = ttk.Scrollbar(self.txt_inspect, command=self.txt_inspect.yview)
        self.txt_inspect.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")

    #logic
    def inspect_image(self):
        path = filedialog.askopenfilename()
        if not path: return
        try:
            img = Image.open(path)
            self.txt_inspect.delete(1.0, tk.END)
            res =  f"--- File Info ---\nName: {os.path.basename(path)}\nSize: {img.size[0]} x {img.size[1]} px\nFormat: {img.format}\n\n--- Metadata ---\n"
            if not img.info: res += "None\n"
            else:
                for k, v in img.info.items():
                    if "bad anatomy" in str(v): res += f"[!! POISON !!] {k}:\n  -> {v}\n\n"
                    else: res += f"[{k}]: {v}\n\n"
            self.txt_inspect.insert(tk.END, res)
            messagebox.showinfo("完了", "解析しました。")
        except Exception as e: messagebox.showerror("Error", f"解析失敗: {e}")

    def save_presets_file(self):
        # try: json.dump(self.presets, open(PRESET_FILE, "w"), indent=4)
        # except: pass
        # Use proper encoding and error output
        try:
            with open(PRESET_FILE, "w", encoding="utf-8") as f:
                json.dump(self.presets, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Write error: {e}")

    def on_close(self):
        self.save_presets_file()
        self.root.destroy()

    def refresh_preset_list(self):
        for w in self.scroll_frame.winfo_children(): w.destroy()
        for name in self.presets:
            r = tk.Frame(self.scroll_frame)
            r.pack(fill="x", pady=2)
            if name not in self.check_vars: self.check_vars[name] = tk.BooleanVar(value=(name=="Default"))
            tk.Checkbutton(r, variable=self.check_vars[name], command=self.update_preview).pack(side="left")
            tk.Button(r, text=name, anchor="w", command=lambda n=name: self.load_edit(n)).pack(side="left", fill="x", expand=True)

    def create_new_preset(self):
        n = simpledialog.askstring("新規", "プリセット名:")
        if n and n not in self.presets:
            self.presets[n] = self.presets["Default"].copy()
            self.refresh_preset_list()
            self.load_edit(n)

    def delete_preset(self):
        n = self.current_editing_name
        if n and n!="Default":
            del self.presets[n]
            self.current_editing_name = None
            self.refresh_preset_list()
            self.update_preview()

    def load_edit(self, name):
        self.current_editing_name = name
        p = self.presets[name]
        self.lbl_editing.config(text=f"編集中: {name}")
        self.mode_var.set(p["mode"])
        self.text_var.set(p["text"])
        self.scale_var.set(p["scale"])
        self.opacity_var.set(p["opacity"])
        self.bold_var.set(p.get("bold", 0))
        self.color_hex = p["color_hex"]
        self.color_rgb = tuple(p["color_rgb"])
        self.font_path = p["font_path"]
        self.pos_x = p["pos_x"]
        self.pos_y = p["pos_y"]
        self.col_btn.config(bg=self.color_hex)
        if name in self.check_vars and not self.check_vars[name].get():
            self.check_vars[name].set(True)
            self.update_preview()

    def save_edit(self):
        if not self.current_editing_name: return
        n = self.current_editing_name
        self.presets[n].update({
            "mode": self.mode_var.get(), "text": self.text_var.get(), "scale": self.scale_var.get(),
            "opacity": self.opacity_var.get(), "bold": self.bold_var.get(),
            "color_hex": self.color_hex, "color_rgb": list(self.color_rgb), "font_path": self.font_path,
            "pos_x": self.pos_x, "pos_y": self.pos_y
        }); self.update_preview()
        # Save to disk on every change to prevent data loss
        self.save_presets_file()

    def pick_color(self):
        c = colorchooser.askcolor(self.color_hex)
        if c[1]: self.color_hex = c[1]; self.color_rgb = tuple(map(int, c[0])); self.col_btn.config(bg=c[1]); self.save_edit()

    def pick_font(self):
        f = filedialog.askopenfilename(filetypes=[("Font", "*.ttf *.otf")])
        if f: self.font_path = f; self.save_edit()

    def browse_image(self):
        f = filedialog.askopenfilename()
        if f:
            self.loaded_path = f; self.file_label.config(text=os.path.basename(f))
            self.original_image = Image.open(f).convert("RGBA"); self.update_preview()

    def on_click(self, e):
        if self.mode_var.get() == "free" and self.original_image and not self.show_noise_check.get():
            cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
            iw, ih = self.original_image.size
            s = min(cw/iw, ch/ih) * 0.9; dw, dh = int(iw*s), int(ih*s); ox, oy = (cw-dw)//2, (ch-dh)//2
            rx, ry = (e.x-ox)/dw, (e.y-oy)/dh
            if 0 <= rx <= 1 and 0 <= ry <= 1: self.pos_x, self.pos_y = rx, ry; self.save_edit()

    def get_font(self, p, s):
        try: return ImageFont.truetype(p if p else "arial.ttf", s)
        except: return ImageFont.load_default()

    def process_image(self, base):
        p = self.mist_power.get()
        if p > 0:
            noise = Image.frombytes("RGB", base.size, os.urandom(base.size[0]*base.size[1]*3)).convert("RGBA")
            noise.putalpha(p)
            base = Image.alpha_composite(base.convert("RGBA"), noise)
        
        w, h = base.size
        for n, v in self.check_vars.items():
            if not v.get(): continue
            pre = self.presets[n]; txt = pre["text"]
            if not txt: continue
            layer = Image.new("RGBA", base.size, (255,255,255,0)); d = ImageDraw.Draw(layer)
            fs = max(1, int(w * (pre["scale"]/100))); font = self.get_font(pre["font_path"], fs)
            col = tuple(pre["color_rgb"] + [pre["opacity"]]); bld = pre.get("bold", 0)
            if pre["mode"] == "free":
                bbox = d.textbbox((0,0), txt, font=font, stroke_width=bld); tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                d.text((w*pre["pos_x"]-tw/2, h*pre["pos_y"]-th/2), txt, font=font, fill=col, stroke_width=bld, stroke_fill=col)
            else:
                d_tmp = ImageDraw.Draw(Image.new("RGBA",(1,1)))
                bbox = d_tmp.textbbox((0,0), txt, font=font, stroke_width=bld); tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
                ti = Image.new("RGBA", (tw+20, th+20), (255,255,255,0)); d2 = ImageDraw.Draw(ti)
                d2.text((10,10), txt, font=font, fill=col, stroke_width=bld, stroke_fill=col)
                rot = ti.rotate(45, expand=True, resample=Image.BICUBIC); rw, rh = rot.size
                sx, sy = int(rw*1.5), int(rh*1.5)
                for y in range(-rh, h, sy):
                    for x in range(-rw, w, sx):
                        o = (sx//2) if (y//sy)%2==0 else 0
                        layer.paste(rot, (x+o, y), rot)
            base = Image.alpha_composite(base, layer)
        return base

    def update_preview(self):
        if not self.original_image: return
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw < 10: return
        iw, ih = self.original_image.size
        s = min(cw/iw, ch/ih) * 0.9; dw, dh = int(iw*s), int(ih*s)
        prev = self.original_image.resize((dw, dh), Image.Resampling.LANCZOS)
        final = self.process_image(prev)
        if self.show_noise_check.get():
            no_mist = self.original_image.resize((dw, dh), Image.Resampling.LANCZOS)
            diff = ImageChops.difference(no_mist.convert("RGBA"), final).convert("RGB")
            final = ImageOps.autocontrast(diff, cutoff=0)
        self.tk = ImageTk.PhotoImage(final)
        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=self.tk, anchor="center")
        if not self.show_noise_check.get() and self.current_editing_name and self.mode_var.get()=="free":
            cx, cy = (cw-dw)//2 + dw*self.pos_x, (ch-dh)//2 + dh*self.pos_y
            self.canvas.create_oval(cx-5, cy-5, cx+5, cy+5, outline="red", width=2)

    def save_image(self):
        if not self.original_image: return
        try:
            final = self.process_image(self.original_image)
            d, f = os.path.split(self.loaded_path)
            n, e = os.path.splitext(f)
            png_info = PngInfo()
            if self.poison_var.get():
                tags = "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry"
                png_info.add_text("parameters", tags); png_info.add_text("Description", tags); png_info.add_text("Software", "Aegis Tool")
            save_path = os.path.join(d, f"{n}_protected.png")
            final.save(save_path, pnginfo=png_info)
            w, h = final.size
            messagebox.showinfo("完了", f"保存しました。\n{save_path}\n\nSize: {w}x{h}")
        except Exception as e: messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = AegisTool(root)
    root.mainloop()