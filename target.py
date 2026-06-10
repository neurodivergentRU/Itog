"""
================================================================================
Модуль target.py — Модель поведения цели
================================================================================

Описание:
    Данный модуль содержит класс Target, который моделирует движение цели
    с различными типами траекторий:
    
    1. Прямолинейная      — равномерное прямолинейное движение с отражением
                            от границ рабочей области.
    2. Циркуляционная     — движение по окружности с заданным радиусом
                            и угловой скоростью.
    3. Случайные маневры  — хаотичная траектория с периодической случайной
                            сменой направления движения.
    4. Рывки              — чередование фаз резкого ускорения (рывок) и
                            постепенного замедления (плавление).

    Координатная система: начало (0, 0) — левый верхний угол Canvas,
    ось X направлена вправо, ось Y — вниз.

Автор: Курсовая работа по дисциплине «Методы ИИ для беспилотных систем»
================================================================================
"""

import math
import random


class Target:
    """
    Класс цели — описывает движение цели по одной из поддерживаемых траекторий.
    
    Атрибуты:
        x, y           (float) : текущие координаты цели (пиксели)
        x0, y0         (float) : начальные координаты цели
        speed          (float) : базовая скорость движения (пикселей/сек)
        trajectory_type (str)  : тип траектории
        time           (float) : время, прошедшее с начала моделирования (сек)
    """

    # ------------------------------------------------------------------ #
    #  Константы — названия типов траекторий (используются в GUI)
    # ------------------------------------------------------------------ #
    STRAIGHT      = "Прямолинейная"
    CIRCULAR      = "Циркуляционная"
    RANDOM_MANEUVER = "Случайные маневры"
    JERKS         = "Рывки"

    # Список всех доступных типов для выпадающего списка
    TYPES = [STRAIGHT, CIRCULAR, RANDOM_MANEUVER, JERKS]

    def __init__(self, x0: float, y0: float, speed: float, trajectory_type: str):
        """
        Конструктор класса Target.
        
        Параметры:
            x0, y0          : начальные координаты (пиксели)
            speed           : базовая скорость (пикселей/сек)
            trajectory_type : один из Target.TYPES
        """
        # ---- Сохраняем начальные параметры ----
        self.x0 = x0                      # начальная координата X
        self.y0 = y0                      # начальная координата Y
        self.speed = speed                # базовая скорость
        self.trajectory_type = trajectory_type  # тип траектории
        self.time = 0.0                   # счётчик времени моделирования

        # ---- Текущая позиция ----
        self.x = x0
        self.y = y0

        # ================================================================ #
        #  Параметры для каждого типа траектории
        # ================================================================ #

        # --- Прямолинейная траектория ---
        # Цель движется по прямой в случайном направлении.
        # При достижении границы области — отражается (упругий удар).
        self.angle = random.uniform(0, 2 * math.pi)  # случайный начальный угол
        self.vx = speed * math.cos(self.angle)        # компонента скорости по X
        self.vy = speed * math.sin(self.angle)        # компонента скорости по Y

        # --- Циркуляционная траектория ---
        # Движение по окружности: x(t) = x0 + R·cos(ωt), y(t) = y0 + R·sin(ωt)
        # Угловая скорость ω = v / R, где v — линейная скорость, R — радиус.
        self.circle_radius = 100.0                    # радиус окружности (пиксели)
        self.circle_omega = speed / self.circle_radius  # угловая скорость (рад/с)
        self.circle_phase = 0.0                       # начальная фаза (рад)

        # --- Случайные маневры ---
        # Через случайные интервалы времени цель меняет направление движения
        # на случайный угол, что создаёт хаотичную траекторию.
        self.maneuver_timer = 0.0                     # таймер до следующей смены
        self.maneuver_interval = random.uniform(1.0, 3.0)  # интервал смены (сек)
        self.current_direction = random.uniform(0, 2 * math.pi)  # текущий угол

        # --- Рывки (jerk) ---
        # Чередование фаз:
        #   «accelerate» — резкое ускорение (скорость × 2.5) в течение jerk_accel_duration
        #   «coast»      — замедление (скорость × 0.3) в течение jerk_coast_duration
        self.jerk_state = "accelerate"                # текущая фаза
        self.jerk_timer = 0.0                         # таймер текущей фазы
        self.jerk_accel_duration = 0.4                # длительность рывка (сек)
        self.jerk_coast_duration = 0.8                # длительность замедления (сек)
        self.current_speed_factor = 1.0               # множитель скорости
        self.jerk_direction = random.uniform(0, 2 * math.pi)  # направление рывка

    # ================================================================== #
    #  Основной метод обновления позиции
    # ================================================================== #
    def update(self, dt: float, bounds: tuple):
        """
        Обновить позицию цели на один временной шаг.
        
        Параметры:
            dt    : шаг интегрирования (сек)
            bounds: кортеж (x_min, y_min, x_max, y_max) — границы области
        """
        self.time += dt  # наращиваем время

        # Вызываем соответствующий приватный метод в зависимости от типа
        if self.trajectory_type == self.STRAIGHT:
            self._update_straight(dt, bounds)
        elif self.trajectory_type == self.CIRCULAR:
            self._update_circular(dt)
        elif self.trajectory_type == self.RANDOM_MANEUVER:
            self._update_random(dt, bounds)
        elif self.trajectory_type == self.JERKS:
            self._update_jerks(dt, bounds)

    # ================================================================== #
    #  Приватные методы обновления для каждого типа траектории
    # ================================================================== #

    def _update_straight(self, dt: float, bounds: tuple):
        """
        Прямолинейное равномерное движение.
        
        Формулы:
            x(t+dt) = x(t) + vx · dt
            y(t+dt) = y(t) + vy · dt
        
        При выходе за границу — отражение (знак скорости меняется на opposite).
        """
        self.x += self.vx * dt
        self.y += self.vy * dt

        x_min, y_min, x_max, y_max = bounds

        # Отражение от вертикальных границ
        if self.x <= x_min:
            self.x = x_min
            self.vx = abs(self.vx)          # направляем вправо
        elif self.x >= x_max:
            self.x = x_max
            self.vx = -abs(self.vx)         # направляем влево

        # Отражение от горизонтальных границ
        if self.y <= y_min:
            self.y = y_min
            self.vy = abs(self.vy)           # направляем вниз
        elif self.y >= y_max:
            self.y = y_max
            self.vy = -abs(self.vy)          # направляем вверх

    def _update_circular(self, dt: float):
        """
        Циркуляционное (круговое) движение.
        
        Формулы:
            x(t) = x0 + R · cos(ω · t + φ0)
            y(t) = y0 + R · sin(ω · t + φ0)
        
        Где:
            R  — радиус окружности,
            ω  — угловая скорость = v / R,
            φ0 — начальная фаза.
        
        Примечание: для круговой траектории границы не проверяются,
        так как окружность полностью лежит внутри рабочей области.
        """
        angle = self.circle_omega * self.time + self.circle_phase
        self.x = self.x0 + self.circle_radius * math.cos(angle)
        self.y = self.y0 + self.circle_radius * math.sin(angle)

    def _update_random(self, dt: float, bounds: tuple):
        """
        Случайные маневры — периодическая хаотичная смена направления.
        
        Алгоритм:
            1. Каждые maneuver_interval секунд генерируем новый угол поворота
               (отклонение от текущего направления на ±π/2).
            2. Двигаемся с базовой скоростью в текущем направлении.
            3. При столкновении с границей — отражаемся.
        """
        self.maneuver_timer += dt

        # Проверяем, настало ли время сменить направление
        if self.maneuver_timer >= self.maneuver_interval:
            self.maneuver_timer = 0.0
            # Новый случайный интервал до следующей смены
            self.maneuver_interval = random.uniform(0.8, 2.5)
            # Отклоняем направление на случайный угол (до ±80°)
            self.current_direction += random.uniform(-math.pi * 0.8, math.pi * 0.8)

        # Обновляем позицию
        self.x += self.speed * math.cos(self.current_direction) * dt
        self.y += self.speed * math.sin(self.current_direction) * dt

        # Отражение от границ
        x_min, y_min, x_max, y_max = bounds
        if self.x <= x_min or self.x >= x_max:
            self.current_direction = math.pi - self.current_direction
            self.x = max(x_min, min(self.x, x_max))
        if self.y <= y_min or self.y >= y_max:
            self.current_direction = -self.current_direction
            self.y = max(y_min, min(self.y, y_max))

    def _update_jerks(self, dt: float, bounds: tuple):
        """
        Рывковая траектория — чередование резких ускорений и замедлений.
        
        Фазы:
            «accelerate»: скорость = base_speed × 2.5, длительность = 0.4 сек
            «coast»     : скорость = base_speed × 0.3, длительность = 0.8 сек
        
        При смене фазы направление движения меняется на случайное
        (или отклоняется от текущего).
        """
        self.jerk_timer += dt

        if self.jerk_state == "accelerate":
            # Фаза рывка — высокая скорость
            self.current_speed_factor = 2.5
            if self.jerk_timer >= self.jerk_accel_duration:
                # Переходим к фазе замедления
                self.jerk_state = "coast"
                self.jerk_timer = 0.0
                # Слегка меняем направление
                self.jerk_direction += random.uniform(-math.pi / 3, math.pi / 3)
        else:
            # Фаза замедления — низкая скорость
            self.current_speed_factor = 0.3
            if self.jerk_timer >= self.jerk_coast_duration:
                # Переходим к фазе рывка
                self.jerk_state = "accelerate"
                self.jerk_timer = 0.0
                # Новое случайное направление рывка
                self.jerk_direction = random.uniform(0, 2 * math.pi)

        # Текущая скорость с учётом множителя фазы
        current_speed = self.speed * self.current_speed_factor
        self.x += current_speed * math.cos(self.jerk_direction) * dt
        self.y += current_speed * math.sin(self.jerk_direction) * dt

        # Отражение от границ
        x_min, y_min, x_max, y_max = bounds
        if self.x <= x_min or self.x >= x_max:
            self.jerk_direction = math.pi - self.jerk_direction
            self.x = max(x_min, min(self.x, x_max))
        if self.y <= y_min or self.y >= y_max:
            self.jerk_direction = -self.jerk_direction
            self.y = max(y_min, min(self.y, y_max))

    # ================================================================== #
    #  Методы получения информации о текущем состоянии
    # ================================================================== #

    def get_formula(self) -> str:
        """
        Возвращает строковое описание формулы траектории.
        Используется для отображения в области отладочной информации.
        """
        if self.trajectory_type == self.STRAIGHT:
            return (
                f"x(t) = {self.x0:.1f} + {self.vx:.1f} · t\n"
                f"y(t) = {self.y0:.1f} + {self.vy:.1f} · t"
            )
        elif self.trajectory_type == self.CIRCULAR:
            return (
                f"x(t) = {self.x0:.1f} + {self.circle_radius:.0f} · "
                f"cos({self.circle_omega:.2f} · t)\n"
                f"y(t) = {self.y0:.1f} + {self.circle_radius:.0f} · "
                f"sin({self.circle_omega:.2f} · t)"
            )
        elif self.trajectory_type == self.RANDOM_MANEUVER:
            return (
                "x(t), y(t) — стохастическая траектория\n"
                "(периодическая случайная смена направления)"
            )
        elif self.trajectory_type == self.JERKS:
            return (
                "x(t), y(t) — рывковая траектория\n"
                "(ускорение ×2.5 / замедление ×0.3)"
            )
        return "Неизвестный тип траектории"

    def get_current_speed(self) -> float:
        """
        Возвращает текущую скалярную скорость цели (пикселей/сек).
        Для рывковой траектории скорость зависит от текущей фазы.
        """
        if self.trajectory_type == self.JERKS:
            return self.speed * self.current_speed_factor
        # Для остальных типов скорость постоянна
        return self.speed

    def get_velocity(self) -> tuple:
        """
        Возвращает текущий вектор скорости (vx, vy) в пикселях/сек.
        Используется для расчёта оценки времени перехвата.
        """
        if self.trajectory_type == self.STRAIGHT:
            return self.vx, self.vy

        elif self.trajectory_type == self.CIRCULAR:
            # Производная параметрического уравнения окружности:
            #   vx = -R · ω · sin(ωt + φ0)
            #   vy =  R · ω · cos(ωt + φ0)
            angle = self.circle_omega * self.time + self.circle_phase
            vx = -self.circle_radius * self.circle_omega * math.sin(angle)
            vy =  self.circle_radius * self.circle_omega * math.cos(angle)
            return vx, vy

        elif self.trajectory_type == self.RANDOM_MANEUVER:
            return (
                self.speed * math.cos(self.current_direction),
                self.speed * math.sin(self.current_direction),
            )

        elif self.trajectory_type == self.JERKS:
            s = self.speed * self.current_speed_factor
            return (
                s * math.cos(self.jerk_direction),
                s * math.sin(self.jerk_direction),
            )

        return 0.0, 0.0
