import pyModeS as pms
import numpy as np
from dict_data import *

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

# извлечение барометрической высоты из сообщения
def get_altitude(msg_str):
    try:
        # это ads-b сообщение
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
        # сообщение о положении (тип 9-18 или 20-22)
        tc = pms.adsb.typecode(msg_str)
        if 9 <= tc <= 18 or 20 <= tc <= 22:
            return pms.adsb.altitude(msg_str)
        return None
    except:
        return None

# извлечение скорости из сообщения
def get_velocity(msg_str):
    try:
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
        # сообщение о скорости (тип 19)
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
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
        # сообщение о скорости (тип 19)
        tc = pms.adsb.typecode(msg_str)
        if tc == 19:
            _, heading, _, _ = pms.adsb.velocity(msg_str)
            return heading
        return None
    except:
        return None
    
def get_track_angle(msg_str):
    try:
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None

        tc = pms.adsb.typecode(msg_str)
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

        if speed_type == 'GS':
            return angle
        
        return None
    except Exception as e:
        return None

# функция извлекает выбранную на автопилоте высоту и режимы
def get_selected_altitude(msg_str):
    try:
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
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
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
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
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
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
        df = pms.df(msg_str)
        if df not in [17, 18]: 
            return None
        # проверяем, что это сообщение идентификации (тип 1-4)
        tc = pms.adsb.typecode(msg_str)
        if 1 <= tc <= 4:
            callsign = pms.adsb.callsign(msg_str)
            if not callsign: 
                return None
            # очищаем позывной от лишних символов
            return ''.join(c for c in callsign if c.isalnum())
        return None
    except:
        return None