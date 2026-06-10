"""
================================================================================
Модуль main.py — Графический интерфейс пользователя (GUI)
================================================================================

Описание:
    Программное обеспечение с графическим интерфейсом для визуализации
    процесса преследования цели с использованием метода виртуальных
    потенциальных полей (Artificial Potential Fields).

    Области интерфейса:
        1. Область настроек — выбор параметров преследования.
        2. Область отображения — визуализация процесса на холсте.
        3. Область отладочной информации — вывод текущих данных.

    Запуск:
        python main.py

    Зависимости:
        — Python 3.8+
        — tkinter (входит в стандартную библиотеку Python)
        — модули target.py и pursuer.py в той же директории

Автор: Курсовая работа по дисциплине «Методы ИИ для беспилотных систем»
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math
import random
import os
from datetime import datetime

# Импортируем модули цели и преследователя
from target import Target
from pursuer import Pursuer


# ====================================================================== #
#  Константы приложения
# ====================================================================== #

CANVAS_WIDTH = 800           # ширина холста (пиксели)
CANVAS_HEIGHT = 600          # высота холста (пиксели)
CATCH_DISTANCE = 15.0        # пороговое расстояние «поимки» (пиксели)
MAX_SIMULATION_TIME = 300.0  # максимальное время моделирования (сек)
FRAME_INTERVAL_MS = 33       # интервал обновления кадра ≈ 30 FPS
MARGIN = 20                  # отступ от краёв холста (пиксели)

# Цветовая схема
COLOR_BG_CANVAS = "#1a1a2e"       # тёмно-синий фон холста
COLOR_TARGET = "#ff6b6b"          # красный — маркер цели
COLOR_TARGET_TRAIL = "#ff6b6b"    # красный — траектория цели
COLOR_PURSUER = "#4ecdc4"         # бирюзовый — маркер преследователя
COLOR_PURSUER_TRAIL = "#4ecdc4"   # бирюзовый — траектория преследователя
COLOR_OBSTACLE = "#6c757d"        # серый — препятствия
COLOR_OBSTACLE_RING = "#495057"   # тёмно-серый — зона влияния препятствия
COLOR_GRID = "#2a2a4a"            # цвет сетки на холсте

# Размеры маркеров
TARGET_RADIUS = 8                 # радиус маркера цели
PURSUER_RADIUS = 8                # радиус маркера преследователя

# Предустановленные препятствия (x, y, radius)
DEFAULT_OBSTACLES = [
    (300, 180, 35),
    (550, 400, 40),
    (450, 280, 30),
    (200, 430, 38),
]


# ====================================================================== #
#  Вспомогательная функция — создание пары «ползунок + поле ввода»
# ====================================================================== #

def create_slider_entry(parent, label_text, from_, to, default, resolution=1.0,
                        row=0, col=0):
    """
    Создаёт в виджете parent строку с:
        — меткой (Label),
        — ползунком (Scale),
        — полем ввода (Entry),
    связанными общей переменной DoubleVar.

    Параметры:
        parent     : родительский контейнер (Frame)
        label_text : текст метки
        from_      : минимальное значение ползунка
        to         : максимальное значение ползунка
        default    : значение по умолчанию
        resolution : шаг ползунка
        row, col   : позиция в сетке (grid)

    Возвращает:
        tk.DoubleVar — переменную, связанную с ползунком и полем ввода.
    """
    var = tk.DoubleVar(value=default)

    # Метка
    lbl = tk.Label(parent, text=label_text, anchor="w", font=("Arial", 9))
    lbl.grid(row=row, column=col, sticky="w", padx=(5, 2), pady=2)

    # Фрейм для ползунка и поля ввода
    frame = tk.Frame(parent)
    frame.grid(row=row, column=col + 1, sticky="ew", padx=2, pady=2)

    # Ползунок (Scale)
    slider = tk.Scale(
        frame,
        variable=var,
        from_=from_,
        to=to,
        resolution=resolution,
        orient=tk.HORIZONTAL,
        length=140,
        showvalue=False,       # не показывать значение над ползунком
        font=("Arial", 8),
    )
    slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

    # Поле ввода (Entry), привязанное к той же переменной
    entry = tk.Entry(
        frame,
        textvariable=var,
        width=7,
        font=("Arial", 9),
        justify=tk.CENTER,
    )
    entry.pack(side=tk.LEFT, padx=(4, 0))

    return var


# ====================================================================== #
#  Основной класс приложения
# ====================================================================== #

class PursuitApp:
    """
    Главный класс приложения — создаёт графический интерфейс и управляет
    процессом моделирования преследования.

    Макет окна:
        ┌────────────────┬──────────────────────────────────────┐
        │  НАСТРОЙКИ     │                                      │
        │                │          ОБЛАСТЬ                     │
        │  (ползунки,    │          ОТОБРАЖЕНИЯ                 │
        │   списки,      │          (Canvas)                    │
        │   кнопки)      │                                      │
        │                │                                      │
        ├────────────────┤                                      │
        │  ОТЛАДКА       │                                      │
        │  (информация)  │                                      │
        └────────────────┴──────────────────────────────────────┘
    """

    def __init__(self, root: tk.Tk):
        """
        Конструктор — создаёт и настраивает все элементы интерфейса.

        Параметры:
            root: главное окно tkinter (Tk)
        """
        self.root = root
        self.root.title(
            "Преследование цели — Метод потенциальных полей (APF)"
        )
        self.root.resizable(False, False)  # фиксированный размер окна

        # ---- Состояние моделирования ----
        self.is_running = False       # флаг: идёт ли моделирование
        self.animation_id = None      # ID таймера анимации (для отмены)
        self.simulation_time = 0.0    # текущее время моделирования (сек)
        self.caught = False           # флаг: цель поймана

        # ---- Объекты модели ----
        self.target = None            # экземпляр Target
        self.pursuer = None           # экземпляр Pursuer
        self.obstacles = []           # список препятствий [(x, y, r), ...]

        # ---- Данные траекторий для отрисовки ----
        self.target_trail = []        # список (x, y) точек траектории цели
        self.pursuer_trail = []       # список (x, y) точек траектории преследователя

        # ---- Данные для сохранения в файл ----
        self.history = []             # список словарей с данными каждого шага
        self.initial_distance = 0.0   # начальная дистанция

        # Строим интерфейс
        self._build_gui()

    # ================================================================== #
    #  Построение графического интерфейса
    # ================================================================== #

    def _build_gui(self):
        """Создаёт все виджеты главного окна."""

        # Главный контейнер (горизонтальное разделение)
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Левая панель (настройки + отладка) ----
        left_panel = tk.Frame(main_frame, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        left_panel.pack_propagate(False)

        # ---- Правая панель (холст визуализации) ----
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)

        # Строим подобласти
        self._build_settings(left_panel)
        self._build_canvas(right_panel)
        self._build_debug(left_panel)

    # ------------------------------------------------------------------ #
    #  Область настроек
    # ------------------------------------------------------------------ #
    def _build_settings(self, parent):
        """
        Создаёт область настроек:
            — выбор типа траектории цели,
            — скорости цели и преследователя,
            — метод преследования,
            — начальная дистанция,
            — параметры APF (k_att, k_rep, d0),
            — галочки (препятствия, сохранение в файл),
            — кнопки управления.
        """
        settings_frame = tk.LabelFrame(
            parent, text=" ⚙ Настройки ", font=("Arial", 10, "bold"),
            padx=5, pady=5,
        )
        settings_frame.pack(fill=tk.X, pady=(0, 5))

        # Фрейм для сетки настроек
        grid_frame = tk.Frame(settings_frame)
        grid_frame.pack(fill=tk.X)

        # Настраиваем веса столбцов для растяжения
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=2)

        row = 0  # счётчик строк

        # ---- Тип траектории цели (выпадающий список) ----
        lbl_traj = tk.Label(grid_frame, text="Траектория цели:", anchor="w",
                            font=("Arial", 9))
        lbl_traj.grid(row=row, column=0, sticky="w", padx=5, pady=2)

        self.var_trajectory = tk.StringVar(value=Target.TYPES[0])
        combo_traj = ttk.Combobox(
            grid_frame, textvariable=self.var_trajectory,
            values=Target.TYPES, state="readonly", width=22,
        )
        combo_traj.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        row += 1

        # ---- Метод преследования (выпадающий список) ----
        lbl_method = tk.Label(grid_frame, text="Метод преследования:", anchor="w",
                              font=("Arial", 9))
        lbl_method.grid(row=row, column=0, sticky="w", padx=5, pady=2)

        self.var_method = tk.StringVar(value=Pursuer.METHODS[0])
        combo_method = ttk.Combobox(
            grid_frame, textvariable=self.var_method,
            values=Pursuer.METHODS, state="readonly", width=22,
        )
        combo_method.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        row += 1

        # ---- Скорость цели (ползунок + ввод) ----
        self.var_target_speed = create_slider_entry(
            grid_frame, "Скорость цели:",
            from_=10, to=200, default=60, resolution=1,
            row=row, col=0,
        )
        row += 1

        # ---- Скорость преследователя (ползунок + ввод) ----
        self.var_pursuer_speed = create_slider_entry(
            grid_frame, "Скорость пресл-ля:",
            from_=10, to=250, default=80, resolution=1,
            row=row, col=0,
        )
        row += 1

        # ---- Начальная дистанция (ползунок + ввод) ----
        self.var_distance = create_slider_entry(
            grid_frame, "Нач. дистанция:",
            from_=50, to=500, default=300, resolution=5,
            row=row, col=0,
        )
        row += 1

        # ---- Разделитель ----
        sep1 = ttk.Separator(grid_frame, orient=tk.HORIZONTAL)
        sep1.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
        row += 1

        # ---- Заголовок параметров APF ----
        lbl_apf = tk.Label(grid_frame, text="Параметры APF:", anchor="w",
                           font=("Arial", 9, "bold"))
        lbl_apf.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=(2, 0))
        row += 1

        # ---- k_att — коэффициент притяжения ----
        self.var_k_att = create_slider_entry(
            grid_frame, "k_att (притяж.):",
            from_=0.1, to=10.0, default=2.0, resolution=0.1,
            row=row, col=0,
        )
        row += 1

        # ---- k_rep — коэффициент отталкивания ----
        self.var_k_rep = create_slider_entry(
            grid_frame, "k_rep (отталк.):",
            from_=10, to=2000, default=300, resolution=10,
            row=row, col=0,
        )
        row += 1

        # ---- d0 — радиус влияния препятствий ----
        self.var_d0 = create_slider_entry(
            grid_frame, "d₀ (рад. влияния):",
            from_=30, to=300, default=120, resolution=5,
            row=row, col=0,
        )
        row += 1

        # ---- Скорость моделирования ----
        self.var_sim_speed = create_slider_entry(
            grid_frame, "Скорость симуляции:",
            from_=0.1, to=5.0, default=1.0, resolution=0.1,
            row=row, col=0,
        )
        row += 1

        # ---- Разделитель ----
        sep2 = ttk.Separator(grid_frame, orient=tk.HORIZONTAL)
        sep2.grid(row=row, column=0, columnspan=2, sticky="ew", pady=5, padx=5)
        row += 1

        # ---- Галочка: препятствия ----
        self.var_obstacles = tk.BooleanVar(value=True)
        chk_obs = tk.Checkbutton(
            grid_frame, text="Показать препятствия",
            variable=self.var_obstacles, font=("Arial", 9),
        )
        chk_obs.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        row += 1

        # ---- Галочка: сохранение в файл ----
        self.var_save = tk.BooleanVar(value=False)
        chk_save = tk.Checkbutton(
            grid_frame, text="Сохранить результаты в файл",
            variable=self.var_save, font=("Arial", 9),
        )
        chk_save.grid(row=row, column=0, columnspan=2, sticky="w", padx=5, pady=2)
        row += 1

        # ---- Кнопки управления ----
        btn_frame = tk.Frame(grid_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=8, padx=5)

        self.btn_start = tk.Button(
            btn_frame, text="▶ Запуск", width=10,
            font=("Arial", 9, "bold"), bg="#28a745", fg="white",
            command=self._start_pursuit,
        )
        self.btn_start.pack(side=tk.LEFT, padx=3)

        self.btn_stop = tk.Button(
            btn_frame, text="■ Прервать", width=10,
            font=("Arial", 9, "bold"), bg="#dc3545", fg="white",
            command=self._stop_pursuit, state=tk.DISABLED,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=3)

        self.btn_reset = tk.Button(
            btn_frame, text="↺ Сброс", width=10,
            font=("Arial", 9, "bold"), bg="#6c757d", fg="white",
            command=self._reset,
        )
        self.btn_reset.pack(side=tk.LEFT, padx=3)
        row += 1

        # Сохраняем ссылки на виджеты настроек для блокировки
        self._settings_widgets = [
            combo_traj, combo_method,
        ]
        self._settings_vars = [
            self.var_target_speed, self.var_pursuer_speed,
            self.var_distance, self.var_k_att, self.var_k_rep,
            self.var_d0, self.var_sim_speed,
            self.var_obstacles, self.var_save,
        ]

    # ------------------------------------------------------------------ #
    #  Область отображения (Canvas)
    # ------------------------------------------------------------------ #
    def _build_canvas(self, parent):
        """
        Создаёт область визуализации — холст (Canvas) с тёмным фоном.
        На холсте отображаются:
            — сетка координат,
            — препятствия,
            — траектории цели и преследователя,
            — маркеры цели и преследователя.
        """
        canvas_frame = tk.LabelFrame(
            parent, text=" 🖥 Область отображения ",
            font=("Arial", 10, "bold"),
            padx=2, pady=2,
        )
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=COLOR_BG_CANVAS,
            highlightthickness=0,
        )
        self.canvas.pack()

        # Рисуем сетку координат
        self._draw_grid()

    # ------------------------------------------------------------------ #
    #  Область отладочной информации
    # ------------------------------------------------------------------ #
    def _build_debug(self, parent):
        """
        Создаёт область отладочной информации с текстовым полем.
        Отображает:
            — точки старта,
            — формулы траекторий,
            — текущую дистанцию,
            — скорости,
            — время,
            — оценку времени перехвата.
        """
        debug_frame = tk.LabelFrame(
            parent, text=" 🔍 Отладочная информация ",
            font=("Arial", 10, "bold"),
            padx=5, pady=5,
        )
        debug_frame.pack(fill=tk.BOTH, expand=True)

        # Текстовое поле (только чтение) с полосами прокрутки
        self.debug_text = tk.Text(
            debug_frame,
            font=("Consolas", 9),
            wrap=tk.WORD,
            state=tk.DISABLED,        # только чтение
            bg="#f8f9fa",
            relief=tk.FLAT,
            padx=5,
            pady=5,
        )
        scrollbar = tk.Scrollbar(debug_frame, command=self.debug_text.yview)
        self.debug_text.config(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.debug_text.pack(fill=tk.BOTH, expand=True)

        # Начальное сообщение
        self._update_debug_text(
            "Добро пожаловать!\n\n"
            "1. Выберите параметры в области настроек.\n"
            "2. Нажмите «▶ Запуск» для начала моделирования.\n"
            "3. Для прерывания нажмите «■ Прервать».\n"
            "4. Для сброса нажмите «↺ Сброс»."
        )

    # ================================================================== #
    #  Отрисовка на холсте
    # ================================================================== #

    def _draw_grid(self):
        """
        Рисует координатную сетку на холсте.
        Шаг сетки — 100 пикселей.
        """
        # Вертикальные линии
        for x in range(0, CANVAS_WIDTH + 1, 100):
            self.canvas.create_line(
                x, 0, x, CANVAS_HEIGHT,
                fill=COLOR_GRID, dash=(2, 4), tags="grid",
            )
            # Подпись координаты
            if x > 0:
                self.canvas.create_text(
                    x, CANVAS_HEIGHT - 5, text=str(x),
                    fill=COLOR_GRID, font=("Arial", 7), anchor="s", tags="grid",
                )

        # Горизонтальные линии
        for y in range(0, CANVAS_HEIGHT + 1, 100):
            self.canvas.create_line(
                0, y, CANVAS_WIDTH, y,
                fill=COLOR_GRID, dash=(2, 4), tags="grid",
            )
            if y > 0:
                self.canvas.create_text(
                    5, y, text=str(y),
                    fill=COLOR_GRID, font=("Arial", 7), anchor="w", tags="grid",
                )

    def _draw_obstacles(self):
        """Рисует препятствия и их зоны влияния на холсте."""
        self.canvas.delete("obstacle")

        if not self.var_obstacles.get():
            return

        d0 = self.var_d0.get()

        for ox, oy, r in self.obstacles:
            # Зона влияния (полупрозрачный круг)
            self.canvas.create_oval(
                ox - d0 - r, oy - d0 - r,
                ox + d0 + r, oy + d0 + r,
                outline=COLOR_OBSTACLE_RING, dash=(3, 3), width=1,
                tags="obstacle",
            )

            # Само препятствие (заполненный круг)
            self.canvas.create_oval(
                ox - r, oy - r,
                ox + r, oy + r,
                fill=COLOR_OBSTACLE, outline="#adb5bd", width=2,
                tags="obstacle",
            )

            # Метка
            self.canvas.create_text(
                ox, oy, text="⚠", fill="white",
                font=("Arial", 10), tags="obstacle",
            )

    def _draw_trails(self):
        """
        Рисует траектории движения цели и преследователя.
        Траектория цели   — красная сплошная линия.
        Траектория пресл-ля — бирюзовая пунктирная линия.
        """
        self.canvas.delete("trail")

        # Траектория цели (сплошная линия)
        if len(self.target_trail) >= 2:
            # Преобразуем список в плоский список координат
            coords = []
            for pt in self.target_trail:
                coords.extend(pt)
            self.canvas.create_line(
                *coords,
                fill=COLOR_TARGET_TRAIL, width=2,
                dash=(),  # сплошная
                tags="trail",
            )

        # Траектория преследователя (пунктирная линия)
        if len(self.pursuer_trail) >= 2:
            coords = []
            for pt in self.pursuer_trail:
                coords.extend(pt)
            self.canvas.create_line(
                *coords,
                fill=COLOR_PURSUER_TRAIL, width=2,
                dash=(6, 4),  # пунктир
                tags="trail",
            )

    def _draw_markers(self):
        """
        Рисует маркеры цели и преследователя в их текущих позициях.
        Цель — красный круг.
        Преследователь — бирюзовый круг.
        """
        self.canvas.delete("marker")

        if self.target is None or self.pursuer is None:
            return

        tx, ty = self.target.x, self.target.y
        px, py = self.pursuer.x, self.pursuer.y

        # Маркер цели (красный)
        self.canvas.create_oval(
            tx - TARGET_RADIUS, ty - TARGET_RADIUS,
            tx + TARGET_RADIUS, ty + TARGET_RADIUS,
            fill=COLOR_TARGET, outline="white", width=2,
            tags="marker",
        )
        self.canvas.create_text(
            tx, ty - TARGET_RADIUS - 8, text="Цель",
            fill=COLOR_TARGET, font=("Arial", 8, "bold"), tags="marker",
        )

        # Маркер преследователя (бирюзовый)
        self.canvas.create_oval(
            px - PURSUER_RADIUS, py - PURSUER_RADIUS,
            px + PURSUER_RADIUS, py + PURSUER_RADIUS,
            fill=COLOR_PURSUER, outline="white", width=2,
            tags="marker",
        )
        self.canvas.create_text(
            px, py - PURSUER_RADIUS - 8, text="Пресл-ль",
            fill=COLOR_PURSUER, font=("Arial", 8, "bold"), tags="marker",
        )

        # Линия между целью и преследователем (пунктир)
        self.canvas.create_line(
            tx, ty, px, py,
            fill="#ffffff", dash=(3, 6), width=1, tags="marker",
        )

    def _draw_legend(self):
        """Рисует легенду в правом верхнем углу холста."""
        self.canvas.delete("legend")

        x0, y0 = CANVAS_WIDTH - 180, 15

        # Фон легенды
        self.canvas.create_rectangle(
            x0 - 5, y0 - 5, x0 + 175, y0 + 60,
            fill="#16213e", outline="#2a2a4a", tags="legend",
        )

        # Цель — сплошная линия
        self.canvas.create_line(
            x0, y0 + 10, x0 + 30, y0 + 10,
            fill=COLOR_TARGET_TRAIL, width=2, tags="legend",
        )
        self.canvas.create_text(
            x0 + 35, y0 + 10, text="— Цель (сплошная)",
            fill=COLOR_TARGET_TRAIL, font=("Arial", 8), anchor="w", tags="legend",
        )

        # Преследователь — пунктирная линия
        self.canvas.create_line(
            x0, y0 + 30, x0 + 30, y0 + 30,
            fill=COLOR_PURSUER_TRAIL, width=2, dash=(6, 4), tags="legend",
        )
        self.canvas.create_text(
            x0 + 35, y0 + 30, text="— Преследователь (пунктир)",
            fill=COLOR_PURSUER_TRAIL, font=("Arial", 8), anchor="w", tags="legend",
        )

        # Препятствие
        self.canvas.create_oval(
            x0 + 10, y0 + 43, x0 + 22, y0 + 55,
            fill=COLOR_OBSTACLE, tags="legend",
        )
        self.canvas.create_text(
            x0 + 35, y0 + 49, text="— Препятствие",
            fill="#adb5bd", font=("Arial", 8), anchor="w", tags="legend",
        )

    # ================================================================== #
    #  Управление режимами
    # ================================================================== #

    def _lock_settings(self):
        """Блокирует элементы настройки во время моделирования."""
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_reset.config(state=tk.DISABLED)

        # Блокируем виджеты настроек
        for widget in self._settings_widgets:
            widget.config(state=tk.DISABLED)

        # Блокируем ползунки (Scale) и поля ввода (Entry) через переменные
        # Для этого делаем виджеты неактивными
        self._set_settings_state(False)

    def _unlock_settings(self):
        """Разблокирует элементы настройки после остановки."""
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_reset.config(state=tk.NORMAL)

        # Восстанавливаем виджеты
        for widget in self._settings_widgets:
            if isinstance(widget, ttk.Combobox):
                widget.config(state="readonly")
            else:
                widget.config(state=tk.NORMAL)

        self._set_settings_state(True)

    def _set_settings_state(self, enabled: bool):
        """
        Включает/выключает все дочерние виджеты настроек
        (ползунки, поля ввода, галочки).
        """
        state = tk.NORMAL if enabled else tk.DISABLED

        # Проходим по всем потомкам корневого фрейма настроек
        # и переключаем состояние Scale, Entry, Checkbutton
        for widget in self.root.winfo_children():
            self._recursive_set_state(widget, state, "Scale")
            self._recursive_set_state(widget, state, "Entry")
            self._recursive_set_state(widget, state, "Checkbutton")

    def _recursive_set_state(self, widget, state, widget_type):
        """Рекурсивно устанавливает состояние виджетов заданного типа."""
        try:
            if widget.winfo_class() == widget_type:
                widget.config(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._recursive_set_state(child, state, widget_type)

    # ================================================================== #
    #  Запуск преследования
    # ================================================================== #

    def _start_pursuit(self):
        """
        Обработчик кнопки «Запуск».

        Алгоритм:
            1. Считать все параметры из виджетов.
            2. Проверить корректность параметров.
            3. Показать диалог подтверждения с информацией о настройках.
            4. При подтверждении — создать объекты Target и Pursuer,
               запустить анимацию.
        """
        try:
            # ---- Шаг 1: Считываем параметры ----
            traj_type = self.var_trajectory.get()
            method = self.var_method.get()
            target_speed = self.var_target_speed.get()
            pursuer_speed = self.var_pursuer_speed.get()
            distance = self.var_distance.get()
            k_att = self.var_k_att.get()
            k_rep = self.var_k_rep.get()
            d0 = self.var_d0.get()

        except (tk.TclError, ValueError) as e:
            messagebox.showerror("Ошибка параметров",
                                 f"Некорректное значение параметра:\n{e}")
            return

        # ---- Шаг 2: Валидация ----
        if pursuer_speed <= 0 or target_speed <= 0:
            messagebox.showwarning("Внимание",
                                   "Скорости должны быть больше 0!")
            return

        if distance <= 0:
            messagebox.showwarning("Внимание",
                                   "Дистанция должна быть больше 0!")
            return

        # ---- Шаг 3: Диалог подтверждения ----
        info = (
            f"Тип траектории цели: {traj_type}\n"
            f"Метод преследования: {method}\n"
            f"Скорость цели: {target_speed} пкс/сек\n"
            f"Скорость преследователя: {pursuer_speed} пкс/сек\n"
            f"Начальная дистанция: {distance} пкс\n"
            f"Препятствия: {'Да' if self.var_obstacles.get() else 'Нет'}\n"
            f"Сохранить в файл: {'Да' if self.var_save.get() else 'Нет'}\n"
            f"\nЗапустить моделирование?"
        )
        result = messagebox.askyesno("Подтверждение запуска", info)
        if not result:
            return

        # ---- Шаг 4: Инициализация модели ----
        # Определяем начальные позиции
        # Преследователь — слева, цель — справа на указанной дистанции
        angle = random.uniform(-math.pi / 6, math.pi / 6)  # небольшой разброс
        cx = CANVAS_WIDTH / 2
        cy = CANVAS_HEIGHT / 2

        pursuer_x = cx - (distance / 2) * math.cos(angle)
        pursuer_y = cy - (distance / 2) * math.sin(angle)
        target_x = cx + (distance / 2) * math.cos(angle)
        target_y = cy + (distance / 2) * math.sin(angle)

        # Ограничиваем позиции в пределах холста
        pursuer_x = max(MARGIN, min(CANVAS_WIDTH - MARGIN, pursuer_x))
        pursuer_y = max(MARGIN, min(CANVAS_HEIGHT - MARGIN, pursuer_y))
        target_x = max(MARGIN, min(CANVAS_WIDTH - MARGIN, target_x))
        target_y = max(MARGIN, min(CANVAS_HEIGHT - MARGIN, target_y))

        # Создаём объекты
        self.target = Target(target_x, target_y, target_speed, traj_type)
        self.pursuer = Pursuer(
            pursuer_x, pursuer_y, pursuer_speed, method,
            k_att=k_att, k_rep=k_rep, d0=d0,
        )

        # Настраиваем препятствия
        if self.var_obstacles.get():
            self.obstacles = list(DEFAULT_OBSTACLES)
        else:
            self.obstacles = []

        # Границы для цели (отражение)
        self.bounds = (MARGIN, MARGIN, CANVAS_WIDTH - MARGIN, CANVAS_HEIGHT - MARGIN)

        # Сбрасываем данные
        self.target_trail = [(target_x, target_y)]
        self.pursuer_trail = [(pursuer_x, pursuer_y)]
        self.history = []
        self.simulation_time = 0.0
        self.caught = False

        # Вычисляем начальную дистанцию
        dx = target_x - pursuer_x
        dy = target_y - pursuer_y
        self.initial_distance = math.sqrt(dx * dx + dy * dy)

        # ---- Шаг 5: Блокируем настройки и запускаем ----
        self._lock_settings()
        self.is_running = True

        # Отрисовываем начальное состояние
        self._redraw_canvas()

        # Запускаем цикл анимации
        self._animation_step()

    # ================================================================== #
    #  Цикл анимации
    # ================================================================== #

    def _animation_step(self):
        """
        Один шаг анимации — вызывается периодически через root.after().

        Алгоритм:
            1. Вычислить dt (шаг времени) с учётом скорости симуляции.
            2. Обновить позицию цели.
            3. Обновить позицию преследователя.
            4. Проверить условия завершения (поимка / таймаут).
            5. Сохранить данные в историю.
            6. Обновить холст и отладочную информацию.
            7. Запланировать следующий кадр.
        """
        if not self.is_running:
            return

        try:
            # ---- Шаг 1: Вычисляем dt ----
            sim_speed = self.var_sim_speed.get()
            dt = (FRAME_INTERVAL_MS / 1000.0) * sim_speed

            # ---- Шаг 2: Обновляем позицию цели ----
            self.target.update(dt, self.bounds)

            # ---- Шаг 3: Обновляем позицию преследователя ----
            target_pos = (self.target.x, self.target.y)
            self.pursuer.update(dt, target_pos, self.obstacles)

            # Ограничиваем позицию преследователя в пределах холста
            self.pursuer.x = max(0, min(CANVAS_WIDTH, self.pursuer.x))
            self.pursuer.y = max(0, min(CANVAS_HEIGHT, self.pursuer.y))

            # ---- Обновляем время ----
            self.simulation_time += dt

            # ---- Запоминаем траектории ----
            self.target_trail.append((self.target.x, self.target.y))
            self.pursuer_trail.append((self.pursuer.x, self.pursuer.y))

            # ---- Вычисляем текущую дистанцию ----
            dx = self.target.x - self.pursuer.x
            dy = self.target.y - self.pursuer.y
            current_distance = math.sqrt(dx * dx + dy * dy)

            # ---- Сохраняем данные в историю ----
            self.history.append({
                "time": self.simulation_time,
                "target_x": self.target.x,
                "target_y": self.target.y,
                "target_speed": self.target.get_current_speed(),
                "pursuer_x": self.pursuer.x,
                "pursuer_y": self.pursuer.y,
                "pursuer_speed": self.pursuer.get_current_speed(),
                "distance": current_distance,
            })

            # ---- Шаг 4: Проверяем условия завершения ----
            # Поимка
            if current_distance <= CATCH_DISTANCE:
                self.caught = True
                self._on_pursuit_end(
                    success=True,
                    message=f"✅ Цель поймана за {self.simulation_time:.2f} сек!"
                )
                return

            # Таймаут
            if self.simulation_time >= MAX_SIMULATION_TIME:
                self._on_pursuit_end(
                    success=False,
                    message=f"⏰ Время истекло ({MAX_SIMULATION_TIME:.0f} сек). Цель не поймана.",
                )
                return

            # ---- Шаг 6: Обновляем визуализацию ----
            self._redraw_canvas()
            self._update_debug_info()

            # ---- Шаг 7: Планируем следующий кадр ----
            self.animation_id = self.root.after(FRAME_INTERVAL_MS, self._animation_step)

        except Exception as e:
            # Обработка ошибок — ПО не должно «падать»
            self.is_running = False
            self._unlock_settings()
            messagebox.showerror(
                "Ошибка моделирования",
                f"Произошла ошибка:\n{type(e).__name__}: {e}"
            )

    # ================================================================== #
    #  Завершение преследования
    # ================================================================== #

    def _on_pursuit_end(self, success: bool, message: str):
        """
        Обработчик завершения преследования (поимка / таймаут / прерывание).

        Параметры:
            success : True — цель поймана, False — нет
            message : сообщение для отображения
        """
        self.is_running = False
        self._unlock_settings()

        # Обновляем визуализацию в последний раз
        self._redraw_canvas()
        self._update_debug_info()

        # Показываем результат
        messagebox.showinfo("Результат", message)

        # Сохраняем результаты в файл (если установлена галочка)
        if self.var_save.get():
            self._save_results(success)

    def _stop_pursuit(self):
        """Обработчик кнопки «Прервать» — останавливает моделирование."""
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None

        self._on_pursuit_end(
            success=False,
            message=f"⏹ Моделирование прервано пользователем на {self.simulation_time:.2f} сек.",
        )

    def _reset(self):
        """Обработчик кнопки «Сброс» — очищает холст и данные."""
        # Очищаем холст от объектов моделирования
        self.canvas.delete("trail")
        self.canvas.delete("marker")
        self.canvas.delete("obstacle")
        self.canvas.delete("legend")

        # Сбрасываем состояние
        self.target = None
        self.pursuer = None
        self.obstacles = []
        self.target_trail = []
        self.pursuer_trail = []
        self.history = []
        self.simulation_time = 0.0
        self.caught = False

        # Обновляем отладочную информацию
        self._update_debug_text(
            "Сброс выполнен.\n\n"
            "Выберите параметры и нажмите «▶ Запуск»."
        )

    # ================================================================== #
    #  Обновление отладочной информации
    # ================================================================== #

    def _update_debug_info(self):
        """
        Обновляет текст в области отладочной информации.
        Выводит:
            — точки старта,
            — формулы траекторий,
            — текущую дистанцию,
            — скорости цели и преследователя,
            — время моделирования,
            — оценочное время перехвата.
        """
        if self.target is None or self.pursuer is None:
            return

        # Текущая дистанция
        dx = self.target.x - self.pursuer.x
        dy = self.target.y - self.pursuer.y
        dist = math.sqrt(dx * dx + dy * dy)

        # Скорости
        t_speed = self.target.get_current_speed()
        p_speed = self.pursuer.get_current_speed()

        # Оценка времени перехвата
        target_vel = self.target.get_velocity()
        eta = self.pursuer.estimate_catch_time(
            (self.target.x, self.target.y), target_vel
        )
        if eta == float("inf"):
            eta_str = "∞ (не догонит)"
        else:
            eta_str = f"{eta:.2f} сек"

        # Формируем текст
        text = (
            f"═══ Точки старта ═══\n"
            f"  Цель:          ({self.target.x0:.1f}, {self.target.y0:.1f})\n"
            f"  Преследователь: ({self.pursuer.x0:.1f}, {self.pursuer.y0:.1f})\n"
            f"\n"
            f"═══ Формулы траекторий ═══\n"
            f"  Цель:\n    {self.target.get_formula().replace(chr(10), chr(10) + '    ')}\n"
            f"  Преследователь:\n    {self.pursuer.get_formula().replace(chr(10), chr(10) + '    ')}\n"
            f"\n"
            f"═══ Текущие параметры ═══\n"
            f"  Дистанция:       {dist:.1f} пкс\n"
            f"  Скорость цели:   {t_speed:.1f} пкс/сек\n"
            f"  Скорость пресл.: {p_speed:.1f} пкс/сек\n"
            f"  Время:           {self.simulation_time:.2f} сек\n"
            f"  Расч. время перехвата: {eta_str}\n"
        )

        self._update_debug_text(text)

    def _update_debug_text(self, text: str):
        """Обновляет содержимое текстового виджета отладки."""
        self.debug_text.config(state=tk.NORMAL)
        self.debug_text.delete("1.0", tk.END)
        self.debug_text.insert("1.0", text)
        self.debug_text.config(state=tk.DISABLED)

    # ================================================================== #
    #  Перерисовка холста
    # ================================================================== #

    def _redraw_canvas(self):
        """Полная перерисовка элементов моделирования на холсте."""
        self._draw_obstacles()
        self._draw_trails()
        self._draw_markers()
        self._draw_legend()

    # ================================================================== #
    #  Сохранение результатов в файл
    # ================================================================== #

    def _save_results(self, caught: bool):
        """
        Сохраняет результаты моделирования в текстовый файл.

        Формат файла:
            Заголовок: тип траектории, метод, дистанция, время, статус
            Таблица шагов: координаты, скорости, время, дистанция.

        Параметры:
            caught : True — цель поймана, False — нет
        """
        try:
            # Генерируем имя файла с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"pursuit_result_{timestamp}.txt"

            with open(filename, "w", encoding="utf-8") as f:
                # ---- Заголовок ----
                f.write(
                    f"{'='*60}\n"
                    f"  РЕЗУЛЬТАТЫ МОДЕЛИРОВАНИЯ ПРЕСЛЕДОВАНИЯ\n"
                    f"{'='*60}\n\n"
                )
                f.write(f"Тип траектории цели:  {self.target.trajectory_type}\n")
                f.write(f"Метод преследования:  {self.pursuer.method}\n")
                f.write(f"Исходная дистанция:   {self.initial_distance:.1f} пкс\n")
                f.write(
                    f"Суммарное время:      {self.simulation_time:.2f} сек\n"
                )
                f.write(
                    f"Результат:            {'Догнал' if caught else 'Нет'}\n\n"
                )

                # ---- Таблица данных ----
                f.write(f"{'-'*90}\n")
                f.write(
                    f"{'Цель (x,y)':<20} "
                    f"{'v цель':>10} "
                    f"{'Пресл. (x,y)':<20} "
                    f"{'v пресл.':>10} "
                    f"{'Время':>8} "
                    f"{'Дист.':>10}\n"
                )
                f.write(f"{'-'*90}\n")

                for h in self.history:
                    f.write(
                        f"({h['target_x']:7.1f}, {h['target_y']:7.1f})   "
                        f"{h['target_speed']:8.1f}   "
                        f"({h['pursuer_x']:7.1f}, {h['pursuer_y']:7.1f})   "
                        f"{h['pursuer_speed']:8.1f}   "
                        f"{h['time']:7.2f}   "
                        f"{h['distance']:9.1f}\n"
                    )

                f.write(f"{'-'*90}\n")
                f.write(f"\nВсего записей: {len(self.history)}\n")

            messagebox.showinfo(
                "Сохранение",
                f"Результаты сохранены в файл:\n{os.path.abspath(filename)}"
            )

        except Exception as e:
            messagebox.showerror(
                "Ошибка сохранения",
                f"Не удалось сохранить файл:\n{e}"
            )


# ====================================================================== #
#  Точка входа — запуск приложения
# ====================================================================== #

if __name__ == "__main__":
    root = tk.Tk()
    app = PursuitApp(root)
    root.mainloop()
