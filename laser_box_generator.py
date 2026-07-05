import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from box_geometry import BoxParams, build_panels, fmt, segment_bounds, validate_params, verify_assembly
from dxf_writer import save_dxf_file, write_example_files
from svg_writer import save_svg_file


APP_TITLE = "ElectronicsBox — генератор DXF и SVG"


class GeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("560x420")
        self.resizable(False, False)
        self.length_var = tk.StringVar(value="100.0")
        self.depth_var = tk.StringVar(value="100.0")
        self.height_var = tk.StringVar(value="100.0")
        self.thickness_var = tk.StringVar(value="3.0")
        self.finger_var = tk.StringVar(value="6.0")
        self.file_var = tk.StringVar(value="electronics_box.dxf")
        self.status = tk.StringVar(value="")
        self.make_window()

    def make_window(self):
        main = ttk.Frame(self, padding=24)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(1, weight=1)

        ttk.Label(main, text="Коробка ElectronicsBox", font=("TkDefaultFont", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 18))

        rows = [
            ("Длина (внутренняя ширина), мм", self.length_var),
            ("Глубина (внутренняя глубина), мм", self.depth_var),
            ("Высота (внутренняя высота), мм", self.height_var),
            ("Толщина материала, мм", self.thickness_var),
            ("Ширина шипа, мм", self.finger_var),
            ("Имя выходного файла", self.file_var),
        ]

        for row, data in enumerate(rows, start=1):
            title, variable = data
            ttk.Label(main, text=title).grid(row=row, column=0, sticky="w", pady=5, padx=(0, 18))
            ttk.Entry(main, textvariable=variable).grid(row=row, column=1, sticky="ew", pady=5)

        buttons = ttk.Frame(main)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(18, 8))
        buttons.columnconfigure(0, weight=1)
        buttons.columnconfigure(1, weight=1)

        ttk.Button(buttons, text="Сгенерировать DXF", command=self.generate_dxf).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(buttons, text="Сгенерировать SVG", command=self.generate_svg).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(main, textvariable=self.status, foreground="#245070").grid(row=8, column=0, columnspan=2, sticky="w")

    def get_params(self):
        return BoxParams(
            self.read_number(self.length_var.get(), "Длина"),
            self.read_number(self.depth_var.get(), "Глубина"),
            self.read_number(self.height_var.get(), "Высота"),
            self.read_number(self.thickness_var.get(), "Толщина материала"),
            self.read_number(self.finger_var.get(), "Ширина шипа"),
        )

    def read_number(self, text, name):
        try:
            return float(text.replace(",", "."))
        except ValueError:
            raise ValueError(f"{name} указана неправильно")

    def output_path(self, extension):
        name = self.file_var.get().strip()
        if not name:
            name = "electronics_box.dxf"

        path = Path(name)
        if path.suffix.lower() != extension:
            path = path.with_suffix(extension)
        if not path.is_absolute():
            path = Path("output") / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def generate_dxf(self):
        try:
            params = self.get_params()
            verify_assembly(params)
            path = self.output_path(".dxf")
            save_dxf_file(params, path)
            self.show_result(params, path)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def generate_svg(self):
        try:
            params = self.get_params()
            verify_assembly(params)
            path = self.output_path(".svg")
            save_svg_file(params, path)
            self.show_result(params, path)
        except Exception as error:
            messagebox.showerror("Ошибка", str(error))

    def show_result(self, params, path):
        segments = []
        for panel in build_panels(params):
            segments.extend(panel.segments)
        min_x, min_y, max_x, max_y = segment_bounds(segments)
        text = f"Готово: {path} ({fmt(max_x - min_x)} x {fmt(max_y - min_y)} мм)"
        self.status.set(text)
        messagebox.showinfo("Готово", text)


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
        files = write_example_files(Path("output"))
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
