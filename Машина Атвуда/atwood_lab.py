"""PyQt virtual lab: determination of g using an Atwood machine.

Run with ``python atwood_lab.py`` after installing PyQt6 or PyQt5.  The app
does not save or export student measurements; the student records them in the
paper/digital report supplied by the teacher.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

try:
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QColor, QPainter, QPen
    from PyQt6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
                                 QGroupBox, QHBoxLayout, QLabel, QMainWindow,
                                 QPushButton, QSpinBox, QVBoxLayout, QWidget)
    ALIGN_CENTER = Qt.AlignmentFlag.AlignCenter
    QT_AVAILABLE = True
except ImportError:
    try:
        from PyQt5.QtCore import Qt, QTimer
        from PyQt5.QtGui import QColor, QPainter, QPen
        from PyQt5.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
                                     QGroupBox, QHBoxLayout, QLabel, QMainWindow,
                                     QPushButton, QSpinBox, QVBoxLayout, QWidget)
        ALIGN_CENTER = Qt.AlignCenter
        QT_AVAILABLE = True
    except ImportError:
        QT_AVAILABLE = False

from atwood_physics import Trial, student_random_gravity
from atwood_geometry import (MAX_DISTANCE_CM, RULER_MAX_CM,
                             machine_geometry, mass_positions)

PHASE_TWO_HEIGHT_CM = 50


if QT_AVAILABLE:
    class MachineView(QWidget):
        """Animated, labelled Atwood machine and centimetre ruler."""

        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(440, 480)
            self.set_distance_cm(20)
            self.set_progress(0.0)

        def set_distance_cm(self, distance: int):
            distance = int(distance)
            if distance != getattr(self, "distance_cm", None):
                # A changed setup is a fresh, clamped run at h2.
                self.progress = 0.0
            self.distance_cm = distance
            self.update()

        def set_progress(self, fraction: float):
            self.progress = max(0.0, min(1.0, float(fraction)))
            self.update()

        def paintEvent(self, event):
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing if hasattr(QPainter, "RenderHint") else QPainter.Antialiasing)
            w, h = self.width(), self.height()
            geom = machine_geometry(w, h)
            mass = mass_positions(geom, self.distance_cm, self.progress)
            painter.fillRect(self.rect(), QColor("#f7f9fc"))

            # Stand, wheel and support.
            stand_x = geom.stand_x
            pulley_x, pulley_y, radius = stand_x, geom.pulley_y, geom.pulley_radius
            gate_y, ruler_x = geom.gate_y, geom.ruler_x
            painter.setPen(QPen(QColor("#62748b"), 7))
            painter.drawLine(stand_x, pulley_y - radius - 12, stand_x, h - 42)
            painter.setPen(QPen(QColor("#62748b"), 4))
            painter.drawLine(stand_x - 72, h - 40, stand_x + 72, h - 40)
            painter.setPen(QPen(QColor("#34465d"), 4))
            painter.setBrush(QColor("#dce5ef"))
            painter.drawEllipse(pulley_x - radius, pulley_y - radius,
                                2 * radius, 2 * radius)
            painter.setBrush(QColor("#34465d"))
            painter.drawEllipse(pulley_x - 5, pulley_y - 5, 10, 10)

            # The full 100 cm ruler runs from h1 to the upper block position.
            # It remains fixed as H changes.
            pixels_per_cm = geom.pixels_per_cm
            painter.setPen(QPen(QColor("#65758b"), 2))
            ruler_top = gate_y - RULER_MAX_CM * pixels_per_cm
            painter.drawLine(ruler_x, int(ruler_top),
                             ruler_x, gate_y + 1)
            for cm in range(0, RULER_MAX_CM + 1):
                yy = gate_y - cm * pixels_per_cm
                major = cm % 10 == 0
                if not major and pixels_per_cm < 2.5 and cm % 5 != 0:
                    continue
                painter.setPen(QPen(QColor("#65758b"), 2 if major else 1))
                painter.drawLine(ruler_x - (13 if major else 5), int(yy),
                                 ruler_x, int(yy))
                label_step = 20 if pixels_per_cm < 2.5 else 10
                if cm % label_step == 0:
                    painter.setPen(QColor("#40536b"))
                    painter.drawText(ruler_x + 5, int(yy + 5), f"{cm}")
            painter.setPen(QColor("#40536b"))
            painter.drawText(ruler_x - 12, int(ruler_top) - 23,
                             24, 18, ALIGN_CENTER, "см")

            # Gate marker h1 and starting lower edge h2.
            start_y = mass.start_lower_edge_y
            painter.setPen(QPen(QColor("#218c74"), 3, Qt.PenStyle.DashLine if hasattr(Qt, "PenStyle") else Qt.DashLine))
            painter.drawLine(ruler_x - 30, gate_y, ruler_x + 20, gate_y)
            painter.setPen(QColor("#218c74"))
            painter.drawText(ruler_x - 53, gate_y + 19, "h₁ = 0")
            painter.setPen(QPen(QColor("#dd8b16"), 2, Qt.PenStyle.DashLine if hasattr(Qt, "PenStyle") else Qt.DashLine))
            painter.drawLine(ruler_x - 30, int(start_y), ruler_x + 20, int(start_y))
            painter.setPen(QColor("#a96500"))
            painter.drawText(ruler_x - 38, int(start_y) - 7, "h₂")
            painter.setPen(QPen(QColor("#218c74"), 2))
            painter.drawLine(ruler_x - 23, gate_y - 3,
                             ruler_x - 23, int(start_y) + 3)
            painter.drawLine(ruler_x - 23, gate_y - 3, ruler_x - 28, gate_y - 10)
            painter.drawLine(ruler_x - 23, gate_y - 3, ruler_x - 18, gate_y - 10)
            painter.drawLine(ruler_x - 23, int(start_y) + 3, ruler_x - 28, int(start_y) + 10)
            painter.drawLine(ruler_x - 23, int(start_y) + 3, ruler_x - 18, int(start_y) + 10)
            painter.setPen(QColor("#218c74"))
            painter.drawText(ruler_x + 28, int((start_y + gate_y) / 2),
                             f"H = {self.distance_cm} см")

            # The photogate/platform is aligned with h1 and the final lower edge.
            painter.setPen(QPen(QColor("#218c74"), 4))
            painter.drawLine(stand_x + radius + 8, gate_y, ruler_x - 28, gate_y)
            painter.setBrush(QColor("#58b99c"))
            painter.setPen(Qt.PenStyle.NoPen if hasattr(Qt, "PenStyle") else Qt.NoPen)
            painter.drawEllipse(stand_x + 40, gate_y - 5, 10, 10)
            painter.setPen(QColor("#218c74"))
            painter.drawText(stand_x + radius + 10, gate_y + 26, "фотодатчик")

            # h2 marks the right block's lower edge. The left block begins at
            # the complementary position on the same fixed-length rope. During
            # the run they move equally in opposite directions.
            left_x, right_x = geom.left_x, geom.right_x
            block_w, block_h = geom.block_width, geom.block_height
            left_y, right_y = mass.left_top_y, mass.right_top_y
            left_center_x = left_x + block_w // 2
            right_center_x = right_x + block_w // 2
            painter.setPen(QPen(QColor("#47586d"), 2))
            painter.drawLine(left_center_x, int(left_y), left_center_x, pulley_y)
            painter.drawLine(left_center_x, pulley_y, pulley_x - radius, pulley_y)
            painter.drawLine(pulley_x + radius, pulley_y, right_center_x, pulley_y)
            painter.drawLine(right_center_x, pulley_y, right_center_x, int(right_y))

            # Left mass M.
            painter.setPen(QPen(QColor("#365f91"), 2))
            painter.setBrush(QColor("#8eb6e3"))
            painter.drawRoundedRect(left_x, int(left_y), block_w, block_h, 5, 5)
            painter.setPen(QColor("#173b65"))
            painter.drawText(left_x, int(left_y + block_h / 2 - 10),
                             block_w, 20, ALIGN_CENTER, "M")

            # Right mass M with removable overload m.
            painter.setPen(QPen(QColor("#a65d27"), 2))
            painter.setBrush(QColor("#edb47f"))
            painter.drawRoundedRect(right_x, int(right_y), block_w, block_h, 5, 5)
            painter.setPen(QColor("#71390f"))
            painter.drawText(right_x, int(right_y + block_h / 2 - 10),
                             block_w, 20, ALIGN_CENTER, "M")
            painter.setBrush(QColor("#e2a43e"))
            painter.setPen(QPen(QColor("#a66e18"), 1))
            plate_height = max(12, int(block_h * 0.28))
            plate_width = max(20, block_w - 14)
            painter.drawRoundedRect(right_x + (block_w - plate_width) // 2,
                                    int(right_y) - plate_height,
                                    plate_width, plate_height, 3, 3)
            painter.setPen(QColor("#613f0c"))
            painter.drawText(right_x + (block_w - plate_width) // 2,
                             int(right_y) - plate_height + 1, plate_width,
                             plate_height, ALIGN_CENTER, "m")
            painter.setPen(QColor("#33465d"))
            painter.end()


    class AtwoodLabWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Лабораторная работа: машина Атвуда")
            self.setMinimumSize(1050, 700)
            self.setMaximumSize(1920, 1080)
            self.resize(1500, 920)
            self.mass_each_g = 200
            self.overload_g = 20
            self.distance_cm = 20
            self.repeat_number = 1
            self.timer_running = False
            self.motion_running = False
            self.run_locked = False
            self.started_at = 0.0
            self.trial = None
            self._build_ui()
            self.clock = QTimer(self)
            self.clock.setInterval(16)
            self.clock.timeout.connect(self._tick)

        def _build_ui(self):
            central = QWidget()
            self.setCentralWidget(central)
            root = QVBoxLayout(central)
            root.setContentsMargins(22, 18, 22, 18)
            root.setSpacing(12)

            title = QLabel("Определение ускорения свободного падения")
            title.setStyleSheet("font-size: 23px; font-weight: 700; color: #1f334d")
            subtitle = QLabel("Виртуальная лабораторная работа • машина Атвуда")
            subtitle.setStyleSheet("font-size: 14px; color: #62748b")
            root.addWidget(title)
            root.addWidget(subtitle)

            content = QHBoxLayout()
            content.setSpacing(18)
            root.addLayout(content, 1)

            panel = QVBoxLayout()
            panel.setSpacing(12)
            content.addLayout(panel, 0)

            setup = QGroupBox("Условия опыта")
            setup_grid = QGridLayout(setup)
            self.mode = QComboBox()
            self.mode.addItem("1. Изменять высоту H")
            self.mode.addItem("2. Изменять перегрузок m")
            self.mass_spin = QSpinBox()
            self.mass_spin.setRange(50, 1000)
            self.mass_spin.setValue(200)
            self.mass_spin.setSuffix(" г")
            self.distance_spin = QSpinBox()
            self.distance_spin.setRange(10, MAX_DISTANCE_CM)
            self.distance_spin.setSingleStep(2)
            self.distance_spin.setValue(20)
            self.distance_spin.setSuffix(" см")
            self.overload_combo = QComboBox()
            self.overload_combo.addItems(["10 г", "20 г", "30 г", "40 г", "50 г"])
            self.overload_combo.setCurrentIndex(1)
            setup_grid.addWidget(QLabel("Масса каждого груза M:"), 0, 0)
            setup_grid.addWidget(self.mass_spin, 0, 1)
            setup_grid.addWidget(QLabel("Режим:"), 1, 0)
            setup_grid.addWidget(self.mode, 1, 1)
            setup_grid.addWidget(QLabel("Перегрузок m:"), 2, 0)
            setup_grid.addWidget(self.overload_combo, 2, 1)
            setup_grid.addWidget(QLabel("Расстояние H:"), 3, 0)
            setup_grid.addWidget(self.distance_spin, 3, 1)
            panel.addWidget(setup)

            stopwatch = QGroupBox("Миллисекундомер")
            watch_layout = QVBoxLayout(stopwatch)
            self.timer_label = QLabel("00.000 с")
            self.timer_label.setAlignment(ALIGN_CENTER)
            self.timer_label.setStyleSheet("font-family: monospace; font-size: 34px; font-weight: 700; color: #183b5b")
            watch_layout.addWidget(self.timer_label)
            buttons = QHBoxLayout()
            self.toggle_button = QPushButton("ВКЛ")
            self.toggle_button.setMinimumHeight(42)
            self.toggle_button.setStyleSheet("QPushButton { background:#20876f; color:white; font-weight:700; border-radius:6px; }")
            self.reset_button = QPushButton("Сброс")
            self.reset_button.setMinimumHeight(42)
            buttons.addWidget(self.toggle_button)
            buttons.addWidget(self.reset_button)
            watch_layout.addLayout(buttons)
            self.timer_status = QLabel("Нажмите ВКЛ, чтобы начать движение и отсчет. У фотодатчика остановите секундомер вручную.")
            self.timer_status.setWordWrap(True)
            self.timer_status.setStyleSheet("color:#53677f")
            watch_layout.addWidget(self.timer_status)
            panel.addWidget(stopwatch)

            repeat_row = QHBoxLayout()
            self.repeat_label = QLabel("Повтор: 1 из 3")
            self.next_button = QPushButton("Следующее измерение")
            repeat_row.addWidget(self.repeat_label)
            repeat_row.addWidget(self.next_button)
            panel.addLayout(repeat_row)

            guidance = QGroupBox("Что записать в отчет")
            guide_layout = QVBoxLayout(guidance)
            self.current_reading = QLabel("H = 20 см   •   m = 20 г")
            self.current_reading.setStyleSheet("font-weight:700; color:#213c5a")
            self.status_message = QLabel("Снимите три показания времени для каждого набора условий. Приложение не сохраняет результаты.")
            self.status_message.setWordWrap(True)
            guide_layout.addWidget(self.current_reading)
            guide_layout.addWidget(self.status_message)
            panel.addWidget(guidance)
            panel.addStretch(1)

            self.machine = MachineView()
            content.addWidget(self.machine, 1)

            self.mode.currentIndexChanged.connect(self._update_conditions)
            self.mass_spin.valueChanged.connect(self._update_conditions)
            self.distance_spin.valueChanged.connect(self._update_conditions)
            self.overload_combo.currentIndexChanged.connect(self._update_conditions)
            self.toggle_button.clicked.connect(self._toggle_timer)
            self.reset_button.clicked.connect(self._reset_timer)
            self.next_button.clicked.connect(self._next_measurement)
            self._update_conditions()

        def _update_conditions(self, *_):
            phase_two = self.mode.currentIndex() == 1
            setup_enabled = not self.run_locked
            self.mode.setEnabled(setup_enabled)
            self.distance_spin.setEnabled(not phase_two and setup_enabled)
            self.overload_combo.setEnabled(setup_enabled)
            self.mass_spin.setEnabled(setup_enabled)
            if phase_two:
                self.distance_cm = PHASE_TWO_HEIGHT_CM
                self.distance_spin.blockSignals(True)
                self.distance_spin.setValue(PHASE_TWO_HEIGHT_CM)
                self.distance_spin.blockSignals(False)
            else:
                self.distance_cm = self.distance_spin.value()
            self.mass_each_g = self.mass_spin.value()
            self.overload_g = (self.overload_combo.currentIndex() + 1) * 10
            self.machine.set_distance_cm(self.distance_cm)
            self.current_reading.setText(
                f"H = {self.distance_cm} см   •   m = {self.overload_g} г   •   M = {self.mass_each_g} г")

        def _toggle_timer(self):
            if self.timer_running:
                self._stopwatch_off()
                return
            if self.run_locked:
                return
            self._update_conditions()
            self.trial = Trial(self.mass_each_g / 1000.0,
                               self.overload_g / 1000.0,
                               self.distance_cm / 100.0,
                               student_random_gravity())
            self.started_at = time.perf_counter()
            self.timer_running = True
            self.motion_running = True
            self.run_locked = True
            self.toggle_button.setText("ВЫКЛ")
            self.toggle_button.setEnabled(True)
            self.toggle_button.setStyleSheet("QPushButton { background:#bd4b4b; color:white; font-weight:700; border-radius:6px; }")
            self.timer_status.setText("Система движется. Когда нижняя грань груза достигнет h₁, нажмите ВЫКЛ.")
            self.status_message.setText("Таймер не остановится сам. Запишите вручную время после нажатия ВЫКЛ.")
            self.machine.set_progress(0.0)
            self._update_conditions()
            self.clock.start()

        def _tick(self):
            if self.trial is None or (not self.timer_running and not self.motion_running):
                self.clock.stop()
                return
            elapsed = max(0.0, time.perf_counter() - self.started_at)
            if self.timer_running:
                self.timer_label.setText(f"{elapsed:05.3f} с")
            if self.motion_running:
                ideal_time = self.trial.ideal_time_s
                progress = min(1.0, elapsed / ideal_time)
                self.machine.set_progress(progress)
                if progress >= 1.0:
                    self.motion_running = False
                    if self.timer_running:
                        self.timer_status.setText("Груз достиг фотодатчика. Нажмите ВЫКЛ, чтобы остановить секундомер.")
                    else:
                        self.timer_status.setText("Груз достиг фотодатчика; секундомер остановлен ранее вручную.")
            if not self.timer_running and not self.motion_running:
                self.clock.stop()

        def _stopwatch_off(self):
            if not self.timer_running:
                return
            stopped_at = max(0.0, time.perf_counter() - self.started_at)
            self.timer_label.setText(f"{stopped_at:05.3f} с")
            self.timer_running = False
            # One manual timing per run; reset prepares the magnet and enables
            # a fresh run under the same conditions.
            self.toggle_button.setText("ВКЛ")
            self.toggle_button.setEnabled(False)
            self.toggle_button.setStyleSheet("QPushButton { background:#20876f; color:white; font-weight:700; border-radius:6px; }")
            self.timer_status.setText("Отсчет остановлен вручную. Запишите время и нажмите «Сброс».")
            self.status_message.setText("Показание осталось на дисплее. Приложение его не сохраняет.")
            if not self.motion_running:
                self.clock.stop()

        def _reset_timer(self):
            self.clock.stop()
            self.timer_running = False
            self.motion_running = False
            self.run_locked = False
            self.trial = None
            self.started_at = 0.0
            self.timer_label.setText("00.000 с")
            self.toggle_button.setText("ВКЛ")
            self.toggle_button.setEnabled(True)
            self.toggle_button.setStyleSheet("QPushButton { background:#20876f; color:white; font-weight:700; border-radius:6px; }")
            self.timer_status.setText("Секундомер обнулен. Система зафиксирована электромагнитом.")
            self.status_message.setText("Данные не сохраняются: перепишите время в свой отчет.")
            self.machine.set_progress(0.0)
            self._update_conditions()

        def _next_measurement(self):
            self._reset_timer()
            self.repeat_number = self.repeat_number % 3 + 1
            self.repeat_label.setText(f"Повтор: {self.repeat_number} из 3")
            if self.repeat_number == 1:
                self.status_message.setText("Три повтора завершены. Измените H или m по плану опыта.")
            else:
                self.status_message.setText("Подготовлено следующее повторное измерение; перепишите каждое время вручную.")

else:
    class AtwoodLabWindow:
        def __init__(self):
            raise RuntimeError("Для интерфейса установите PyQt6 или PyQt5: python -m pip install PyQt6")


def main() -> int:
    # IDLE runs user code inside its own Tk event loop. Running Qt's event loop
    # in that same process can make the window disappear when IDLE restarts its
    # shell, so hand the GUI off to an ordinary Python process when F5 is used.
    idle_is_running = any(name == "idlelib" or name.startswith("idlelib.")
                          for name in sys.modules)
    standalone_child = os.environ.get("ATWOOD_LAB_STANDALONE") == "1"
    if idle_is_running and not standalone_child and os.name == "nt":
        child_env = os.environ.copy()
        child_env["ATWOOD_LAB_STANDALONE"] = "1"
        script_path = os.path.abspath(__file__)
        try:
            subprocess.Popen(
                [sys.executable, script_path],
                cwd=os.path.dirname(script_path),
                env=child_env,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        except OSError as exc:
            print(f"Не удалось запустить отдельный процесс PyQt: {exc}", file=sys.stderr)
            return 1
        return 0

    if not QT_AVAILABLE:
        print("Не найдена библиотека PyQt6/PyQt5. Установите PyQt6 командой: python -m pip install PyQt6", file=sys.stderr)
        return 1
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AtwoodLabWindow()
    window.show()
    return app.exec() if hasattr(app, "exec") else app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
