from collections import defaultdict

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

# для сбора данных
icao_times = {}
icao_altitude = defaultdict(list)
icao_speed = defaultdict(list)
icao_callsigns = {}
icao_selected_altitude = defaultdict(list)
icao_altitude_difference = defaultdict(list)
icao_baro_correction = defaultdict(list)
icao_has_selected_alt = {}
icao_has_gnss = {}
adsb_icao_list = set()
icao_positions = defaultdict(list)
icao_courses = defaultdict(list)
cpr_messages = {}

icao_track_angles = defaultdict(list)
icao_gs_spd_ts = defaultdict(list)
icao_airspd_ts = defaultdict(list)

# reg 05
icao_airborne_pos_ts = defaultdict(list)
# reg 06
icao_surface_pos_ts = defaultdict(list)

# reg 08
icao_ident_ts = defaultdict(list)

# reg 09
icao_spd_ts = defaultdict(list)

# reg 61
last_mode_a = {}
change_event_start = {}
icao_status_ts = defaultdict(list)
icao_emg_ts = defaultdict(list)
icao_tcas_ts = defaultdict(list)
icao_mode_a_ts = defaultdict(list)

# reg 62
icao_target_state_ts = defaultdict(list)

# reg 65
icao_air_op_status_ts = defaultdict(list)
icao_surf_op_status_ts = defaultdict(list)

# df 11
icao_acq_ts = defaultdict(list)