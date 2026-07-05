import math
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from box_geometry import BoxParams, build_panels, fmt, segment_bounds, validate_params, verify_assembly
from dxf_writer import save_dxf_file, write_example_files


APP_TITLE = "ElectronicsBox DXF"


class GeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("900x720")
        self.minsize(780, 620)
        self.status = tk.StringVar(value="Готово")
        self.make_window()
        self.preview()

    def make_window(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = ttk.Frame(main)
        left.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        right = ttk.Frame(main)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        ttk.Label(left, text=APP_TITLE, font=("TkDefaultFont", 14, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 12))
        ttk.Label(left, text="Размер коробки: 100 x 100 x 100 мм").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Label(left, text="Материал: фанера 3 мм").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Label(left, text="Габарит раскладки: 221.9 x 452.2 мм").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Button(left, text="Обновить", command=self.preview).grid(row=4, column=0, sticky="ew", pady=(14, 3))
        ttk.Button(left, text="Сохранить DXF", command=self.save_file).grid(row=5, column=0, sticky="ew", pady=3)
        ttk.Label(left, textvariable=self.status, wraplength=230, foreground="#245070").grid(row=6, column=0, sticky="w", pady=(12, 0))

        self.canvas = tk.Canvas(right, bg="white", highlightthickness=1, highlightbackground="#aaaaaa")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda event: self.preview())

    def get_params(self):
        return BoxParams()

    def save_file(self):
        try:
            params = self.get_params()
            validate_params(params)
            verify_assembly(params)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))
            return

        path = filedialog.asksaveasfilename(
            title="Сохранить DXF",
            defaultextension=".dxf",
            initialfile="electronics_box.dxf",
            filetypes=[("DXF", "*.dxf"), ("Все файлы", "*.*")],
        )

        if path:
            save_dxf_file(params, path)
            self.status.set(f"Файл сохранён: {path}")

    def preview(self):
        try:
            params = self.get_params()
            panels = build_panels(params)
        except Exception as error:
            self.status.set(f"Ошибка: {error}")
            return

        self.canvas.delete("all")

        segments = []
        for panel in panels:
            segments.extend(panel.segments)

        bounds = segment_bounds(segments)
        if bounds is None:
            return

        min_x, min_y, max_x, max_y = bounds
        canvas_w = max(1, self.canvas.winfo_width())
        canvas_h = max(1, self.canvas.winfo_height())
        margin = 30
        scale_x = (canvas_w - margin * 2) / (max_x - min_x)
        scale_y = (canvas_h - margin * 2) / (max_y - min_y)
        scale = min(scale_x, scale_y)

        if not math.isfinite(scale) or scale <= 0:
            scale = 1

        def point(x, y):
            px = margin + (x - min_x) * scale
            py = canvas_h - margin - (y - min_y) * scale
            return px, py

        for segment in segments:
            color = "#111111"
            if segment.layer == "HOLES":
                color = "#0046ff"
            elif segment.layer == "TEXT":
                color = "#d00000"

            if segment.kind == "line":
                x1, y1, x2, y2 = segment.values
                self.canvas.create_line(*point(x1, y1), *point(x2, y2), fill=color, width=1.2)
            elif segment.kind == "circle":
                x, y, r = segment.values
                x1, y1 = point(x - r, y - r)
                x2, y2 = point(x + r, y + r)
                self.canvas.create_oval(x1, y1, x2, y2, outline=color, width=1.2)
            elif segment.kind == "arc":
                x, y, r, a1, a2 = segment.values
                x1, y1 = point(x - r, y - r)
                x2, y2 = point(x + r, y + r)
                angle = a2 - a1
                if angle <= 0:
                    angle = angle + 360
                self.canvas.create_arc(x1, y1, x2, y2, start=-a1, extent=-angle, style=tk.ARC, outline=color, width=1.2)
            elif segment.kind == "text":
                x, y, text, size = segment.values
                self.canvas.create_text(*point(x, y), text=text, anchor="sw", fill=color, font=("TkDefaultFont", max(6, int(size * scale))))

        self.status.set("Предпросмотр готов")


def check_examples():
    params = BoxParams()
    validate_params(params)
    verify_assembly(params)
    segments = []
    for panel in build_panels(params):
        segments.extend(panel.segments)
    min_x, min_y, max_x, max_y = segment_bounds(segments)
    print(f"OK: раскладка {fmt(max_x - min_x)} x {fmt(max_y - min_y)} мм")


def main():
    if "--examples" in sys.argv:
        files = write_example_files(Path("output/dxf"))
        for path in files:
            print(path)
        return

    if "--check" in sys.argv:
        check_examples()
        return

    app = GeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
