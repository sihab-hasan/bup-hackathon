from enum import StrEnum


class DirectiveType(StrEnum):
    SOLAR_REDUCTION = "solar_reduction"
    MINIMUM_BATTERY_RESERVE = "minimum_battery_reserve"
    NO_CHARGE_WINDOW = "no_charge_window"
    NO_DISCHARGE_WINDOW = "no_discharge_window"
    MAX_GRID_WINDOW = "max_grid_window"
    NO_OP = "no_op"


class BatteryAction(StrEnum):
    CHARGE = "charge"
    DISCHARGE = "discharge"
    IDLE = "idle"
