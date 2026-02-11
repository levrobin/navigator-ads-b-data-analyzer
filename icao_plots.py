import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.widgets import *
from time_formatter import timestamp_to_utc
from dict_data import *

class IcaoPlots:
    def __init__(self, alt_dict, spd_dict, pos_dict, course_dict, adsb_icao_list, icao_callsigns, 
                 icao_sel_alt, icao_alt_diff, icao_baro_correction, 
                 icao_airborne_pos_ts, icao_surface_pos_ts, icao_ident_ts,
                 icao_speed_ts, icao_status, icao_emg_ts, icao_mode_change, icao_tcas_ra, icao_target_state, 
                 icao_air_op_status, icao_surf_op_status, icao_acq_ts, icao_track_angles, icao_gs_spd_ts, icao_airspd_ts):
        
        self.icao_list = sorted(list(adsb_icao_list))
        self.has_plot_data = False

        # словари с данными
        self.alt_dict = alt_dict
        self.spd_dict = spd_dict
        self.pos_dict = pos_dict
        self.course_dict = course_dict
        self.icao_callsigns = icao_callsigns
        self.sel_alt_dict = icao_sel_alt if icao_sel_alt else {}
        self.alt_diff_dict = icao_alt_diff if icao_alt_diff else {}
        self.baro_correction_dict = icao_baro_correction if icao_baro_correction else {} 
        self.track_angle_dict = icao_track_angles if icao_track_angles else {}
        self.icao_gs_spd_ts_dict = icao_gs_spd_ts if icao_gs_spd_ts else {}
        self.icao_airspd_ts_dict = icao_airspd_ts if icao_airspd_ts else {}

        # reg 05
        self.icao_airborne_pos_ts = icao_airborne_pos_ts if icao_airborne_pos_ts else {}
        
        # reg 06
        self.icao_surface_pos_ts = icao_surface_pos_ts if icao_surface_pos_ts else {}
                
        # reg 08
        self.icao_ident_ts = icao_ident_ts if icao_ident_ts else {}

        # reg 09
        self.icao_speed_ts = icao_speed_ts if icao_speed_ts else {}

        # reg 61
        self.icao_status = icao_status if icao_status else {}
        self.icao_emg_ts = icao_emg_ts if icao_emg_ts else {}
        self.icao_mode_change = icao_mode_change if icao_mode_change else {}
        self.icao_tcas_ra = icao_tcas_ra if icao_tcas_ra else {}

        # reg 62
        self.icao_target_state = icao_target_state if icao_target_state else {}
        
        # reg 65
        self.icao_air_op_status = icao_air_op_status if icao_air_op_status else {}
        self.icao_surf_op_status = icao_surf_op_status if icao_surf_op_status else {}

        # df 11
        self.icao_df11_ts = icao_acq_ts if icao_acq_ts else {}

        self.icao_index = 0
        
        # список доступных режимов (типов графиков и гистограмм)
        self.graph_modes = ['altitude', 'speed', 'altitude_speed_combined', 
                           'latitude', 'course', 'track', 'altitude_diff', 'baro_correction',
                           'reg09_tracks', 'track_angle', 'airspd_angle']
        
        self.hist_modes = ['reg05_hist', 'reg06_1_hist', 'reg06_2_hist', 
                           'reg08_hist', 'reg09_hist', 'reg61_1_hist', 'reg61_2_hist', 'reg61_3_hist', 
                           'reg61_4_hist', 'reg62_hist', 
                           'reg65_1_hist', 'reg65_2_hist', 'df11_hist']

        self.current_mode_group = 'graphs'
        self.plot_modes = self.graph_modes
        self.plot_mode_idx = 0
        self.ylims = {mode: {} for mode in self.graph_modes}

        # пределы осей y по умолчанию для адекватного отображения графиков при первом открытии
        self.default_ylims = {
            'altitude': (-1200, 40000), 
            'speed': (0, 500), 
            'course': (0, 360), 
            'track_angle': (0, 360),
            'latitude': 'auto',
            'altitude_speed_combined': (0, 40000),
            'altitude_diff': (-2000, 2000),
            'baro_correction': (950, 1050)
        }

        # окно и основная области для рисования (осей)
        self.fig, self.ax = plt.subplots(figsize=(13, 7))
        self.fig.canvas.manager.set_window_title('Графики бортов')
        plt.subplots_adjust(left=0.25, bottom=0.25) # пространство для кнопок
        
        # атрибут для хранения ссылки на правую ось y
        self.ax2 = None

        # области для кнопок
        ax_prev_icao = plt.axes([0.05, 0.05, 0.2, 0.075])
        ax_next_icao = plt.axes([0.28, 0.05, 0.2, 0.075])
        ax_prev_mode = plt.axes([0.52, 0.05, 0.2, 0.075])
        ax_next_mode = plt.axes([0.75, 0.05, 0.2, 0.075])

        ax_radio = plt.axes([0.02, 0.60, 0.15, 0.15])
        
        # кнопки
        self.btn_prev_icao = Button(ax_prev_icao, '<- Пред. борт', color='lightblue', hovercolor='skyblue')
        self.btn_next_icao = Button(ax_next_icao, 'След. борт ->', color='lightblue', hovercolor='skyblue')
        self.btn_prev_mode = Button(ax_prev_mode, '<- Пред. график', color='lightgreen', hovercolor='limegreen')
        self.btn_next_mode = Button(ax_next_mode, 'След. график ->', color='lightgreen', hovercolor='limegreen')
        self.radio_mode = RadioButtons(ax_radio, ['Графики', 'Гистограммы'], active=0)
        self.radio_mode.on_clicked(self.on_radio_changed)

        # привязка функций-обработчиков к кнопкам
        self.btn_prev_icao.on_clicked(self.prev_icao)
        self.btn_next_icao.on_clicked(self.next_icao)
        self.btn_prev_mode.on_clicked(self.prev_mode)
        self.btn_next_mode.on_clicked(self.next_mode)
        self.radio_mode.on_clicked(self.on_radio_changed)
        
        # подключение обработчиков событий клавиатуры и колеса мыши к окну
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)
        
        # первоначальная отрисовка графика
        self.plot_current()
        # запуск окна
        plt.show()

        if not self.icao_list:
            self.ax.text(0.5, 0.5, f"Нет данных для построения графиков", ha='center', va='center')
            self.has_plot_data = False

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

        # если нет данных
        if not self.icao_list:
            self.ax.text(0.5, 0.5, "Нет бортов с данными для отображения", ha='center', va='center')
            self.fig.canvas.draw_idle()
            return
        
        # текущий выбранный icao и режим (тип графика)
        icao = self.icao_list[self.icao_index]
        mode = self.plot_modes[self.plot_mode_idx]
        
        # заголовок с позывным и активными режимами автопилота
        callsign = self.icao_callsigns.get(icao, "N/A")
        modes_key = f"{icao}_modes"
        active_modes = self.icao_callsigns.get(modes_key, set())
        mode_str = f" ({', '.join(sorted(active_modes))})" if active_modes else ""
        display_id = f"{callsign} ({icao}){mode_str}" if callsign != "N/A" else f"{icao}{mode_str}"
        
        # переменные для подписей
        data = None
        label = ""
        title = ""

        # блок отрисовки графика высоты
        if mode == 'altitude':
            # получаем данные о высоте для текущего icao
            data = self.alt_dict.get(icao, [])
            sel_data = self.sel_alt_dict.get(icao, []) 
            title, label = f"Высота: {display_id}", "Высота (футы)"
            # если данных нет, выводим сообщение
            if not data and not sel_data:
                self.ax.text(0.5, 0.5, f"Нет данных о высоте для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                # баро и GNSS высоты
                baro_times, baro_values = [], []
                gnss_times, gnss_values = [], []
                
                for t, v, alt_type in sorted(data):
                    if alt_type == 'baro':
                        baro_times.append(timestamp_to_utc(t))
                        baro_values.append(v)
                    elif alt_type == 'gnss':
                        gnss_times.append(timestamp_to_utc(t))
                        gnss_values.append(v)
                
                # отрисовка баро высоты
                if baro_times:
                    self.ax.plot(baro_times, baro_values, 'o-', markersize=3, 
                                label='Барометрическая высота', color='blue')
                
                # отрисовка GNSS высоты
                if gnss_times:
                    self.ax.plot(gnss_times, gnss_values, 's-', markersize=4, 
                                label='GNSS высота', color='cyan', alpha=0.7)
                
                # отрисовка выбранной высоты
                if sel_data:
                    times = [timestamp_to_utc(t) for t, v in sorted(sel_data)]
                    values = [v for t, v in sorted(sel_data)]
                    self.ax.step(times, values, where='post', label='Выбранная высота', 
                                color='red', linestyle='--')
                
                self.has_plot_data = True
        
        # блок отрисовки графика скорости
        elif mode == 'speed':
            data = self.spd_dict.get(icao, [])
            title, label = f"Скорость: {display_id}", "Скорость (узлы)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о скорости для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Скорость', color='green')
                self.has_plot_data = True

        # комбинированный график высоты и скорости
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
                self.ax.set_ylim(0, 40000)
                # создание и настройка правой оси y для скорости
                self.ax2 = self.ax.twinx() # создаём и сохраняем вторую ось
                self.ax2.set_ylabel("Скорость (узлы)", color='green')
                self.ax2.tick_params(axis='y', labelcolor='green')
                self.ax2.set_ylim(0, 500)

                # отрисовка данных и сбор информации для общей легенды
                lines1, labels1, lines2, labels2 = [], [], [], []
                if alt_data:
                    alt_times = []
                    alt_values = []
                    for t, v, alt_type in sorted(alt_data):
                        alt_times.append(timestamp_to_utc(t))
                        alt_values.append(v)
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

        # график широты
        elif mode == 'latitude':
            data = self.pos_dict.get(icao, [])
            title, label = f"Координаты: {display_id}", "Широта (°)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о координатах для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, lat, lon in data]
                lats = [lat for t, lat, lon in data]
                self.ax.plot(times, lats, 'o-', markersize=3, label='Широта', color='orange')
                self.has_plot_data = True

        # график курса
        elif mode == 'course':
            data = self.course_dict.get(icao, [])
            title, label = f"Курс: {display_id}", "Курс (°)"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о курсе для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                times = [timestamp_to_utc(t) for t, v in sorted(data)]
                values = [v for t, v in sorted(data)]
                self.ax.plot(times, values, 'o-', markersize=3, label='Курс', color='purple')
                self.has_plot_data = True

        # трек полёта (карта)
        elif mode == 'track':
            data = self.pos_dict.get(icao, [])
            title = f"Схема трека полёта: {display_id}"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о координатах для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                lons = [lon for t, lat, lon in data]
                lats = [lat for t, lat, lon in data]
                self.ax.plot(lons, lats, 'o', markersize=2, label='Трек')

        # график разницы высот
        elif mode == 'altitude_diff':
            data = self.alt_diff_dict.get(icao, [])
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

        # график барокоррекции
        elif mode == 'baro_correction':
            data = self.baro_correction_dict.get(icao, [])
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

        elif mode == 'reg09_tracks':
            title = f"Схема трека по TC 19: {display_id}"
            if icao not in self.icao_speed_ts or icao not in self.pos_dict:
                self.ax.text(0.5, 0.5, f"Нет данных TC 19 или координат для борта {icao}", 
                            ha='center', va='center')
                self.has_plot_data = False

            else:
                tc19_times = self.icao_speed_ts[icao]
                pos_data = self.pos_dict[icao]
                
                pos_times_dict = {}
                for t, lat, lon in pos_data:
                    rounded = round(t, 1)
                    if rounded not in pos_times_dict:
                        pos_times_dict[rounded] = (lat, lon)

                # координаты для временных меток TC 19
                tc19_coords = []
                for tc19_time in sorted(tc19_times):
                    rounded_time = round(tc19_time, 1)
                    if rounded_time in pos_times_dict:
                        lat, lon = pos_times_dict[rounded_time]
                        tc19_coords.append((lat, lon))
                
                if not tc19_coords:
                    self.ax.text(0.5, 0.5, f"Не найдено координат для сообщений TC 19 борта {icao}", 
                                ha='center', va='center')
                    self.has_plot_data = False
                else:
                    lons = [lon for lat, lon in tc19_coords]
                    lats = [lat for lat, lon in tc19_coords]
                    
                    self.ax.plot(lons, lats, 'o-', color='lime', linewidth=2, markersize=4, 
                                label=f"{display_id}")
                    
                    self.ax.set_aspect('equal', adjustable='datalim')
                    self.ax.set_xlabel("Долгота (°)")
                    self.ax.set_ylabel("Широта (°)")
                    self.ax.set_title(title)
                    self.ax.grid(True, linestyle='--', alpha=0.5)
                    self.ax.legend(fontsize=8, loc='upper left')
                    
                    self.has_plot_data = True

        elif mode == 'track_angle':
            pos_data = self.pos_dict.get(icao, [])
            gs_data  = self.icao_gs_spd_ts_dict.get(icao, [])
            title = f"Трек и линия путевого угла: {display_id}"

            if not pos_data or not gs_data:
                self.ax.text(0.5, 0.5, f"Нет данных путевого угла для борта {display_id}", ha='center')
                self.has_plot_data = False
            else:
                # полный трек
                full_lons = [lon for t, lat, lon in pos_data]
                full_lats = [lat for t, lat, lon in pos_data]
                self.ax.plot(full_lons, full_lats, '-', color='limegreen', linewidth=4, alpha=0.5, label='Полный трек')

                # словарь для поиска координат по времени
                pos_times = {round(t, 1): (lat, lon) for t, lat, lon in pos_data}
                track_line_lons = []
                track_line_lats = []

                # построение линии путевого угла
                for t, angle in sorted(gs_data):
                    rounded_t = round(t, 1)
                    if rounded_t in pos_times:
                        lat, lon = pos_times[rounded_t]
                        rad = np.radians(90 - angle)
                        vector_length = 0.05

                        end_lon = lon + np.cos(rad) * vector_length
                        end_lat = lat + np.sin(rad) * vector_length

                        track_line_lons.append(end_lon)
                        track_line_lats.append(end_lat)

                all_lons = full_lons + track_line_lons
                all_lats = full_lats + track_line_lats

                # линию последнего угла
                if track_line_lons:
                    last_angle = gs_data[-1][1]
                    self.ax.plot(track_line_lons, track_line_lats, '-', color='red', linewidth=1.5,
                                label=f'Линия путевого угла: {last_angle:.1f}°')
                else:
                    self.ax.text(0.5, 0.5, f"Нет данных путевого угла для наложения", ha='center',
                                 transform=self.ax.transAxes)

                self.ax.set_aspect('equal', adjustable='datalim')
                self.ax.set_xlim(min(all_lons), max(all_lons))
                self.ax.set_ylim(min(all_lats), max(all_lats))
                self.ax.set_title(title)
                self.ax.grid(True, linestyle='--', alpha=0.3)
                self.ax.legend(fontsize=8)
                self.has_plot_data = True

        elif mode == 'airspd_angle':
            spd_data = self.icao_airspd_ts_dict.get(icao, [])
            pos_data = self.pos_dict.get(icao, [])
            title = f"Трек и ориентация самолёта: {display_id}"

            if not pos_data or not spd_data:
                self.ax.text(0.5, 0.5, f"Нет данных TC 19 subtype 3 для {icao}", ha='center')
                self.has_plot_data = False
            else:
                # полный трек
                full_lons = [lon for t, lat, lon in pos_data]
                full_lats = [lat for t, lat, lon in pos_data]
                self.ax.plot(full_lons, full_lats, '-', color='lime', linewidth=4, alpha=0.5, label='Полный трек')

                track_line_lons = []
                track_line_lats = []

                for t, angle in sorted(spd_data):

                    nearest = None
                    min_diff = None

                    for pos in pos_data:
                        diff = abs(pos[0] - t)
                        if min_diff is None or diff < min_diff:
                            min_diff = diff
                            nearest = pos

                    if nearest is None:
                        continue

                    lat, lon = nearest[1], nearest[2]

                    rad = np.radians(90 - angle)
                    vector_length = 0.05

                    end_lon = lon + np.cos(rad) * vector_length
                    end_lat = lat + np.sin(rad) * vector_length

                    track_line_lons.append(end_lon)
                    track_line_lats.append(end_lat)

                all_lons = full_lons + track_line_lons
                all_lats = full_lats + track_line_lats

                if track_line_lons:
                    last_angle = spd_data[-1][1]
                    self.ax.plot(track_line_lons, track_line_lats, '-', color='blue', linewidth=1.5,
                                label=f'Магнитный курс: {last_angle:.1f}°')
                else:
                    self.ax.text(0.5, 0.1, "Нет данных для наложения магнитного курса", ha='center', transform=self.ax.transAxes)

                self.ax.set_aspect('equal', adjustable='datalim')
                self.ax.set_xlim(min(all_lons), max(all_lons))
                self.ax.set_ylim(min(all_lats), max(all_lats))
                self.ax.set_title(title)
                self.ax.grid(True, linestyle='--', alpha=0.3)
                self.ax.legend(fontsize=8)
                self.has_plot_data = True

        elif mode == 'track':
            data = self.pos_dict.get(icao, [])
            title = f"Схема трека полёта: {display_id}"
            if not data:
                self.ax.text(0.5, 0.5, f"Нет данных о координатах для борта {icao}", ha='center', va='center')
                self.has_plot_data = False
            else:
                lons = [lon for t, lat, lon in data]
                lats = [lat for t, lat, lon in data]
                self.ax.plot(lons, lats, 'o', markersize=2, label='Трек')

        # гистограммы промежутков времени
        elif mode in self.hist_modes:
            callsign = self.icao_callsigns.get(icao, "N/A")
            display_id = f"{callsign} ({icao})" if callsign != "N/A" else icao

            if mode == 'reg05_hist':
                data_source = self.icao_airborne_pos_ts
                name = 'о местоположении в воздухе'
                color = 'blue'
                bar_color = 'mediumblue'
                center, dev, num_bins = 500, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера местоположения в воздухе {display_id} (REG05)'

            elif mode == 'reg06_1_hist':
                data_source = self.icao_surface_pos_ts
                name = 'о местоположении на земле при высокой частоте'
                color = 'red'
                bar_color = 'firebrick'
                center, dev, num_bins = 500, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера местоположения на земле при высокой частоте {display_id} (REG06)'
            
            elif mode == 'reg06_2_hist':
                data_source = self.icao_surface_pos_ts
                name = 'о местоположении на земле при низкой частоте'
                color = 'red'
                bar_color = 'firebrick'
                center, dev, num_bins = 5000, 200, 15
                title_text = f'Распределение интервалов сообщений сквиттера местоположения на земле при низкой частоте {display_id} (REG06)'

            elif mode == 'reg08_hist':
                data_source = self.icao_ident_ts
                name = 'об опознавательном коде и категории в полете'
                color = 'cyan'
                bar_color = 'skyblue'
                center, dev, num_bins = 5000, 200, 15
                title_text = f'Распределение интервалов сообщений сквиттера опознавательного кода и категории {display_id} (REG08)'
            
            elif mode == 'reg09_hist':
                data_source = self.icao_speed_ts
                name = 'о скорости при нахождении в воздухе'
                color = 'lime'
                bar_color = 'mediumseagreen'
                center, dev, num_bins = 500, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера путевой скорости при нахождении в воздухе: {display_id} (REG09)'

            elif mode == 'reg61_1_hist':
                data_source = self.icao_status
                name = 'о статусе воздушного судна для'
                color = 'darkviolet'
                bar_color = 'indigo'
                center, dev, num_bins = 5000, 200, 15
                title_text = f'Распределение интервалов сообщений сквиттера статуса {display_id} (REG61)'

            elif mode == 'reg61_2_hist':
                data_source = self.icao_emg_ts
                name = 'о сигнале бедствия воздушного судна'
                color = 'darkviolet'
                bar_color = 'indigo'
                center, dev, num_bins = 800, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера сигнала бедствия {display_id} (REG61)'

            elif mode == 'reg61_3_hist':
                data_source = self.icao_mode_change
                name = 'о статусe смены Mode A'
                color = 'darkviolet'
                bar_color = 'indigo'
                center, dev, num_bins = 800, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера статуса передающей системы {display_id} (REG61)'
            
            elif mode == 'reg61_4_hist':
                data_source = self.icao_tcas_ra
                name = 'о статусe передачи TCAS RA'
                color = 'darkviolet'
                bar_color = 'indigo'
                center, dev, num_bins = 800, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера статуса TCAS RA {display_id} (REG61)'
            
            elif mode == 'reg62_hist':
                data_source = self.icao_target_state
                name = 'о состоянии и статусе цели'
                color = 'gold'
                bar_color = 'darkorange'
                center, dev, num_bins = 1250, 50, 15
                title_text = f'Распределение интервалов сообщений сквиттера состояния и статуса цели {display_id} (REG62)'

            elif mode == 'reg65_1_hist':
                data_source = self.icao_air_op_status
                name = 'об эксплуатационном статусе в полете'
                color = 'mediumaquamarine'
                bar_color = 'lightseagreen'
                center, dev, num_bins = 2500, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера эксплуатационного статуса в полете {display_id} (REG65)'    
            
            elif mode == 'reg65_2_hist':
                data_source = self.icao_surf_op_status
                name = 'об эксплуатационном статусе на земле'
                color = 'mediumaquamarine'
                bar_color = 'lightseagreen'
                center, dev, num_bins = 2500, 100, 15
                title_text = f'Распределение интервалов сообщений сквиттера эксплуатационного статуса на земле {display_id} (REG65)'  

            elif mode == 'df11_hist':
                data_source = self.icao_df11_ts
                name = 'об опознавании'
                color = 'orange'
                bar_color = 'darkorange'
                center, dev, num_bins = 1000, 200, 15
                title_text = f'Распределение интервалов сообщений сквиттера опознавания {display_id} (DF11)'
            
            if icao in data_source and len(data_source[icao]) > 0:
                timestamps = np.array(sorted(data_source[icao]))
                intervals = np.diff(timestamps) * 1000
                intervals = intervals[intervals >= 0]
                
                if len(intervals) > 0:
                    low = center - dev
                    high = center + dev
                    
                    left = intervals[intervals < low]
                    middle = intervals[(intervals >= low) & (intervals <= high)]
                    right = intervals[intervals > high]
                    
                    bar_width = (high - low) / num_bins
                    
                    bin_edges = np.concatenate(([0], np.linspace(low, high, num_bins + 1)))
                    self.ax.hist(
                        middle,
                        bins=bin_edges,
                        alpha=0.6,
                        color=color,
                        edgecolor='black',
                        label=f"{center-dev}-{center+dev}: {len(middle)}"
                    )

                    self.ax.bar(
                        low - bar_width,
                        len(left),
                        width=bar_width,
                        align='edge',
                        color=bar_color,
                        edgecolor='black',
                        label=f"0–{center-dev}: {len(left)}"
                    )

                    self.ax.bar(
                        high,
                        len(right),
                        width=bar_width,
                        align='edge',
                        color=bar_color,
                        edgecolor='black',
                        label=f"> {center+dev}: {len(right)}"
                    )

                    min_interval = intervals.min()
                    max_interval = intervals.max()

                    self.ax.set_xlim(low - bar_width, high + bar_width)
                    self.ax.axvline(low, linestyle='--', color='black', alpha=0.8)
                    self.ax.axvline(high, linestyle='--', color='black', alpha=0.8)
                    self.ax.set_xlabel('Интервал между сообщениями (мс)')
                    self.ax.set_ylabel('Количество')
                    self.ax.set_title(title_text)
                    self.ax.legend(title=f"Всего интервалов {len(intervals)}")

                    stats_text = f"Min: {round(min_interval, 2)} мс\nMax: {round(max_interval, 2)} мс"
                    self.ax.text(
                        0.02, 0.98,
                        stats_text,
                        transform=self.ax.transAxes,
                        ha='left',
                        va='top',
                        bbox=dict(facecolor='white', alpha=0.8)
                    )
                    self.ax.grid(True, linestyle='--', alpha=0.7)
                    self.has_plot_data = True
                    self.fig.canvas.draw_idle()
                else:
                    self.ax.text(0.5, 0.5, f"Нет данных {name} для {icao}", ha='center', va='center', fontsize=15)
                    self.has_plot_data = False
            
            else:
                self.ax.text(0.5, 0.5, f"Нет данных {name} для {icao}", ha='center', va='center', fontsize=15)
                self.has_plot_data = False
        
        if self.has_plot_data == False:
            self.ax.set_axis_off()

        # специльная настройка для гистограммы
        if mode.endswith('_hist'):
            self.fig.canvas.draw_idle()
            return
        
        # установка общих элементов: заголовок и сетка
        self.ax.set_title(title)
        self.ax.grid(True, linestyle='--', alpha=0.7)

        # специальная настройка для графика трека (карты)
        if mode == 'track' or mode == 'reg09_tracks' or mode == 'track_angle' \
            or mode == 'gs_spd_angle' or mode == 'airspd_angle':
            # равномасштабные оси
            self.ax.set_aspect('equal', adjustable='datalim')
            self.ax.set_xlabel("Долгота (°)")
            self.ax.set_ylabel("Широта (°)")
        # общие настройки для временных графиков
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

    # масштабирование колесом мыши
    def on_scroll(self, event):
        # если нет данных для борта
        if not self.has_plot_data:
            return
        # если курсор не над осями, ничего не делаем
        if event.inaxes != self.ax: 
            return

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
        if mode == 'track' or mode == 'reg09_tracks' or mode == 'track_angle' \
            or mode == 'gs_spd_angle' or mode == 'airspd_angle':
            cur_xlim = self.ax.get_xlim()
            cur_ylim = self.ax.get_ylim()
            xdata = event.xdata
            ydata = event.ydata
            if xdata is None or ydata is None: 
                return

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

    # навигация между бортами и графиками
    def show_graphs(self, event=None):
        if self.current_mode_group == 'graphs':
            return
        self.current_mode_group = 'graphs'
        self.plot_modes = self.graph_modes
        self.plot_mode_idx = 0
        if hasattr(self, 'radio_mode'):
            self.radio_mode.set_active(0)
        self.plot_current()
   
    def show_hists(self, event=None):
        if self.current_mode_group == 'hists':
            return
        self.current_mode_group = 'hists'
        self.plot_modes = self.hist_modes
        self.plot_mode_idx = 0
        if hasattr(self, 'radio_mode'):
            self.radio_mode.set_active(1)
        self.plot_current()

    def on_radio_changed(self, label):
        if label == 'Графики':
            self.show_graphs()
        elif label == 'Гистограммы':
            self.show_hists()

    def next_icao(self, event=None):
        if not self.icao_list: 
            return
        self.icao_index = (self.icao_index + 1) % len(self.icao_list)
        self.plot_current()

    def prev_icao(self, event=None):
        if not self.icao_list: 
            return
        self.icao_index = (self.icao_index - 1 + len(self.icao_list)) % len(self.icao_list)
        self.plot_current()

    def next_mode(self, event=None):
        if not self.icao_list: 
            return
        self.plot_mode_idx = (self.plot_mode_idx + 1) % len(self.plot_modes)
        self.plot_current()

    def prev_mode(self, event=None):
        if not self.icao_list: 
            return
        self.plot_mode_idx = (self.plot_mode_idx - 1 + len(self.plot_modes)) % len(self.plot_modes)
        self.plot_current()

    # навигация с помощью клавиш
    def on_key(self, event):
        if event.key == 'right': 
            self.next_icao()
        elif event.key == 'left': 
            self.prev_icao()
        elif event.key == 'up': 
            self.next_mode()
        elif event.key == 'down': 
            self.prev_mode()