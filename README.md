# Генератор DXF ElectronicsBox

Проект для практики 1 курса по теме "Генерация DXF чертежей для лазерной резки".

Приложение открывает образец `assets/ElectronicsBox.svg`, показывает его в GUI и сохраняет такой же чертеж в формате DXF.

## Состав проекта

- `laser_box_generator.py` - окно приложения, предпросмотр и кнопка сохранения.
- `box_geometry.py` - чтение SVG и перевод контуров в простые отрезки.
- `dxf_writer.py` - запись DXF через `ezdxf`.
- `assets/ElectronicsBox.svg` - исходный образец раскладки.
- `output/dxf/electronics_box.dxf` - готовый пример DXF.
- `tests/` - автоматические проверки.
- `docs/report.md` - текст отчета.

## Запуск

```bash
python3 -m pip install -r requirements.txt
python3 laser_box_generator.py
```

## Генерация DXF без GUI

```bash
python3 laser_box_generator.py --examples
```

Команда создаст файл `output/dxf/electronics_box.dxf`.

## Проверка

```bash
python3 laser_box_generator.py --check
python3 -m unittest discover -s tests
```

Проверки контролируют чтение SVG, наличие всех деталей, слои DXF, размеры раскладки и возможность создать DXF.

## Что получается

Чертеж повторяет образец `ElectronicsBox.svg`:

- верхняя крышка;
- дно;
- четыре стенки;
- четыре треугольные монтажные детали;
- отверстия и пазы;
- подписи деталей.

В DXF используются миллиметры. Основной контур находится в слое `CUT`, отверстия и пазы из синего слоя SVG - в слое `HOLES`, подписи - в слое `TEXT`.
