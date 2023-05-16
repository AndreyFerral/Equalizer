import sys, os
import numpy as np
import pyqtgraph as pg
import matplotlib.pyplot as plt
from scipy.io import wavfile
from PyQt5 import QtWidgets, QtCore, QtGui, QtMultimedia

class Window(QtWidgets.QWidget):
    freq_split, fft_split = [], []
    audio = 'sample-105s.wav'
    update_timer = 500

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Эквалайзер")
        self.setFont(QtGui.QFont('Arial', 12))
        max_x, max_y = 500, 400
        self.resize(max_x, max_y)

        # Первый горизонтальный layout
        self.button_play = QtWidgets.QPushButton("Пуск")
        self.button_graph = QtWidgets.QPushButton("График")
        self.label_volume = QtWidgets.QLabel("Громкость")
        self.label_volume.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.slider_volume = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, self)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(30)
        self.slider_volume.setTickPosition(QtWidgets.QSlider.TickPosition.TicksAbove)

        self.first_hlayout = QtWidgets.QHBoxLayout()
        self.first_hlayout.addWidget(self.button_play)
        self.first_hlayout.addWidget(self.button_graph)
        self.first_hlayout.addWidget(self.label_volume)
        self.first_hlayout.addWidget(self.slider_volume)

        # Второй горизонтальный layout
        self.cur_time = QtWidgets.QLabel("0:00")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal, enabled=False)
        self.end_time = QtWidgets.QLabel("0:01")
        self.second_hlayout = QtWidgets.QHBoxLayout()
        self.second_hlayout.addWidget(self.cur_time)
        self.second_hlayout.addWidget(self.slider)
        self.second_hlayout.addWidget(self.end_time)

        # layout для отображения графика
        self.graph_widget = pg.PlotWidget()
        self.graph_widget.setLabel('bottom', 'Частота (Khz)')
        self.graph_widget.setLabel('left', 'Мощность (dB)')
        self.widget_layout = QtWidgets.QVBoxLayout()
        self.widget_layout.addWidget(self.graph_widget)

        # Отображение созданных layout
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addLayout(self.first_hlayout)
        self.main_layout.addLayout(self.second_hlayout)
        self.main_layout.addLayout(self.widget_layout)

        # Настравиваем проигрыватель музыки
        self.player = QtMultimedia.QMediaPlayer()
        self.player.setVolume(self.slider_volume.value())

        # Настраиваем таймер, по которому обновляется график
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.update_timer)
        self.timer.timeout.connect(self.update_plot_data)

        # Назначаем функции по нажатию, слушателей
        self.slider_volume.valueChanged.connect(self.update_volume)
        self.player.positionChanged.connect(self.position_changed)
        self.player.durationChanged.connect(self.duration_changed)
        self.button_play.clicked.connect(self.play_clicked)
        self.button_graph.clicked.connect(self.graph_clicked)

    def play_clicked(self):
        # Первый запуск аудиозаписи
        if self.player.state() == 0:
            self.freq_split, self.fft_split = self.get_fft()
            url = QtCore.QUrl.fromLocalFile(os.path.join(os.getcwd(), self.audio))
            self.player.setMedia(QtMultimedia.QMediaContent(url))
            # Запускаем обновление графика
            self.timer.start()
        # Обработка пуска и паузы музыки
        if self.player.state() == 1:
            self.timer.stop()
            self.player.pause()
            self.button_play.setText("Пуск")
        else:
            self.player.play()
            self.timer.start()
            self.button_play.setText("Пауза")

    def graph_clicked(self):
        scale_x = np.concatenate(self.freq_split)/1000
        scale_y = 10 * np.log10 (np.concatenate(self.fft_split))
        plt.plot(scale_x, scale_y, color='Grey')
        plt.xlabel('Частота (Khz)')
        plt.ylabel('Мощность (dB)')
        plt.show()

    def update_volume(self, value):
        self.player.setVolume(value)

    def position_changed(self, position):
        # Меняем текущее время для отображения
        self.slider.setValue(position)
        m, s = self.get_min_sec(position)
        # Отображаем текущее время 
        if s < 10: s = '0' + str(s)
        self.cur_time.setText(f'{m}:{s}')
        # Когда песня закончится
        if position == self.player.duration():
            self.timer.stop()
            self.slider.setValue(0)
            self.cur_time.setText("0:00")
            self.button_play.setText("Пуск")

    def duration_changed(self, duration):
        # Задаем длину песни
        m, s = self.get_min_sec(duration)
        self.slider.setRange(0, duration)
        self.end_time.setText(f'{m}:{s}')

    def get_min_sec(self, duration):
        return duration // 1000 // 60, duration // 1000 % 60
    
    def update_plot_data(self):
        # Обновляем плеер, передаем миллисекунды
        self.update_graph(self.player.position())

    def update_graph(self, ms):
        # Конвертируем миллисекунды
        i = int(ms/self.update_timer)
        # Отображаем график
        self.graph_widget.clear()
        self.graph_widget.plot(self.freq_split[i]/1000, 10 * np.log10 (self.fft_split[i]))

    def get_fft(self):
        sampling_freq, sound = wavfile.read(self.audio)
        duration = sound.shape[0] / sampling_freq

        # Преобразуем значения аудиоданных к диапазону от -1 до 1
        sound = sound / (2. ** 15)
        # Если два канала, выбираем только один канал
        one_channel = sound[:, 0]

        # Получаем длину массива аудиоданных
        sound_ength = len(sound)
        # Получаем массив частот из амплитуд и времени с помощью БПФ
        fft_array = np.fft.fft(one_channel)
        num_unique_points = np.ceil((sound_ength + 1) / 2.0)
        fft_array = fft_array[0:int(num_unique_points)]

        # БПФ содержит как величину, так и фазу. Получаем только величину с помощью модуля
        fft_array = abs(fft_array)
        # Масштабируем массив БПФ длиной выборки
        fft_array = fft_array / float(sound_ength)
        # Возводим в квадрат, чтобы получить только положительные частоты
        fft_array = fft_array ** 2

        # Нечетное число точек в БПФ
        if sound_ength % 2 > 0: 
            fft_array[1:len(fft_array)] = fft_array[1:len(fft_array)] * 2
        # Четное число точек в БПФ
        else: fft_array[1:len(fft_array) - 1] = fft_array[1:len(fft_array) - 1] * 2

        freq_array = np.arange(0, num_unique_points, 1.0) * (sampling_freq / sound_ength)

        # Разделяем на ровные части полученный график
        count = 1000 / self.update_timer
        freq_split = np.array_split(freq_array, duration * count)
        fft_split = np.array_split(fft_array, duration * count)
        return freq_split, fft_split

def main():
    app = QtWidgets.QApplication(sys.argv)  # новый экземпляр QApplication
    window = Window()  # создаём объект класса ExampleApp
    window.show()  # показываем окно
    app.exec_()  # запускаем приложение

# Если файл запущен напрямую
if __name__ == '__main__':
    main()