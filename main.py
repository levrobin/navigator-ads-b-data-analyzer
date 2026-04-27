import pyModeS as pms
import argparse
from dict_data import *
from parsing import *
from icao_plots import *
from time_formatter import *
from table_window import *
from PySide6.QtGui import *
import sys

MAX_MESSAGE_LENGTH = 32
DEFAULT_FILE = "data/2025-12-29.1766986424.606828104.t4433"

pms_df = pms.df
pms_icao = pms.icao
pms_tc = pms.adsb.typecode
pms_oe_flag = pms.adsb.oe_flag
pms_pos = pms.adsb.position
hex2bin = pms.common.hex2bin
bin2int = pms.common.bin2int
pms_velocity = pms.adsb.velocity
emergency_squawk = pms.adsb.emergency_squawk

def open_graphs_for_set(icao_set):
    if not icao_set:
        return
    
    plots_window = IcaoPlots(
        icao_set, icao_altitude, icao_speed, icao_positions, icao_courses, 
        icao_callsigns, icao_selected_altitude, icao_altitude_difference, 
        icao_baro_correction, 
        icao_airborne_pos_ts, 
        icao_surface_pos_ts, 
        icao_ident_air_ts, icao_ident_ground_hwr_ts, icao_ident_ground_lwr_ts,
        icao_spd_ts, 
        icao_status_ts, icao_emg_ts, icao_mode_a_ts, icao_tcas_ts, 
        icao_target_state_ts, 
        icao_air_op_status_ts, icao_air_op_status_change_ts, icao_surf_op_status_hwr_ts, icao_surf_op_status_lwr_ts,
        icao_acq_ts, 
        icao_track_angles, icao_gs_spd_ts, icao_airspd_ts
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
    open_graphs_for_set(set(adsb_icao_list))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('img/airplane.png'))
    # парсинг аргументов из командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Имя входного файла", default=DEFAULT_FILE)
    parser.add_argument("-a", "--aircraft", help="ICAO адрес конкретного борта")
    args = parser.parse_args()

    file_path = args.file
    target_icao = args.aircraft.upper() if args.aircraft else None
    
    try:
        # основной цикл чтения файла
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