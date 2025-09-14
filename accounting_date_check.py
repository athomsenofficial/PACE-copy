from datetime import datetime
from dateutil.relativedelta import relativedelta
from constants import SCODS

def accounting_date_check(date_arrived_station, grade, year):
    if not date_arrived_station:
        return False

    scod = f'{SCODS.get(grade)}-{year}'
    formatted_scod_date = datetime.strptime(scod, "%d-%b-%Y")
    accounting_date = formatted_scod_date - relativedelta(days=120 - 1)
    adjusted_accounting_date = accounting_date.replace(day=3, hour=23, minute=59, second=59)

    if date_arrived_station > adjusted_accounting_date:
        return False
    return True
