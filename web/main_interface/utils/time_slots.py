from datetime import datetime, timedelta


def generate_time_slots(start="09:00", end="20:00", step=30):
    slots = []
    start_dt = datetime.strptime(start, "%H:%M")
    end_dt = datetime.strptime(end, "%H:%M")
    while start_dt < end_dt:
        slot_start = start_dt.strftime("%H:%M")
        slot_end = (start_dt + timedelta(minutes=step)).strftime("%H:%M")
        slots.append(f"{slot_start}-{slot_end}")
        start_dt += timedelta(minutes=step)
    return slots
