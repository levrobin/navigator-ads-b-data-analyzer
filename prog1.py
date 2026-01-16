import numpy as np
import pyModeS as pms
from datetime import datetime, timezone
import argparse
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import Button

MAX_MESSAGE_LENGTH = 32
# DEFAULT_FILE = "2025-12-29.1767077337.410148389.t4433" # файл со старым форматом данных
DEFAULT_FILE = "2025-12-29.1766986424.606828104.t4433" # файл с новым форматом с длинными и короткими сообщениями

# словарь для преобразования режимов автопилота в понятные сокращения
MODE_MAP = {
    'U': 'AP',      # autopilot on
    '/': 'ALT',     # altitude hold
    'M': 'VNAV',    # vertical navigation
    'F': 'LNAV',    # lateral navigation
    'P': 'APP',     # approach mode
    'T': 'TCAS',    # tcas ra active
    'C': 'HDG'      # selected heading
}

# парсинг одной строки из файла с данными
def parse_ads_b_line(line):
    parts = line.strip().split()
    if len(parts) < 2:
        return None
    try:
        timestamp = np.float64(parts[0])
    except ValueError:
        return None
    
    # определение нахождения hex данных
    if len(parts) >= 3 and parts[1] in ['DF', 'UF']: # если есть поле df/uf
        hex_parts = parts[2:]
    else:
        hex_parts = parts[1:]
    
    message_spaced = ' '.join(hex_parts).upper().strip()
    message_str = message_spaced.replace(" ", "")
    
    if len(message_str) == 0 or not all(c in "0123456789ABCDEF" for c in message_str):
        return None
    
    return timestamp, message_spaced, message_str

# функция конвертирует unix timestamp в объект datetime
def timestamp_to_utc(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

# функция форматирует время, сохраняя наносекунды для точности
def format_timestamp_with_nanoseconds(ts):
    # форматируем основную часть времени (до секунд)
    main_dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    main_dt_str = main_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # получаем дробную часть времени (наносекунды) как строку
    ts_str = f"{ts:.9f}"
    nanoseconds_str = ts_str.split('.')[1]
    
    # соединяем обе части
    return f"{main_dt_str}.{nanoseconds_str}"

# извлечение барометрической высоты из сообщения
def get_altitude(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение о положении (тип 9-18)
        tc = pms.adsb.typecode(msg_str)
        if 9 <= tc <= 18:
            return pms.adsb.altitude(msg_str)
        return None
    except:
        return None

# извлечение скорости из сообщения
def get_velocity(msg_str):
    try:
        # это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение о скорости (тип 19)
        tc = pms.adsb.typecode(msg_str)
        if tc == 19:
            result = pms.adsb.velocity(msg_str)
            if result and result[0] is not None:
                return result[0]
        return None
    except:
        return None

# функция извлекает курс из сообщения
def get_course(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # также проверяем, что это сообщение о скорости (тип 19)
        tc = pms.adsb.typecode(msg_str)
        if tc == 19:
            _, heading, _, _ = pms.adsb.velocity(msg_str)
            return heading
        return None
    except:
        return None

# функция извлекает выбранную на автопилоте высоту и режимы
def get_selected_altitude(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение о статусе (тип 29)
        tc = pms.adsb.typecode(msg_str)
        if tc != 29: return None
        sel_alt_info = pms.adsb.selected_altitude(msg_str)
        if sel_alt_info is None: return None
        selected_alt, raw_modes = sel_alt_info
        if selected_alt is not None and -2000 <= selected_alt <= 50000:
            # переводим режимы в понятные сокращения
            processed_modes = {MODE_MAP.get(m, m) for m in raw_modes}
            return selected_alt, processed_modes
        return None
    except Exception as e:
        return None

# получение разности высот
def get_altitude_difference(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение о скорости (тип 19)
        tc = pms.adsb.typecode(msg_str)
        if tc != 19:
            return None
        
        altitude_diff = pms.adsb.altitude_diff(msg_str)
        if altitude_diff is not None and -2500 <= altitude_diff <= 2500:
            return altitude_diff
        
        return None
    except Exception as e:
        return None

# получение барокоррекции
def get_baro_correction(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение о статусе (тип 29)
        tc = pms.adsb.typecode(msg_str)
        if tc != 29:
            return None
        
        baro_setting = pms.adsb.baro_pressure_setting(msg_str)
        
        if baro_setting is not None:
            # разумные пределы для атмосферного давления
            if 800 <= baro_setting <= 1100:
                return baro_setting
                
        return None
        
    except Exception as e:
        return None

# функция извлекает позывной (callsign)
def get_callsign(msg_str):
    try:
        # проверяем, что это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: return None
        # проверяем, что это сообщение идентификации (тип 1-4)
        tc = pms.adsb.typecode(msg_str)
        if 1 <= tc <= 4:
            callsign = pms.adsb.callsign(msg_str)
            if not callsign: return None
            # очищаем позывной от лишних символов
            return ''.join(c for c in callsign if c.isalnum())
        return None
    except:
        return None

# класс для создания и управления окном с графиками
class IcaoGraphs:
    def __init__(self, alt_dict, spd_dict, pos_dict, course_dict, adsb_icao_list, icao_callsigns, icao_sel_alt, icao_alt_diff, icao_baro_correction):
        # все icao, по которым есть какие-либо данные для отображения
        icao_with_data = set(alt_dict.keys()) | set(spd_dict.keys()) | set(pos_dict.keys()) | set(course_dict.keys())
        self.icao_list = sorted(list(icao_with_data.intersection(adsb_icao_list)))
        
        self.has_plot_data = False

        # если нет данных, выводим сообщение и выходим
        if not self.icao_list:
            print("Нет данных для построения графиков")
            return

        # сохраняем все словари с данными в атрибутах класса для доступа из других методов
        self.alt_dict = alt_dict
        self.spd_dict = spd_dict
        self.pos_dict = pos_dict
        self.course_dict = course_dict
        self.icao_callsigns = icao_callsigns
        self.sel_alt_dict = icao_sel_alt if icao_sel_alt else {}
        self.alt_diff_dict = icao_alt_diff if icao_alt_diff else {}
        self.baro_correction_dict = icao_baro_correction if icao_baro_correction else {} 
        self.icao_index = 0
        
        # список доступных режимов (типов графиков)
        self.plot_modes = ['altitude', 'speed', 'altitude_speed_combined', 
                           'latitude', 'course', 'track', 'altitude_diff', 
                           'baro_correction', 'alt_msg_intervals', 
                           'spd_msg_intervals', 'course_msg_intervals',
                           'sel_alt_msg_intervals', 'alt_diff_msg_intervals',
                           'baro_corr_msg_intervals']
        self.plot_mode_idx = 0
        self.ylims = {mode: {} for mode in self.plot_modes}

        # пределы осей y по умолчанию для адекватного отображения графиков при первом открытии
        self.default_ylims = {
            'altitude': (-1200, 40000), 
            'speed': (0, 500), 
            'course': (0, 360), 
            'latitude': 'auto',
            'altitude_speed_combined': 'auto',
            'altitude_diff': (-2000, 2000),
            'baro_correction': (950, 1050)
        }

        # окно и основная области для рисования (осей)
        self.fig, self.ax = plt.subplots(figsize=(12, 7))
        self.fig.canvas.manager.set_window_title('Графики бортов')
        plt.subplots_adjust(bottom=0.25) # нижнее пространство для кнопок
        
        # атрибут для хранения ссылки на вторую (правую) ось y
        self.ax2 = None

        # области для кнопок
        ax_prev_icao = plt.axes([0.05, 0.05, 0.2, 0.075])
        ax_next_icao = plt.axes([0.28, 0.05, 0.2, 0.075])
        ax_prev_mode = plt.axes([0.52, 0.05, 0.2, 0.075])
        ax_next_mode = plt.axes([0.75, 0.05, 0.2, 0.075])
        
        # создание и настройка кнопок
        self.btn_prev_icao = Button(ax_prev_icao, '<- Пред. борт', color='lightblue', hovercolor='skyblue')
        self.btn_next_icao = Button(ax_next_icao, 'След. борт ->', color='lightblue', hovercolor='skyblue')
        self.btn_prev_mode = Button(ax_prev_mode, '<- Пред. график', color='lightgreen', hovercolor='limegreen')
        self.btn_next_mode = Button(ax_next_mode, 'След. график ->', color='lightgreen', hovercolor='limegreen')
        
        # привязка функций-обработчиков к кнопкам
        self.btn_prev_icao.on_clicked(self.prev_icao)
        self.btn_next_icao.on_clicked(self.next_icao)
        self.btn_prev_mode.on_clicked(self.prev_mode)
        self.btn_next_mode.on_clicked(self.next_mode)
        
        # подключение обработчиков событий клавиатуры и колеса мыши к окну
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        
        # первоначальная отрисовка графика
        self.plot_current()
        # запуск окна
        plt.show()

    # отрисовка текущего графика, вызывается при любом изменении
    def plot_current(self):
        # удаляем вторую ось y, если она осталась от предыдущего графика
        if self.ax2:
            self.ax2.remove()
            self.ax2 = None
        # полностью очищаем основную область рисования
        self.ax.clear()
        
        # принудительно сбрасываем соотношение сторон к стандартному ('auto')
        self.ax.set_aspect('auto')

        # если нет данных, выводим сообщение и выходим
        if not self.icao_list:
            self.ax.text(0.5, 0.5, "Нет бортов с данными для отображения", ha='center', va='center')
            self.fig.canvas.draw_idle()
            return

        # получаем текущий выбранный icao и режим (тип графика)
        icao = self.icao_list[self.icao_index]
        mode = self.plot_modes[self.plot_mode_idx]
        
        # формирование заголовка с позывным и активными режимами автопилота
        callsign = self.icao_callsigns.get(icao, "N/A")
        modes_key = f"{icao}_modes"
        active_modes = self.icao_callsigns.get(modes_key, set())
        mode_str = f" ({', '.join(sorted(active_modes))})" if active_modes else ""
        display_id = f"{callsign} ({icao}){mode_str}" if callsign != "N/A" else f"{icao}{mode_str}"
        
        # инициализация переменных для подписей
        data = None
        label = ""
        title = ""

        # блок отрисовки графика высоты 
        if mode == 'altitude':
            # получаем данные о высоте для текущего icao
            data = self.alt_dict.get(icao)
            sel_data = self.sel_alt_dict.get(icao)
            title, label = f"Высота: {display_id}", "Высота (футы)"
            # если данных нет, выводим сообщение
            if not data and not sel_data:
                self.ax.text(0.5, 0.5, f"Нет данных о высоте для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                # отрисовка барометрической высоты
                if data:
                    times = [timestamp_to_utc(t) for t, v in sorted(data)]
                    values = [v for t, v in sorted(data)]
                    self.ax.plot(times, values, 'o-', markersize=3, label='Барометрическая высота', color='blue')
                # отрисовка выбранной высоты (ступенчатый график)
                if sel_data:
                    times = [timestamp_to_utc(t) for t, v in sorted(sel_data)]
                    values = [v for t, v in sorted(sel_data)]
                    self.ax.step(times, values, where='post', label='Выбранная высота', color='red', linestyle='--')
                self.has_plot_data = True
        
        # блок отрисовки графика скорости 
        elif mode == 'speed':
            data = self.spd_dict.get(icao)
            title, label = f"Скорость: {display_id}", "Скорость (узлы)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о скорости для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Скорость', color='green')
                self.has_plot_data = True

        # блок отрисовки комбинированного графика (высота и скорость)
        elif mode == 'altitude_speed_combined':
            title = f"Высота и скорость: {display_id}"
            alt_data = self.alt_dict.get(icao)
            spd_data = self.spd_dict.get(icao)
            
            if not alt_data and not spd_data:
                self.ax.text(0.5, 0.5, f"Нет данных о высоте и скорости для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                # настройка левой оси y для высоты
                self.ax.set_ylabel("Высота (футы)", color='blue')
                self.ax.tick_params(axis='y', labelcolor='blue')
                
                # создание и настройка правой оси y для скорости
                self.ax2 = self.ax.twinx() # создаём и сохраняем вторую ось
                self.ax2.set_ylabel("Скорость (узлы)", color='green')
                self.ax2.tick_params(axis='y', labelcolor='green')

                # отрисовка данных и сбор информации для общей легенды
                lines1, labels1, lines2, labels2 = [], [], [], []
                if alt_data:
                    alt_times = [timestamp_to_utc(t) for t, v in sorted(alt_data)]
                    alt_values = [v for t, v in sorted(alt_data)]
                    line, = self.ax.plot(alt_times, alt_values, 'o-', markersize=3, label='Высота', color='blue')
                    lines1.append(line)
                    labels1.append('Высота')
                if spd_data:
                    spd_times = [timestamp_to_utc(t) for t, v in sorted(spd_data)]
                    spd_values = [v for t, v in sorted(spd_data)]
                    line, = self.ax2.plot(spd_times, spd_values, 'o-', markersize=3, label='Скорость', color='green')
                    lines2.append(line)
                    labels2.append('Скорость')
                
                # создание общей легенды для обеих осей
                self.ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

        # блок отрисовки графика широты 
        elif mode == 'latitude':
            data = self.pos_dict.get(icao)
            title, label = f"Координаты: {display_id}", "Широта (°)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о координатах для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, lat, lon in data]
                lats = [lat for t, lat, lon in data]
                self.ax.plot(times, lats, 'o-', markersize=3, label='Широта', color='orange')
                self.has_plot_data = True

        # блок отрисовки графика курса 
        elif mode == 'course':
            data = self.course_dict.get(icao)
            title, label = f"Курс: {display_id}", "Курс (°)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о курсе для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Курс', color='purple')
                self.has_plot_data = True

        # блок отрисовки трека полёта (карты)
        elif mode == 'track':
            data = self.pos_dict.get(icao)
            title = f"Схема трека полёта: {display_id}"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о координатах для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                lons = [lon for t, lat, lon in data]
                lats = [lat for t, lat, lon in data]
                self.ax.plot(lons, lats, 'o', markersize=2, label='Трек')

        # блок отрисовки графика разницы высот 
        elif mode == 'altitude_diff':
            data = self.alt_diff_dict.get(icao)
            title, label = f"Разница высот (DIF_FROM_BARO_ALT): {display_id}", "Разница высот (футы)"
            
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о разнице высот для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Разница высот (выбранная - барометрическая)', color='red')
                self.ax.axhline(y=0, color='gray', linestyle='--', alpha=0.7, label='Нулевая разница')
                self.has_plot_data = True

        # блок отрисовки графика барокоррекции 
        elif mode == 'baro_correction':
            data = self.baro_correction_dict.get(icao)
            title, label = f"Барокоррекция: {display_id}", "Давление (гПа)"
            
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о барокоррекции для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Барокоррекция', color='brown')
                self.ax.axhline(y=1013.25, color='green', linestyle='--', alpha=0.7, label='Стандартное давление (1013.25 гПа)')
                self.has_plot_data = True

        # блоки отрисовки гистограммы распределения интервалов по типам сквиттеров
        elif mode == 'alt_msg_intervals':
            # данные для гистограммы
            data_to_plot = []
            
            # проверка каждого типа данных по отдельности
            if icao in self.alt_dict and len(self.alt_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.alt_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, "Высота", 'blue'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                # параметры для гистограммы
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8  # количество интервалов внутри диапазона

                # гистрограмма с обрезкой крайних значений
                for intervals, label, color in data_to_plot:
                    # обрезка интервалов в диапазоне center +/- dev
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    # границы интервалов равномерно внутри диапазона
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)
                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()
                self.has_plot_data = True

                self.fig.canvas.draw_idle()

        elif mode == 'spd_msg_intervals':
            data_to_plot = []
            
            if icao in self.spd_dict and len(self.spd_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.spd_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, f"Скорость", 'green'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8 # количество бинов внутри диапазона

                for intervals, label, color in data_to_plot:
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)

                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                # настройки графика
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()
                self.has_plot_data = True
                self.fig.canvas.draw_idle()

        elif mode == 'course_msg_intervals':
            # данные для гистограмм
            data_to_plot = []
            if icao in self.course_dict and len(self.course_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.course_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, "Курс", 'purple'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8 # количество бинов внутри диапазона

                # гистрограммы
                for intervals, label, color in data_to_plot:
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)
                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                # настройки графика
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()
                self.has_plot_data = True

                self.fig.canvas.draw_idle()

        elif mode == 'sel_alt_msg_intervals':
            # данные для гистограмм
            data_to_plot = []

            if icao in self.sel_alt_dict and len(self.sel_alt_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.sel_alt_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, "Выбр. высота", 'red'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8 # количество бинов внутри диапазона

                # гистрограммы
                for intervals, label, color in data_to_plot:
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)
                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                # настройки графика
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()
                
                self.has_plot_data = True

                self.fig.canvas.draw_idle()

        elif mode == 'alt_diff_msg_intervals':
            # данные для гистограмм
            data_to_plot = []

            if icao in self.alt_diff_dict and len(self.alt_diff_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.alt_diff_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, "Разн. высот", 'orange'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8 # количество бинов внутри диапазона

                # гистрограммы
                for intervals, label, color in data_to_plot:
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)
                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                # настройки графика
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()

                self.has_plot_data = True

                self.fig.canvas.draw_idle()

        elif mode == 'baro_corr_msg_intervals':
            # данные для гистограммы
            data_to_plot = []

            if icao in self.baro_correction_dict and len(self.baro_correction_dict[icao]) > 1:
                timestamps = np.unique([t for t, _ in self.baro_correction_dict[icao]])
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                if len(intervals) > 0:
                    data_to_plot.append((intervals, "Барокорр.", 'brown'))

            if not data_to_plot:
                self.ax.text(0.5, 0.5, f"Нет данных для {icao}", ha='center', va='center')
                self.has_plot_data = False
                
            else:
                center = 500  # типичный период, мс
                dev = 100     # разброс, мс
                num_bins = 8 # количество бинов внутри диапазона

                # гистрограммы
                for intervals, label, color in data_to_plot:
                    clipped_intervals = np.clip(intervals, center - dev, center + dev)
                    bin_edges = np.linspace(center - dev, center + dev, num_bins + 1)
                    self.ax.hist(clipped_intervals, bins=bin_edges, alpha=0.6, 
                                label=f"{label} ({len(intervals)} раз)", 
                                color=color, edgecolor='black', density=False)
                    
                # настройки графика
                callsign = self.icao_callsigns.get(icao, "N/A")
                display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao
                self.ax.set_xlabel('Интервал между сообщениями (мс)')
                self.ax.set_ylabel('Частота встречаемости сообщения')
                self.ax.set_title(f'Распределение интервалов: {display_id}')
                self.ax.legend()

                self.has_plot_data = True

                self.fig.canvas.draw_idle()


        # специльная настройка для гистограммы
        if mode.endswith('_msg_intervals'):
            self.fig.canvas.draw_idle()
            return

        # установка общих элементов: заголовок и сетка
        self.ax.set_title(title)
        self.ax.grid(True, linestyle='--', alpha=0.7)

        # специальная настройка для графика трека (карты)
        if mode == 'track':
            # делаем оси равномасштабными, чтобы карта не искажалась
            self.ax.set_aspect('equal', adjustable='datalim')
            self.ax.set_xlabel("Долгота (°)")
            self.ax.set_ylabel("Широта (°)")
        # общие настройки для всех остальных (временных) графиков
        else:
            self.ax.set_xlabel("Время (UTC)")
            # форматируем подписи на оси x для отображения времени
            self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S.%f'))
            # автоматически поворачиваем подписи, чтобы они не накладывались друг на друга
            self.fig.autofmt_xdate(rotation=30)
            if mode != 'altitude_speed_combined':
                self.ax.set_ylabel(label)
        
        # отображение легенды, если она есть
        if self.ax.get_legend_handles_labels()[0] and mode != 'altitude_speed_combined':
            self.ax.legend()

        # применение сохранённого масштаба (кроме комбинированного графика)
        if mode != 'altitude_speed_combined':
            ylim = self.ylims[mode].get(icao, self.default_ylims.get(mode))
            if ylim and ylim != 'auto':
                self.ax.set_ylim(ylim)

        # перерисовка окна с обновлённым графиком
        self.fig.canvas.draw_idle()

    # функция-обработчик для масштабирования колесом мыши
    def on_scroll(self, event):
        # если нет данных для борта
        if not self.has_plot_data:
            return
        # если курсор не над осями, ничего не делаем
        if event.inaxes != self.ax: return

        base_scale = 1.2
        mode = self.plot_modes[self.plot_mode_idx]
        
        # определяем направление прокрутки
        if event.button == 'up':
            scale_factor = 1 / base_scale # приближение
        elif event.button == 'down':
            scale_factor = base_scale # отдаление
        else:
            return

        # специальная логика для 2d-масштабирования карты
        if mode == 'track':
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            xdata = event.xdata
            ydata = event.ydata
            if xdata is None or ydata is None: return

            # вычисляем новые пределы по осям x и y
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            rel_x = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rel_y = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])

            # устанавливаем новые пределы, центрируясь на курсоре
            self.ax.set_xlim([xdata - new_width * (1 - rel_x), xdata + new_width * rel_x])
            self.ax.set_ylim([ydata - new_height * (1 - rel_y), ydata + new_height * rel_y])
        
        # стандартная логика для 1d-масштабирования по оси y
        else:
            cur_ylim = self.ax.get_ylim()
            ydata = event.ydata if event.ydata is not None else (cur_ylim[0] + cur_ylim[1]) / 2
            
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor
            rel_y = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
            
            # устанавливаем новые пределы для оси y
            self.ax.set_ylim([ydata - new_height * (1-rel_y), ydata + new_height * rel_y])

        # обновляем график
        self.fig.canvas.draw_idle()

    # функция для переключения на следующий борт
    def next_icao(self, event=None):
        if not self.icao_list: return
        self.icao_index = (self.icao_index + 1) % len(self.icao_list)
        self.plot_current()

    # функция для переключения на предыдущий борт
    def prev_icao(self, event=None):
        if not self.icao_list: return
        self.icao_index = (self.icao_index - 1 + len(self.icao_list)) % len(self.icao_list)
        self.plot_current()

    # функция для переключения на следующий тип графика
    def next_mode(self, event=None):
        if not self.icao_list: return
        self.plot_mode_idx = (self.plot_mode_idx + 1) % len(self.plot_modes)
        self.plot_current()

    # функция для переключения на предыдущий тип графика
    def prev_mode(self, event=None):
        if not self.icao_list: return
        self.plot_mode_idx = (self.plot_mode_idx - 1 + len(self.plot_modes)) % len(self.plot_modes)
        self.plot_current()

    # функция-обработчик для горячих клавиш
    def on_key(self, event):
        if event.key == 'right': self.next_icao()
        elif event.key == 'left': self.prev_icao()
        elif event.key == 'up': self.next_mode()
        elif event.key == 'down': self.prev_mode()

if __name__ == '__main__':
    # парсинг аргументов из командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Имя входного файла", default=DEFAULT_FILE)
    parser.add_argument("-a", "--aircraft", help="ICAO адрес конкретного борта")
    args = parser.parse_args()

    file_path = args.file
    target_icao = args.aircraft.upper() if args.aircraft else None

    # создаём пустые словари для сбора данных
    icao_times = {}
    icao_altitude = {}
    icao_speed = {}
    icao_callsigns = {}
    icao_selected_altitude = {}
    icao_altitude_difference = {}
    icao_baro_correction = {}
    icao_has_selected_alt = {}
    adsb_icao_list = set()
    icao_positions = {}
    icao_courses = {}
    cpr_messages = {}

    try:
        # основной цикл чтения файла
        with open(file_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                # пропуск пустых строк
                if not line.strip(): 
                    continue 
                parsed = parse_ads_b_line(line)
                if parsed is None: 
                    continue
                timestamp, message_spaced, message_str = parsed

                try:
                    df = pms.df(message_str)
                    aa = pms.icao(message_str)
                # пропуск повреждённых сообщений
                except Exception as e:
                    continue 

                if df not in [17, 18]: continue # нас интересуют только ads-b сообщения
                if target_icao and aa != target_icao: continue # если задан борт, фильтруем

                adsb_icao_list.add(aa)

                # обновляем время первого/последнего сообщения для борта
                if aa not in icao_times:
                    icao_times[aa] = {"first": timestamp, "last": timestamp}
                else:
                    icao_times[aa]["last"] = timestamp
                
                try:
                    # узнаём тип сообщения и вызываем нужные функции для извлечения данных
                    tc = pms.adsb.typecode(message_str)
                    # сообщения с высотой и координатами (tc 9-18)
                    if 9 <= tc <= 18:
                        alt = get_altitude(message_str)
                        if alt is not None and -1000 <= alt <= 50000:
                            icao_altitude.setdefault(aa, []).append((timestamp, alt))
                        
                        # логика декодирования координат из двух cpr сообщений
                        cpr_messages.setdefault(aa, [None, None])
                        oe_flag = pms.adsb.oe_flag(message_str)
                        cpr_messages[aa][oe_flag] = (message_str, timestamp)
                        # если получены оба сообщения (чётное и нечётное) в пределах 10 секунд
                        if all(cpr_messages[aa]):
                            msg0, t0 = cpr_messages[aa][0]
                            msg1, t1 = cpr_messages[aa][1]
                            if abs(t0 - t1) < 10:
                                pos = pms.adsb.position(msg0, msg1, t0, t1)
                                if pos:
                                    icao_positions.setdefault(aa, []).append((timestamp, pos[0], pos[1]))
                                # сбрасываем сообщения для следующей пары
                                cpr_messages[aa] = [None, None]
                    
                    # сообщения со скоростью и курсом (tc 19)
                    elif tc == 19:
                        gs = get_velocity(message_str)
                        if gs is not None and 0 <= gs <= 1000:
                            icao_speed.setdefault(aa, []).append((timestamp, gs))
                        
                        course = get_course(message_str)
                        if course is not None:
                            icao_courses.setdefault(aa, []).append((timestamp, course))
                        
                        # разница высот
                        alt_diff = get_altitude_difference(message_str)
                        if alt_diff is not None:
                            icao_altitude_difference.setdefault(aa, []).append((timestamp, alt_diff))

                    # сообщения с позывным (tc 1-4)
                    elif 1 <= tc <= 4:
                        cs = get_callsign(message_str)
                        if cs: icao_callsigns[aa] = cs

                    # сообщения с параметрами автопилота (tc 29)
                    elif tc == 29:
                        sel_alt = get_selected_altitude(message_str)
                        if sel_alt:
                            sel_alt_value, modes = sel_alt
                            icao_selected_altitude.setdefault(aa, []).append((timestamp, sel_alt_value))
                            icao_has_selected_alt[aa] = True
                            modes_key = f"{aa}_modes"
                            existing_modes = icao_callsigns.get(modes_key, set())
                            icao_callsigns[modes_key] = existing_modes.union(modes)
                        
                        # барокоррекция
                        baro_corr = get_baro_correction(message_str)
                        if baro_corr is not None:
                            icao_baro_correction.setdefault(aa, []).append((timestamp, baro_corr))
                            
                except Exception:
                    continue

        # итоговая сводная таблица
        print("=" * 160)
        print(" "*60 + "Сводная таблица")
        print("=" * 160)
        print(f"{'ICAO':<8} {'Номер рейса':<12} {'Первое (UTC)':<33} {'Последнее (UTC)':<33} {'Координаты':<12} {'Курс':<8} {'Выб. высота':<12} {'Разн. высот':<12} {'Барокорр.':<10}")
        print("-" * 160)

        for icao in sorted(list(adsb_icao_list)):
            if icao not in icao_times: continue
            times = icao_times[icao]
            first_utc_str = format_timestamp_with_nanoseconds(times["first"])
            last_utc_str = format_timestamp_with_nanoseconds(times["last"])
            callsign = icao_callsigns.get(icao, "N/A")
            sel_alt_flag = "Да" if icao_has_selected_alt.get(icao) else "Нет"
            coord_flag = "Да" if icao in icao_positions and icao_positions[icao] else "Нет"
            course_flag = "Да" if icao in icao_courses and icao_courses[icao] else "Нет"
            alt_diff_flag = "Да" if icao in icao_altitude_difference and icao_altitude_difference[icao] else "Нет"
            baro_corr_flag = "Да" if icao in icao_baro_correction and icao_baro_correction[icao] else "Нет"
            print(f"{icao:<8} {callsign:<12} {first_utc_str:<33} "
                  f"{last_utc_str:<33} "
                  f"{coord_flag:<12} {course_flag:<8} {sel_alt_flag:<12} {alt_diff_flag:<12} {baro_corr_flag:<10}")
            
        print(f"\nВсего бортов: {len(adsb_icao_list)}\n")

        # запуск графического интерфейса с передачей всех собранных данных
        IcaoGraphs(icao_altitude, icao_speed, icao_positions, icao_courses, adsb_icao_list, icao_callsigns, icao_selected_altitude, icao_altitude_difference, icao_baro_correction)

    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
    except Exception as e:
        print(f"Произошла критическая ошибка: {e}")