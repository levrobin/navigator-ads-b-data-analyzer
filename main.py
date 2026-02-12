import pyModeS as pms
import argparse
from dict_data import *
from parsing import *
from time_formatter import *
from icao_plots import *
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

if __name__ == '__main__':
    # парсинг аргументов из командной строки
    parser = argparse.ArgumentParser()
    parser.add_argument("-f", "--file", help="Имя входного файла", default=DEFAULT_FILE)
    parser.add_argument("-a", "--aircraft", help="ICAO адрес конкретного борта")
    args = parser.parse_args()

    file_path = args.file
    target_icao = args.aircraft.upper() if args.aircraft else None
    
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
                    df = pms_df(message_str)
                except Exception:
                    continue 

                if df == 11:
                    try:
                        aa = pms_icao(message_str)
                    except Exception:
                        continue
                    icao_acq_ts.setdefault(aa, []).append(timestamp)
                    continue

                # только ads-b сообщения
                if df not in (17, 18): 
                    continue 

                try:
                    aa = pms_icao(message_str)
                except Exception:
                    continue

                # фильтрация по заданному борту
                if target_icao and aa != target_icao: 
                    continue

                adsb_icao_list.add(aa)

                # время первого/последнего сообщения для борта
                if aa not in icao_times:
                    icao_times[aa] = {"first": timestamp, "last": timestamp}
                else:
                    icao_times[aa]["last"] = timestamp
                
                try:
                    tc = pms_tc(message_str)
                except Exception:
                    continue
                    
                if 5 <= tc <= 8:
                    icao_surface_pos_ts[aa].append(timestamp)

                # сообщения с высотой и координатами (tc 9-18)
                elif 9 <= tc <= 18:
                    icao_airborne_pos_ts[aa].append(timestamp)

                    alt = get_altitude(message_str)
                    if alt is not None and -1000 <= alt <= 50000:
                        icao_altitude[aa].append((timestamp, alt, 'baro'))
                    
                    # логика декодирования координат из двух cpr сообщений
                    cpr_messages.setdefault(aa, [None, None])
                    oe_flag = pms_oe_flag(message_str)
                    cpr_messages[aa][oe_flag] = (message_str, timestamp)
                    # если получены оба сообщения (чётное и нечётное) в пределах 10 секунд
                    if all(cpr_messages[aa]):
                        msg0, t0 = cpr_messages[aa][0]
                        msg1, t1 = cpr_messages[aa][1]
                        if abs(t0 - t1) < 10:
                            pos = pms_pos(msg0, msg1, t0, t1)
                            if pos:
                                icao_positions[aa].append((timestamp, pos[0], pos[1]))
                            # сбрасываем сообщения для следующей пары
                            cpr_messages[aa] = [None, None]

                # сообщения с позывным (tc 1-4)
                elif 1 <= tc <= 4:
                    icao_ident_ts[aa].append(timestamp)
                    cs = get_callsign(message_str)
                    if cs: 
                        icao_callsigns[aa] = cs

                elif tc == 19:
                    icao_spd_ts[aa].append(timestamp)

                    msg_bin = hex2bin(message_str)
                    subtype = bin2int(msg_bin[37:40])

                    try:
                        spd, angle, ns_vel, ew_vel = pms_velocity(message_str)
                    except Exception:
                        continue

                    if subtype == 1:
                        icao_gs_spd_ts[aa].append((timestamp, angle))
                    elif subtype == 3:
                        icao_airspd_ts[aa].append((timestamp, angle))

                    gs = get_velocity(message_str)
                    if gs is not None and 0 <= gs <= 1000:
                        icao_speed[aa].append((timestamp, gs))

                    track_angle = get_track_angle(message_str)
                    if track_angle is not None:
                        icao_track_angles[aa].append((timestamp, track_angle))
                    
                    course = get_course(message_str)
                    if course is not None:
                        icao_courses[aa].append((timestamp, course))
                    
                    # разница высот
                    alt_diff = get_altitude_difference(message_str)
                    if alt_diff is not None:
                        icao_altitude_difference[aa].append((timestamp, alt_diff))
                        icao_has_gnss[aa] = True

                # сообщения с GNSS высотой
                elif 20 <= tc <= 22:
                    icao_airborne_pos_ts[aa].append(timestamp)

                    alt = get_altitude(message_str)
                    if alt is not None and -1000 <= alt <= 50000:
                        icao_altitude[aa].append((timestamp, alt, 'gnss'))
                        icao_has_gnss[aa] = True
                            
                elif tc == 28:
                    # TCAS RA (subtype 2)
                    try:
                        if pms.adsb.tcas_ra(message_str):
                            icao_tcas_ts[aa].append(timestamp)
                            continue
                    except Exception:
                        pass
                    
                    # остальные подтипы (0 и 1)
                    try:
                        squawk = emergency_squawk(message_str)
                    except RuntimeError as e:
                        # пропуск ошибки ACAS-RA
                        if "ACAS-RA" in str(e):
                            squawk = None
                        else:
                            squawk = None
                    except Exception:
                        squawk = None

                    if squawk is not None:
                        # subtype 0 или 1
                        try:
                            is_emg = pms.adsb.is_emergency(message_str)
                        except RuntimeError as e:
                            if "ACAS-RA" in str(e):
                                is_emg = False
                            else:
                                is_emg = False
                        except Exception:
                            is_emg = False
                        if is_emg:
                            icao_emg_ts[aa].append(timestamp)
                        else:
                            icao_status_ts[aa].append(timestamp)

                        prev = last_mode_a.get(aa)
                        if prev is not None and squawk != prev:
                            if squawk not in ("1000", "7500", "7600", "7700"):
                                change_event_start[aa] = timestamp

                        if aa in change_event_start and (timestamp - change_event_start[aa] <= 24.5):
                            icao_mode_a_ts[aa].append(timestamp)

                        last_mode_a[aa] = squawk

                elif tc == 29:
                    icao_target_state_ts[aa].append(timestamp)
                    sel_alt = get_selected_altitude(message_str)
                    if sel_alt:
                        sel_alt_value, modes = sel_alt
                        icao_selected_altitude[aa].append((timestamp, sel_alt_value))
                        icao_has_selected_alt[aa] = True
                        modes_key = f"{aa}_modes"
                        existing_modes = icao_callsigns.get(modes_key, set())
                        icao_callsigns[modes_key] = existing_modes.union(modes)
                    
                    # барокоррекция
                    baro_corr = get_baro_correction(message_str)
                    if baro_corr is not None:
                        icao_baro_correction[aa].append((timestamp, baro_corr))

                elif tc == 31:
                    msg_bin = hex2bin(message_str)
                    subtype = bin2int(msg_bin[37:40])

                    if subtype == 0:
                        icao_air_op_status_ts[aa].append(timestamp)
                    elif subtype == 1:
                        icao_surf_op_status_ts[aa].append(timestamp)

        if target_icao:
            if target_icao not in adsb_icao_list:
                print(f"\nБорт {target_icao} не найден")
                sys.exit(0)
        # итоговая сводная таблица
        print("=" * 160)
        print(" " * 60 + "Сводная таблица")
        print("=" * 160)
        print(f"{'ICAO':<8} {'Номер рейса':<12} {'Первое (UTC)':<33} {'Последнее (UTC)':<33} "
              f"{'Координаты':<12} {'Курс':<8} {'Выб. высота':<12} {'Разн. высот':<12} "
              f"{'Барокорр.':<10} {'GNSS':<6}")
        print("-" * 160)

        for icao in sorted(list(adsb_icao_list)):
            if icao not in icao_times: 
                continue
            times = icao_times[icao]
            
            first_utc_str = format_timestamp_with_nanoseconds(times["first"])
            last_utc_str = format_timestamp_with_nanoseconds(times["last"])
            
            callsign = icao_callsigns.get(icao, "N/A")
            
            sel_alt_flag = "Да" if icao_has_selected_alt.get(icao) else "Нет"
            coord_flag = "Да" if icao in icao_positions and icao_positions[icao] else "Нет"
            course_flag = "Да" if icao in icao_courses and icao_courses[icao] else "Нет"
            alt_diff_flag = "Да" if icao in icao_altitude_difference and icao_altitude_difference[icao] else "Нет"
            baro_corr_flag = "Да" if icao in icao_baro_correction and icao_baro_correction[icao] else "Нет"
            gnss_flag = "Да" if icao_has_gnss.get(icao) else "Нет"
            print(f"{icao:<8} {callsign:<12} {first_utc_str:<33} "
                  f"{last_utc_str:<33} "
                  f"{coord_flag:<12} {course_flag:<8} {sel_alt_flag:<12} {alt_diff_flag:<12} "
                  f"{baro_corr_flag:<10} {gnss_flag:<6}")

        print(f"\nВсего бортов: {len(adsb_icao_list)}\n")
        
        # запуск графиков с передачей всех собранных данных
        IcaoPlots(icao_altitude, icao_speed, icao_positions, icao_courses, adsb_icao_list, 
                   icao_callsigns, icao_selected_altitude, icao_altitude_difference, 
                   icao_baro_correction, icao_airborne_pos_ts, icao_surface_pos_ts, icao_ident_ts,
                   icao_spd_ts, icao_status_ts, icao_emg_ts, icao_mode_a_ts, icao_tcas_ts,
                   icao_target_state_ts, icao_air_op_status_ts, icao_surf_op_status_ts, icao_acq_ts, 
                   icao_track_angles, icao_gs_spd_ts, icao_airspd_ts)
        
    except FileNotFoundError:
        print(f"Файл {file_path} не найден")
    except Exception as e:
        print(f"Произошла критическая ошибка: {e}")