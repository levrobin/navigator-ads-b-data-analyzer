import argparse
from dict_data import *
from parsing import *
from icao_plots import *
from time_formatter import *
from table_window import *
from PySide6.QtGui import *
import sys
from adsb_data import *

adsb_data = AdsbData(
    # параметры полета
    altitude=icao_altitude,
    speed=icao_speed,
    positions=icao_positions,
    courses=icao_courses,
    callsigns=icao_callsigns,
    sel_alt=icao_selected_altitude,
    altitude_diff=icao_altitude_difference,
    baro_corr=icao_baro_correction,

    # временные метки
    airborne_pos_ts=icao_airborne_pos_ts,
    surface_pos_ts=icao_surface_pos_ts,

    ident_air_ts=icao_ident_air_ts,
    ident_ground_hwr_ts=icao_ident_ground_hwr_ts,
    ident_ground_lwr_ts=icao_ident_ground_lwr_ts,

    spd_ts=icao_spd_ts,

    status_ts=icao_status_ts,
    emg_ts=icao_emg_ts,
    mode_a_ts=icao_mode_a_ts,
    tcas_ts=icao_tcas_ts,

    target_state_ts=icao_target_state_ts,

    air_op_status_ts=icao_air_op_status_ts,
    air_op_status_change_ts=icao_air_op_status_change_ts,
    surf_op_status_hwr_ts=icao_surf_op_status_hwr_ts,
    surf_op_status_lwr_ts=icao_surf_op_status_lwr_ts,

    acq_ts=icao_acq_ts,

    track_angles=icao_track_angles,
    gs_spd_ts=icao_gs_spd_ts,
    airspd_ts=icao_airspd_ts
)

def open_graphs_for_set(icao_set):
    if not icao_set:
        return
    
    plots_window = IcaoPlots(
        icao_set, adsb_data
    )

    table_window.graph_windows.append(plots_window)
    
def open_graphs_for_row(row, column):
    # графики для конкретного борта
    item = table_window.table.item(row, 0)
    if not item:
        return
    
    icao = item.text().strip()
    if not icao:
        return
    
    open_graphs_for_set({icao})

def open_graphs_for_all():
    if not adsb_icao_list:
        QMessageBox.warning(
            table_window, 
            "Нет данных", 
            f"Файл не загружен или список бортов пуст"
        )
    
    open_graphs_for_set(set(adsb_icao_list))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('img/airplane.png'))
    # парсинг аргументов из командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Имя входного файла", default=None)
    parser.add_argument("-a", "--aircraft", help="ICAO адрес конкретного борта")
    args = parser.parse_args()

    file_path = args.file
    target_icao = args.aircraft.upper() if args.aircraft else None
    
    try:
        # основной цикл чтения файла
        if file_path:
            parse_ads_b_file(file_path, target_icao)

            if target_icao and target_icao not in adsb_icao_list:
                QMessageBox.warning(None, "Ошибка", f"Борт {target_icao} не найден")
                sys.exit(0)
        # итоговая сводная таблица
        table_window = TableWindow(
            adsb_icao_list, icao_times, icao_callsigns, 
            icao_positions, icao_courses, icao_has_selected_alt, 
            icao_altitude_difference, icao_baro_correction, 
            icao_has_gnss
        )
        table_window.show()
        table_window.table.cellDoubleClicked.connect(open_graphs_for_row)
        table_window.all_plots_btn.clicked.connect(open_graphs_for_all)
        sys.exit(app.exec())
        
    except FileNotFoundError:
        QMessageBox.warning(None, "Ошибка", f"Файл {file_path} не найден")
    except Exception as e:
        QMessageBox.critical(None, "Ошибка", f"{e}")