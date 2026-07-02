import argparse
import math
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from box_geometry import BoxParams, build_panels, fmt, segment_bounds, validate_params, verify_assembly
from dxf_writer import save_dxf_file, write_example_files


APP_TITLE = "Генератор DXF монтажного короба"


class GeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1120x760")
        self.minsize(980, 680)

        self.values = {
            "inner_length": tk.StringVar(value="120"),
            "inner_width": tk.StringVar(value="80"),
            "inner_height": tk.StringVar(value="50"),
            "thickness": tk.StringVar(value="3"),
            "kerf": tk.StringVar(value="0.12"),
            "tab_width": tk.StringVar(value="12"),
            "hole_diameter": tk.StringVar(value="4"),
            "hole_margin": tk.StringVar(value="10"),
            "corner_radius": tk.StringVar(value="3"),
            "panel_gap": tk.StringVar(value="12"),
            "label": tk.StringVar(value="Монтажный короб"),
        }
        self.include_lid = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Готово к генерации DXF.")

        self.build_window()
        self.preview()

    def build_window(self):
        root = ttk.Frame(self, padding=14)
        root.pack(fill=tk.BOTH, expand=True)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=0, sticky="nsw", padx=(0, 14))

        preview_frame = ttk.Frame(root)
        preview_frame.grid(row=0, column=1, sticky="nsew")
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        fields = [
            ("inner_length", "Внутренняя длина, мм"),
            ("inner_width", "Внутренняя ширина, мм"),
            ("inner_height", "Высота стенок, мм"),
            ("thickness", "Толщина фанеры, мм"),
            ("kerf", "Компенсация реза, мм"),
            ("tab_width", "Ширина шипа, мм"),
            ("hole_diameter", "Диаметр отверстий, мм"),
            ("hole_margin", "Отступ отверстий, мм"),
            ("corner_radius", "Скругление углов, мм"),
            ("panel_gap", "Зазор раскладки, мм"),
            ("label", "Подпись"),
        ]

        ttk.Label(controls, text=APP_TITLE, font=("TkDefaultFont", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12)
        )

        for row, (key, label) in enumerate(fields, start=1):
            ttk.Label(controls, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(controls, textvariable=self.values[key], width=22)
            entry.grid(row=row, column=1, sticky="ew", pady=4)
            entry.bind("<KeyRelease>", lambda _event: self.preview())

        row = len(fields) + 1
        ttk.Checkbutton(controls, text="Добавить крышку", variable=self.include_lid, command=self.preview).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(8, 4)
        )

        ttk.Button(controls, text="Обновить предпросмотр", command=self.preview).grid(
            row=row + 1, column=0, columnspan=2, sticky="ew", pady=(12, 4)
        )
        ttk.Button(controls, text="Сохранить DXF", command=self.save_dxf).grid(
            row=row + 2, column=0, columnspan=2, sticky="ew", pady=4
        )
        ttk.Button(controls, text="Пример 3 мм", command=lambda: self.set_thickness("3")).grid(
            row=row + 3, column=0, sticky="ew", pady=4, padx=(0, 4)
        )
        ttk.Button(controls, text="Пример 4 мм", command=lambda: self.set_thickness("4")).grid(
            row=row + 3, column=1, sticky="ew", pady=4
        )
        ttk.Label(controls, textvariable=self.status, wraplength=290, foreground="#255a77").grid(
            row=row + 4, column=0, columnspan=2, sticky="w", pady=(14, 0)
        )

        self.canvas = tk.Canvas(preview_frame, bg="white", highlightthickness=1, highlightbackground="#b8b8b8")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda _event: self.preview())

    def current_params(self):
        numbers = {}
        for key in [
            "inner_length",
            "inner_width",
            "inner_height",
            "thickness",
            "kerf",
            "tab_width",
            "hole_diameter",
            "hole_margin",
            "corner_radius",
            "panel_gap",
        ]:
            numbers[key] = float(self.values[key].get().replace(",", "."))

        return BoxParams(
            inner_length=numbers["inner_length"],
            inner_width=numbers["inner_width"],
            inner_height=numbers["inner_height"],
            thickness=numbers["thickness"],
            kerf=numbers["kerf"],
            tab_width=numbers["tab_width"],
            hole_diameter=numbers["hole_diameter"],
            hole_margin=numbers["hole_margin"],
            corner_radius=numbers["corner_radius"],
            panel_gap=numbers["panel_gap"],
            include_lid=self.include_lid.get(),
            label=self.values["label"].get().strip() or "Монтажный короб",
        )

    def set_thickness(self, value):
        self.values["thickness"].set(value)
        self.preview()

    def save_dxf(self):
        try:
            params = self.current_params()
            validate_params(params)
            verify_assembly(params)
        except Exception as exc:
            messagebox.showerror("Ошибка параметров", str(exc))
            return

        default_name = f"montazhny_korob_{fmt(params.thickness)}mm.dxf"
        path = filedialog.asksaveasfilename(
            title="Сохранить DXF",
            defaultextension=".dxf",
            initialfile=default_name,
            filetypes=[("DXF files", "*.dxf"), ("All files", "*.*")],
        )
        if path:
            save_dxf_file(params, path)
            self.status.set(f"DXF сохранён: {path}")

    def preview(self):
        try:
            params = self.current_params()
            panels = build_panels(params)
        except Exception as exc:
            self.status.set(f"Ошибка параметров: {exc}")
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
        margin = 36
        scale = min((canvas_w - 2 * margin) / (max_x - min_x), (canvas_h - 2 * margin) / (max_y - min_y))
        if not math.isfinite(scale) or scale <= 0:
            scale = 1.0

        def map_point(px, py):
            sx = margin + (px - min_x) * scale
            sy = canvas_h - margin - (py - min_y) * scale
            return sx, sy

        for panel in panels:
            tx, ty = map_point(panel.x, panel.y - 4)
            self.canvas.create_text(tx, ty, text=panel.title, anchor="sw", fill="#505050", font=("TkDefaultFont", 9))

        for segment in segments:
            if segment.kind == "line":
                x1, y1, x2, y2 = segment.values
                self.canvas.create_line(*map_point(x1, y1), *map_point(x2, y2), fill="#b20d0d", width=1.5)
            elif segment.kind == "circle":
                x, y, r = segment.values
                x1, y1 = map_point(x - r, y - r)
                x2, y2 = map_point(x + r, y + r)
                self.canvas.create_oval(x1, y1, x2, y2, outline="#b20d0d", width=1.5)
            elif segment.kind == "arc":
                x, y, r, start, end = segment.values
                x1, y1 = map_point(x - r, y - r)
                x2, y2 = map_point(x + r, y + r)
                extent = end - start
                if extent <= 0:
                    extent += 360
                self.canvas.create_arc(x1, y1, x2, y2, start=-start, extent=-extent, style=tk.ARC, outline="#b20d0d", width=1.5)

        self.status.set("Предпросмотр обновлён. Красные линии идут в слой CUT.")


def check_examples():
    for thickness, kerf in [(3.0, 0.12), (4.0, 0.15)]:
        params = BoxParams(thickness=thickness, kerf=kerf)
        validate_params(params)
        verify_assembly(params)
        print(f"OK: {fmt(thickness)} мм, рез {fmt(kerf)} мм")


def main():
    parser = argparse.ArgumentParser(description="Генератор DXF монтажного короба для лазерной резки.")
    parser.add_argument("--examples", action="store_true", help="создать DXF-примеры в output/dxf")
    parser.add_argument("--check", action="store_true", help="проверить шипы и пазы для 3 и 4 мм")
    args = parser.parse_args()

    if args.check:
        check_examples()
        return

    if args.examples:
        for path in write_example_files(Path("output/dxf")):
            print(path)
        return

    app = GeneratorApp()
    app.mainloop()


if __name__ == "__main__":
    main()
