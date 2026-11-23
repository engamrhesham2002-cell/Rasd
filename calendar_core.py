# Rasd - نواة التقويم: قواعد التكرار (RRULE)، فروق التوقيت، وتوزيع المواعيد المتداخلة.
# هذا الملف مستقل عن Tk حتى يسهل اختباره، ويُستخدم من طبقة البيانات والواجهة.
import calendar
import json
import re
from datetime import date, datetime, time, timedelta, timezone

WEEKDAY_CODES = ('MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU')
WEEKDAY_NAMES_AR = ('الاثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد')
MONTH_NAMES_AR = ('يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر')


def parse_hhmm(value):
    """يحوّل HH:MM أو h:MM AM/PM إلى عدد دقائق من منتصف الليل."""
    text = str(value or '').strip().upper()
    if not text:
        return None
    try:
        if text.endswith((' AM', ' PM')):
            clock, period = text.rsplit(' ', 1)
            hour, minute = (int(part) for part in clock.split(':'))
            if not 1 <= hour <= 12 or not 0 <= minute < 60:
                return None
            hour = (hour % 12) + (12 if period == 'PM' else 0)
        else:
            hour, minute = (int(part) for part in text.split(':'))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return hour * 60 + minute
    except (TypeError, ValueError):
        pass
    return None


def minutes_to_hhmm(minutes):
    minutes = max(0, min(24 * 60, int(minutes)))
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def local_to_utc_iso(value, tz=None):
    """يحوّل وقتًا محليًا (naive) إلى نص UTC ISO للتخزين.

    عند عدم تمرير منطقة زمنية نستخدم توقيت الجهاز الفعلي مع مراعاة
    التوقيت الصيفي للتاريخ نفسه (عبر timestamp) بدل تثبيت إزاحة اليوم.
    """
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        value = datetime.combine(value, time.min)
    if value.tzinfo is None:
        if tz is None:
            try:
                return datetime.fromtimestamp(value.timestamp(), timezone.utc).isoformat()
            except (OSError, OverflowError, ValueError):
                pass
        value = value.replace(tzinfo=tz or datetime.now().astimezone().tzinfo)
    return value.astimezone(timezone.utc).isoformat()


def utc_iso_to_local(value, tz=None):
    """يقرأ نص UTC ISO ويعيد datetime محليًا بدون معلومات توقيت."""
    if not value:
        return None
    text = str(value).strip().replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if tz is not None:
        return parsed.astimezone(tz).replace(tzinfo=None)
    return parsed.astimezone().replace(tzinfo=None)


def local_timezone_label():
    try:
        info = datetime.now().astimezone()
        name = info.tzname() or 'Local'
        offset = info.utcoffset() or timedelta(0)
        sign = '+' if offset >= timedelta(0) else '-'
        total = abs(int(offset.total_seconds()))
        return f'{name} (UTC{sign}{total // 3600:02d}:{(total % 3600) // 60:02d})'
    except Exception:
        return 'Local'


# ---------------------------------------------------------------------------
# RRULE: قراءة وكتابة قواعد التكرار الشائعة
# ---------------------------------------------------------------------------
def parse_rrule(text):
    """يفكّ RRULE مبسطًا إلى قاموس. يدعم FREQ/INTERVAL/BYDAY/COUNT/UNTIL."""
    data = {'freq': None, 'interval': 1, 'byday': [], 'until': None, 'count': None}
    if not text:
        return data
    raw = str(text).strip().upper()
    if raw.startswith('RRULE:'):
        raw = raw[6:]
    for part in raw.split(';'):
        if not part or '=' not in part:
            continue
        key, value = part.split('=', 1)
        key = key.strip()
        value = value.strip()
        if key == 'FREQ':
            if value in ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'):
                data['freq'] = value
        elif key == 'INTERVAL':
            try:
                data['interval'] = max(1, int(value))
            except ValueError:
                pass
        elif key == 'BYDAY':
            days = []
            for item in value.split(','):
                code = item.strip().lstrip('+-0123456789')[:2]
                if code in WEEKDAY_CODES and code not in days:
                    days.append(code)
            data['byday'] = days
        elif key == 'COUNT':
            try:
                data['count'] = max(1, int(value))
            except ValueError:
                pass
        elif key == 'UNTIL':
            parsed = None
            for fmt in ('%Y%m%dT%H%M%S', '%Y%m%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
                try:
                    parsed = datetime.strptime(value, fmt)
                    # تاريخ فقط يعني أن اليوم نفسه مشمول حتى نهايته.
                    if fmt in ('%Y%m%d', '%Y-%m-%d'):
                        parsed = parsed.replace(hour=23, minute=59, second=59)
                    break
                except ValueError:
                    continue
            data['until'] = parsed
    if data['freq'] is None:
        data['byday'] = []
    return data


def build_rrule(freq=None, interval=1, byday=None, count=None, until=None):
    """يبني نص RRULE من مكوّناته."""
    if not freq:
        return None
    parts = [f'FREQ={str(freq).upper()}']
    if interval and int(interval) > 1:
        parts.append(f'INTERVAL={int(interval)}')
    if byday:
        parts.append('BYDAY=' + ','.join(code for code in byday if code in WEEKDAY_CODES))
    if count:
        parts.append(f'COUNT={int(count)}')
    if until:
        if isinstance(until, datetime) and (until.hour or until.minute or until.second):
            parts.append('UNTIL=' + until.strftime('%Y%m%dT%H%M%S'))
        elif isinstance(until, (date, datetime)):
            parts.append('UNTIL=' + until.strftime('%Y%m%d'))
        else:
            parts.append(f'UNTIL={until}')
    return ';'.join(parts)


def rrule_from_preset(preset, base_date):
    """يحوّل الاختيار العربي في الواجهة إلى RRULE، مع يوم الأسبوع المناسب."""
    code = WEEKDAY_CODES[base_date.weekday()]
    return {
        'يومياً': 'FREQ=DAILY',
        'أسبوعياً': f'FREQ=WEEKLY;BYDAY={code}',
        'كل أسبوعين': f'FREQ=WEEKLY;INTERVAL=2;BYDAY={code}',
        'شهرياً': 'FREQ=MONTHLY',
        'سنوياً': 'FREQ=YEARLY',
    }.get(preset)


def rrule_to_preset(rrule):
    parsed = parse_rrule(rrule)
    if not parsed['freq']:
        return 'بدون تكرار'
    if parsed['freq'] == 'DAILY':
        return 'يومياً'
    if parsed['freq'] == 'WEEKLY':
        return 'كل أسبوعين' if parsed['interval'] > 1 else 'أسبوعياً'
    if parsed['freq'] == 'MONTHLY':
        return 'شهرياً'
    if parsed['freq'] == 'YEARLY':
        return 'سنوياً'
    return 'بدون تكرار'


def add_months(value, months):
    """يضيف شهورًا مع ضبط آخر الشهر (31 يناير -> 28/29 فبراير)."""
    month_index = value.year * 12 + (value.month - 1) + int(months)
    year, month = divmod(month_index, 12)
    month += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _occurrence_dates(base_start, rule, range_end):
    """يولّد بدايات التكرار (datetime) حتى نهاية النطاق، مع احترام COUNT/UNTIL."""
    freq = rule['freq']
    interval = rule['interval']
    count = rule['count']
    until = rule['until']
    if not freq:
        return
    produced = 0
    max_iterations = 20000
    if freq == 'DAILY':
        current = base_start
        while current <= range_end and produced < max_iterations:
            if count is not None and produced >= count:
                break
            if until and current > until:
                break
            yield current
            produced += 1
            current += timedelta(days=interval)
        return
    if freq == 'WEEKLY':
        if rule['byday']:
            week_start = base_start - timedelta(days=base_start.weekday())
            cursor = week_start
            while cursor <= range_end and produced < max_iterations:
                for code in WEEKDAY_CODES:
                    if code not in rule['byday']:
                        continue
                    offset = WEEKDAY_CODES.index(code)
                    current = cursor + timedelta(days=offset)
                    if current < base_start or current > range_end:
                        continue
                    if count is not None and produced >= count:
                        return
                    if until and current > until:
                        return
                    yield current
                    produced += 1
                cursor += timedelta(days=7 * interval)
            return
        current = base_start
        while current <= range_end and produced < max_iterations:
            if count is not None and produced >= count:
                break
            if until and current > until:
                break
            yield current
            produced += 1
            current += timedelta(days=7 * interval)
        return
    if freq == 'MONTHLY':
        current = base_start
        while current <= range_end and produced < max_iterations:
            if count is not None and produced >= count:
                break
            if until and current > until:
                break
            yield current
            produced += 1
            current = add_months(base_start, produced * interval)
        return
    if freq == 'YEARLY':
        current = base_start
        while current <= range_end and produced < max_iterations:
            if count is not None and produced >= count:
                break
            if until and current > until:
                break
            yield current
            produced += 1
            try:
                current = base_start.replace(year=base_start.year + produced * interval)
            except ValueError:
                current = base_start.replace(year=base_start.year + produced * interval, day=28)
        return


def _override_key(occurrence_date):
    return occurrence_date.isoformat()


def expand_occurrences(base_start, duration, rrule_text, range_start, range_end,
                       exdates=None, overrides=None):
    """يعيد قائمة بالم appearances داخل النطاق [range_start, range_end).

    كل عنصر: {'start': datetime, 'end': datetime, 'occurrence_date': date, 'override': dict|None}
    """
    if base_start is None:
        return []
    range_start = range_start or datetime.combine(date.today(), time.min)
    range_end = range_end or (range_start + timedelta(days=31))
    duration = duration if duration is not None else timedelta(0)
    excluded = set()
    for value in (exdates or []):
        try:
            excluded.add(date.fromisoformat(str(value)[:10]).isoformat())
        except ValueError:
            continue
    override_map = overrides if isinstance(overrides, dict) else {}
    rule = parse_rrule(rrule_text)
    if not rule['freq']:
        if base_start < range_end and (base_start + duration > range_start or
                                        (duration == timedelta(0) and base_start >= range_start)):
            key = _override_key(base_start.date())
            override = override_map.get(key)
            if override and override.get('cancelled'):
                return []
            start = base_start
            end = base_start + duration
            if override:
                start, end = _apply_override(start, end, override)
            return [{'start': start, 'end': end, 'occurrence_date': start.date(),
                     'rule_date': base_start.date(), 'override': override}]
        return []
    results = []
    for current in _occurrence_dates(base_start, rule, range_end):
        occurrence_date = current.date()
        if occurrence_date.isoformat() in excluded:
            continue
        override = override_map.get(_override_key(occurrence_date))
        if override and override.get('cancelled'):
            continue
        start, end = current, current + duration
        if override:
            start, end = _apply_override(start, end, override)
        if end <= range_start or start >= range_end:
            # المواعيد الصفرية (طول اليوم) تُقبل إذا كان تاريخها داخل النطاق.
            if not (start == end and range_start <= start < range_end):
                continue
        results.append({'start': start, 'end': end, 'occurrence_date': start.date(),
                        'rule_date': occurrence_date, 'override': override})
    return results


def _apply_override(start, end, override):
    """يطبّق استثناء موعد واحد على بدايته ونهايته (قد يشمل نقل اليوم)."""
    if not isinstance(override, dict):
        return start, end
    duration = end - start
    new_start = start
    if override.get('date'):
        try:
            moved = date.fromisoformat(str(override['date'])[:10])
            new_start = new_start.replace(year=moved.year, month=moved.month, day=moved.day)
        except (TypeError, ValueError):
            pass
    if override.get('start'):
        minutes = parse_hhmm(override['start'])
        if minutes is not None:
            new_start = new_start.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)
    new_end = new_start + duration
    if override.get('end'):
        minutes = parse_hhmm(override['end'])
        if minutes is not None:
            new_end = new_start.replace(hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0)
            if new_end <= new_start:
                new_end = new_start + timedelta(minutes=15)
    if override.get('all_day'):
        new_start = new_start.replace(hour=0, minute=0, second=0, microsecond=0)
        new_end = new_start
    return new_start, new_end


# ---------------------------------------------------------------------------
# توزيع المواعيد المتداخلة في أعمدة
# ---------------------------------------------------------------------------
def layout_overlaps(events):
    """يوزّع المواعيد المتداخلة على مسارات ويعيد أقصى عدد مسارات.

    كل عنصر يجب أن يحتوي start_min و end_min (دقائق من منتصف الليل).
    """
    ordered = sorted(events, key=lambda item: (item.get('start_min', 0), item.get('end_min', 0)))
    groups = []
    group = []
    group_end = None
    for item in ordered:
        start = item.get('start_min', 0)
        end = max(item.get('end_min', start + 15), start + 1)
        if group and start >= group_end:
            groups.append(group)
            group = []
            group_end = None
        group.append(item)
        group_end = end if group_end is None else max(group_end, end)
    if group:
        groups.append(group)
    max_lanes = 1
    for overlap in groups:
        lane_ends = []
        for item in overlap:
            start = item.get('start_min', 0)
            end = max(item.get('end_min', start + 15), start + 1)
            lane = next((index for index, lane_end in enumerate(lane_ends) if lane_end <= start), len(lane_ends))
            if lane == len(lane_ends):
                lane_ends.append(end)
            else:
                lane_ends[lane] = end
            item['lane'] = lane
        for item in overlap:
            item['lanes'] = len(lane_ends)
        max_lanes = max(max_lanes, len(lane_ends))
    return max_lanes


def overlaps(start_a, end_a, start_b, end_b):
    return start_a < end_b and start_b < end_a


def format_minutes_range(start_minutes, end_minutes):
    return f'{minutes_to_hhmm(start_minutes)}–{minutes_to_hhmm(end_minutes)}'


def clamp_date(value, low, high):
    return max(low, min(high, value))


def parse_json_list(value):
    try:
        data = json.loads(value) if value else []
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


def parse_json_dict(value):
    try:
        data = json.loads(value) if value else {}
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}
