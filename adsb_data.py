from dataclasses import *

@dataclass
class AdsbData:
    # основные параметры полета
    altitude: dict = field(default_factory=dict)
    speed: dict = field(default_factory=dict)
    positions: dict = field(default_factory=dict)
    courses: dict = field(default_factory=dict)
    callsigns: dict = field(default_factory=dict)
    sel_alt: dict = field(default_factory=dict)
    altitude_diff: dict = field(default_factory=dict)
    baro_corr: dict = field(default_factory=dict)

    # временные метки
    airborne_pos_ts: dict = field(default_factory=dict)
    surface_pos_ts: dict = field(default_factory=dict)
    
    ident_air_ts: dict = field(default_factory=dict)
    ident_ground_hwr_ts: dict = field(default_factory=dict)
    ident_ground_lwr_ts: dict = field(default_factory=dict)
    
    spd_ts: dict = field(default_factory=dict)

    status_ts: dict = field(default_factory=dict)
    emg_ts: dict = field(default_factory=dict)
    mode_a_ts: dict = field(default_factory=dict)
    tcas_ts: dict = field(default_factory=dict)

    target_state_ts: dict = field(default_factory=dict)

    air_op_status_ts: dict = field(default_factory=dict)
    air_op_status_change_ts: dict = field(default_factory=dict)
    surf_op_status_hwr_ts: dict = field(default_factory=dict)
    surf_op_status_lwr_ts: dict = field(default_factory=dict)

    acq_ts: dict = field(default_factory=dict)

    track_angles: dict = field(default_factory=dict)
    gs_spd_ts: dict = field(default_factory=dict)
    airspd_ts: dict = field(default_factory=dict)