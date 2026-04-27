from time_formatter import *
from parsing import *
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt

class TableWindow(QWidget):
    def __init__(self, adsb_icao_list, icao_times, icao_callsigns, icao_positions, 
                 icao_courses, icao_has_selected_alt, icao_altitude_difference, 
                 icao_baro_correction, icao_has_gnss):
        super().__init__()
        self.graph_windows = []
        self.adsb_icao_list = adsb_icao_list
        self.icao_times = icao_times
        self.icao_callsigns = icao_callsigns
        self.icao_positions = icao_positions
        self.icao_courses = icao_courses
        self.icao_has_selected_alt = icao_has_selected_alt
        self.icao_altitude_difference = icao_altitude_difference
        self.icao_baro_correction = icao_baro_correction
        self.icao_has_gnss = icao_has_gnss

        self.setWindowTitle("Сводная таблица бортов")
        self.resize(1100, 600)
        
        layout = QVBoxLayout(self)
        top_layout = QHBoxLayout()

        self.total_label = QLabel()
        self.all_plots_btn = QPushButton("Открыть все графики")
        self.all_plots_btn.setFixedHeight(33)

        self.open_file_btn = QPushButton("Выбрать файл")
        self.open_file_btn.setFixedHeight(33)
        self.open_file_btn.clicked.connect(self.select_file)

        self.table = QTableWidget(0, 10, self)

        # стиль окна сводной таблицы
        self.setStyleSheet("""
            QPushButton {
                background-color: #6b6b6b;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #525252;
            }
            QPushButton:pressed {
                background-color: #706f6f;
            }
            QHeaderView::section {
                background-color: #6b6b6b;
                color: white;
                font-weight: bold;
                text-align: center;
            }
                           
            QTableWidget::item {
                padding: 10px;
                outline: none;
            }
                           
            QTableWidget::item:selected {
                background-color: #f5f5f5;
                color: black;
            }         
        """)

        # настройка стилей
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = self.total_label.font()
        font.setPointSize(14)
        self.total_label.setFont(font)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        headers = ["ICAO", "Позывной", "Первое (UTC)", "Последнее (UTC)",
                   "Координаты", "Курс", "Выб. высота", "Разн. высот", 
                   "Барокорр.", "GNSS"]
        self.table.setHorizontalHeaderLabels(headers)
        
        self.table.verticalHeader().setVisible(False)
        
        self.fill_table()
        
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setHighlightSections(False)

        header = self.table.horizontalHeader()

        # автоматический размер таблицы по содержимому
        for col in range(10):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)  # первое (UTC)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # последнее (UTC)
        
        top_layout.addWidget(self.total_label)
        top_layout.addStretch()
        top_layout.addWidget(self.open_file_btn)
        top_layout.addWidget(self.all_plots_btn)
        layout.addLayout(top_layout)
        layout.addWidget(self.table)
    
    def fill_table(self):
        self.table.setRowCount(0)
        
        for icao in sorted(list(self.adsb_icao_list)):
            if icao not in self.icao_times: 
                continue
            
            times = self.icao_times[icao]
            first_utc_str = format_timestamp_with_nanoseconds(times["first"])
            last_utc_str = format_timestamp_with_nanoseconds(times["last"])
            callsign = self.icao_callsigns.get(icao, "N/A")
        
            coord_flag = "Да" if icao in self.icao_positions and self.icao_positions[icao] else "Нет"
            course_flag = "Да" if icao in self.icao_courses and self.icao_courses[icao] else "Нет"
            sel_alt_flag = "Да" if self.icao_has_selected_alt.get(icao) else "Нет"
            alt_diff_flag = "Да" if icao in self.icao_altitude_difference and self.icao_altitude_difference[icao] else "Нет"
            baro_corr_flag = "Да" if icao in self.icao_baro_correction and self.icao_baro_correction[icao] else "Нет"
            gnss_flag = "Да" if self.icao_has_gnss.get(icao) else "Нет"
            
            # строка
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # заполнение ячеек
            self.add_table_item(row, 0, icao)
            self.add_table_item(row, 1, callsign)
            self.add_table_item(row, 2, first_utc_str)
            self.add_table_item(row, 3, last_utc_str)
            self.add_table_item(row, 4, coord_flag)
            self.add_table_item(row, 5, course_flag)
            self.add_table_item(row, 6, sel_alt_flag)
            self.add_table_item(row, 7, alt_diff_flag)
            self.add_table_item(row, 8, baro_corr_flag)
            self.add_table_item(row, 9, gnss_flag)

        self.total_label.setText(f"\nВсего бортов: {len(self.adsb_icao_list)}\n")
        
    def add_table_item(self, row, col, text):
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, col, item)

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите ADS-B файл",
            "",
            "ADS-B files (*.t4433);;All Files (*)",
        )

        if not file_path:
            return
        
        QApplication.setOverrideCursor(Qt.WaitCursor)
        
        try:
            for w in self.graph_windows:
                w.close()
            self.graph_windows.clear()

            adsb_icao_list.clear()
            icao_times.clear()
            icao_callsigns.clear()
            icao_positions.clear()
            icao_courses.clear()
            icao_has_selected_alt.clear()
            icao_altitude_difference.clear()
            icao_baro_correction.clear()
            icao_has_gnss.clear()

            icao_altitude.clear()
            icao_speed.clear()
            # reg 05
            icao_airborne_pos_ts.clear()
            # reg 06
            icao_surface_pos_ts.clear()
            # reg 08
            icao_ident_air_ts.clear()
            icao_ident_ground_hwr_ts.clear()
            icao_ident_ground_lwr_ts.clear()
            # reg 09
            icao_spd_ts.clear()
            # reg 61
            icao_status_ts.clear()
            icao_emg_ts.clear()
            icao_mode_a_ts.clear()
            icao_tcas_ts.clear()
            # reg 62
            icao_target_state_ts.clear()
            # reg 65
            icao_air_op_status_ts.clear()
            icao_air_op_status_change_ts.clear()
            icao_surf_op_status_hwr_ts.clear()
            icao_surf_op_status_lwr_ts.clear()
            # df 11
            icao_acq_ts.clear()

            icao_track_angles.clear()
            icao_gs_spd_ts.clear()
            icao_airspd_ts.clear()
            cpr_messages.clear()
            last_mode_a.clear()
            change_event_start.clear() 
            icao_selected_altitude.clear()
            
            parse_ads_b_file(file_path)
            self.fill_table()

        except Exception as e:
            QApplication.restoreOverrideCursor()
            print(f"Ошибка при чтении файла: {e}")
        finally:
            QApplication.restoreOverrideCursor()