import pyModeS as pms
from dict_data import *

pms_df = pms.df
pms_icao = pms.icao
pms_tc = pms.adsb.typecode
pms_oe_flag = pms.adsb.oe_flag
pms_pos = pms.adsb.position
hex2bin = pms.common.hex2bin
bin2int = pms.common.bin2int
pms_velocity = pms.adsb.velocity
pms_tcas_ra = pms.adsb.tcas_ra
emergency_squawk = pms.adsb.emergency_squawk
is_emergency = pms.adsb.is_emergency

# парсинг одной строки из файла с данными
def parse_ads_b_line(line):
    parts = line.strip().split()
    if len(parts) < 2:
        return None
    try:
        timestamp = float(parts[0])
    except ValueError:
        return None
    
    # определение нахождения hex данных
    if len(parts) >= 3 and parts[1] in ('DF', 'UF'): # если есть поле df/uf
        hex_parts = parts[2:]
    else:
        hex_parts = parts[1:]
    
    message_spaced = ' '.join(hex_parts).upper().strip()
    message_str = message_spaced.replace(" ", "")

    if not message_str:
         return None
    
    try:
        int(message_str, 16)
    except ValueError:
        return None
    
    return timestamp, message_spaced, message_str

# извлечение барометрической высоты из сообщения
def get_altitude(msg_str, tc):
    try:
        # сообщение о положении (тип 9-18 или 20-22)
        if 9 <= tc <= 18 or 20 <= tc <= 22:
            return pms.adsb.altitude(msg_str)
        return None
    except:
        return None

# извлечение скоростных данных
def get_velocity_data(msg_str, tc):
    try:
        if tc != 19:
            return None

        # данные о скорости
        v_data = pms.adsb.velocity(msg_str, source=True)

        if not v_data:
            return None
        
        # количество возвращенных значений
        if len(v_data) >= 6:
            speed, angle, vert_rate, speed_type, dir_source, vr_source = v_data[:6]
        else:
            # без source в случае ошибки
            v_data_simple = pms.adsb.velocity(msg_str, source=False)
            if not v_data_simple or len(v_data_simple) < 4:
                return None
            speed, angle, vert_rate, speed_type = v_data_simple[:4]
            dir_source = None
            vr_source = None

        return {
            "speed": speed,
            "angle": angle,
            "vert_rate": vert_rate,
            "speed_type": speed_type,
            "dir_source": dir_source,
            "vr_source": vr_source
        }

    except Exception:
        return None

# функция извлекает выбранную на автопилоте высоту и режимы
def get_selected_altitude(msg_str, tc):
    try:
        # это сообщение о статусе (тип 29)
        if tc != 29: 
            return None
        
        sel_alt_info = pms.adsb.selected_altitude(msg_str)
        if sel_alt_info is None: 
            return None
        
        selected_alt, raw_modes = sel_alt_info

        if selected_alt is not None and -2000 <= selected_alt <= 50000:
            # перевод режимов в понятные сокращения
            processed_modes = {MODE_MAP.get(m, m) for m in raw_modes}
            return selected_alt, processed_modes
        
        return None
    except Exception as e:
        return None

# получение разности высот
def get_altitude_difference(msg_str, tc):
    try:
        # это сообщение о скорости (тип 19)
        if tc != 19:
            return None
        
        altitude_diff = pms.adsb.altitude_diff(msg_str)
        if altitude_diff is not None and -2500 <= altitude_diff <= 2500:
            return altitude_diff
        
        return None
    
    except Exception as e:
        return None

# получение барокоррекции
def get_baro_correction(msg_str, tc):
    try:
        # это сообщение о статусе (тип 29)
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

# получение позывного (callsign)
def get_callsign(msg_str, tc):
    try:
        # это сообщение идентификации (тип 1-4)
        if 1 <= tc <= 4:
            callsign = pms.adsb.callsign(msg_str)
            if not callsign: 
                return None
            # очистка позывного от лишних символов
            return ''.join(c for c in callsign if c.isalnum())
        return None
    except:
        return None
    
def get_op_status_key(msg_str):
    msg_bin = hex2bin(msg_str)
    me = msg_bin[32:88]  # биты 33–88

    st = bin2int(me[5:8])          # subtype / ST
    version = bin2int(me[8:11])    # ADS-B version, ME биты 41–43

    nic_s = int(me[11])            # NIC supplement, ME бит 44
    nacp = bin2int(me[12:16])      # NACp, ME биты 45–48
    sil = bin2int(me[17:19])       # SIL, ME биты 50–51

    return (st, version, nic_s, nacp, sil)
    
def parse_ads_b_file(file_path, target_icao=None):
    # основной цикл чтения файла
    with open(file_path, "r") as f:
        for line in f:
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
            if df != 17:
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

            state = icao_state.setdefault(aa, {
                "airborne": False,
                "ground": False,
                "surface_hwr": False,
                "surface_lwr": False,
                "last_surface_ts": None,
            })
                
            if 5 <= tc <= 8:
                icao_surface_pos_ts[aa].append(timestamp)

                prev_ts = state["last_surface_ts"]
                if prev_ts is None:
                    state["ground"] = True
                else:
                    dt = timestamp - prev_ts
                    if 0.4 <= dt <= 0.6:
                        state["ground"] = True
                        state["surface_hwr"] = True
                        state["surface_lwr"] = False
                    elif 4.8 <= dt <= 5.2:
                        state["ground"] = True
                        state["surface_hwr"] = False
                        state["surface_lwr"] = True

                state["last_surface_ts"] = timestamp

            # сообщения с высотой и координатами (tc 9-18)
            elif 9 <= tc <= 18:
                icao_airborne_pos_ts[aa].append(timestamp)
                state["airborne"] = True
                state["ground"] = False

                alt = get_altitude(message_str, tc)
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


            elif tc == 19:
                icao_spd_ts[aa].append(timestamp)

                msg_bin = hex2bin(message_str)
                subtype = bin2int(msg_bin[37:40])

                v = get_velocity_data(message_str, tc)
                if not v:
                    continue
                speed = v["speed"]
                angle = v["angle"]
                speed_type = v["speed_type"]

                if subtype == 1:
                    icao_gs_spd_ts[aa].append((timestamp, angle))
                elif subtype == 3:
                    icao_airspd_ts[aa].append((timestamp, angle))

                if speed is not None and 0 <= speed <= 1000:
                    icao_speed[aa].append((timestamp, speed))

                if speed_type == 'GS':
                    icao_track_angles[aa].append((timestamp, angle))
                
                elif speed_type == 'IAS':
                    icao_courses[aa].append((timestamp, angle))
                
                # разница высот
                alt_diff = get_altitude_difference(message_str, tc)
                if alt_diff is not None:
                    icao_altitude_difference[aa].append((timestamp, alt_diff))
                    icao_has_gnss[aa] = True

            # сообщения с GNSS высотой
            elif 20 <= tc <= 22:
                icao_airborne_pos_ts[aa].append(timestamp)
                state["airborne"] = True
                state["ground"] = False

                alt = get_altitude(message_str, tc)
                if alt is not None and -1000 <= alt <= 50000:
                    icao_altitude[aa].append((timestamp, alt, 'gnss'))
                    icao_has_gnss[aa] = True
                        
            # сообщения с позывным (tc 1-4)
            elif 1 <= tc <= 4:
                if state["airborne"]:
                    icao_ident_air_ts[aa].append(timestamp)
                elif state["ground"] and state["surface_hwr"]:
                    icao_ident_ground_hwr_ts[aa].append(timestamp)
                elif state["ground"] and state["surface_lwr"]:
                    icao_ident_ground_lwr_ts[aa].append(timestamp)
                cs = get_callsign(message_str, tc)
                if cs:
                    icao_callsigns[aa] = cs

            elif tc == 28:
                msg_bin = hex2bin(message_str)
                subtype = bin2int(msg_bin[37:40])
                try:
                    if pms_tcas_ra(message_str):
                        icao_tcas_ts[aa].append(timestamp)
                        continue
                except Exception:
                    pass
                if subtype == 2:
                    icao_tcas_ts[aa].append(timestamp)
                    continue
                if subtype != 1:
                    continue
                try:
                    squawk = emergency_squawk(message_str)
                except Exception:
                    squawk = None
                try:
                    is_emg = is_emergency(message_str)
                except Exception:
                    is_emg = False

                prev = last_mode_a.get(aa)
                is_change = (
                    squawk is not None and
                    prev is not None and
                    squawk != prev and
                    squawk not in ("1000", "7500", "7600", "7700")
                )

                if squawk is not None:
                    last_mode_a[aa] = squawk
                if is_change:
                    change_event_start[aa] = timestamp
                in_change_window = (
                    aa in change_event_start and
                    (timestamp - change_event_start[aa] <= 24.5)
                )
                if is_emg or squawk in ("7500", "7600", "7700"):
                    icao_emg_ts[aa].append(timestamp)
                elif in_change_window:
                    icao_mode_a_ts[aa].append(timestamp)
                else:
                    icao_status_ts[aa].append(timestamp)
                        
            elif tc == 29:
                icao_target_state_ts[aa].append(timestamp)
                sel_alt = get_selected_altitude(message_str, tc)
                if sel_alt:
                    sel_alt_value, modes = sel_alt
                    icao_selected_altitude[aa].append((timestamp, sel_alt_value))
                    icao_has_selected_alt[aa] = True
                    modes_key = f"{aa}_modes"
                    existing_modes = icao_callsigns.get(modes_key, set())
                    icao_callsigns[modes_key] = existing_modes.union(modes)
                # барокоррекция
                baro_corr = get_baro_correction(message_str, tc)
                if baro_corr is not None:
                    icao_baro_correction[aa].append((timestamp, baro_corr))

            elif tc == 31:
                msg_bin = hex2bin(message_str)
                subtype = bin2int(msg_bin[37:40])

                current_state = get_op_status_key(message_str)
                prev_state = last_op_status_state.get(aa)
                is_change = prev_state is not None and prev_state != current_state
                last_op_status_state[aa] = current_state
                if subtype == 0:
                    icao_air_op_status_ts[aa].append(timestamp)
                    if is_change:
                        icao_air_op_status_change_ts[aa].append(timestamp)

                elif subtype == 1:
                    if state["ground"] and state["surface_lwr"]:
                        icao_surf_op_status_lwr_ts[aa].append(timestamp)
                        if is_change:
                            icao_air_op_status_change_ts[aa].append(timestamp)

                    elif state["ground"] and state["surface_hwr"]:
                        icao_surf_op_status_hwr_ts[aa].append(timestamp)
                        if is_change:
                            icao_air_op_status_change_ts[aa].append(timestamp)