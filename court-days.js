// ── Court-day calendars for the NY and NJ deadline calculators ──────────────
//
// CourtDays.holiday(date, 'NY'|'NJ')  → { name, projected } or null
// CourtDays.reason(date, j)           → 'Saturday' | 'Sunday' | holiday name | null
// CourtDays.isCourtDay(date, j)
// CourtDays.prevCourtDay(date, j)     → date itself if a court day, else the closest earlier one
// CourtDays.nextCourtDay(date, j)     → date itself if a court day, else the closest later one
// CourtDays.subtractCourtDays(date, n, j) → count back n court days (excludes weekends/holidays)
//
// NY: New York State public holidays observed by the Unified Court System —
//   the federal holidays plus Lincoln's Birthday (Feb 12) and Election Day.
//   A holiday falling on Saturday is treated as observed Friday, Sunday as Monday.
//
// NJ: Inside NJ_OFFICIAL, the exact closures from the Supreme Court's annual
//   "Legal Holidays and Court Recesses" orders (including Judicial College and
//   year-end recess days). Outside it, a rule-based projection (federal holidays
//   + Good Friday + Election Day) flagged as projected — recess days such as
//   Judicial College are not known until the order for that court year issues.

(function (global) {
  const pad = n => String(n).padStart(2, '0');
  const key = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

  function fixedObs(y, m, day) {
    const d = new Date(y, m - 1, day);
    if (d.getDay() === 0) d.setDate(d.getDate() + 1);
    else if (d.getDay() === 6) d.setDate(d.getDate() - 1);
    return d;
  }
  function nthWeekday(y, m, wd, n) {
    const d = new Date(y, m - 1, 1);
    while (d.getDay() !== wd) d.setDate(d.getDate() + 1);
    d.setDate(d.getDate() + 7 * (n - 1));
    return d;
  }
  function lastWeekday(y, m, wd) {
    const d = new Date(y, m, 0);
    while (d.getDay() !== wd) d.setDate(d.getDate() - 1);
    return d;
  }
  function electionDay(y) {            // Tuesday after the first Monday in November
    const d = nthWeekday(y, 11, 1, 1);
    d.setDate(d.getDate() + 1);
    return d;
  }
  function goodFriday(y) {             // anonymous Gregorian Easter algorithm, minus 2 days
    const a = y % 19, b = Math.floor(y / 100), c = y % 100;
    const d = Math.floor(b / 4), e = b % 4, f = Math.floor((b + 8) / 25);
    const g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7;
    const m = Math.floor((a + 11 * h + 22 * l) / 451);
    const month = Math.floor((h + l - 7 * m + 114) / 31);
    const day = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(y, month - 1, day - 2);
  }

  function federal(y) {
    return [
      [fixedObs(y, 1, 1),        "New Year's Day"],
      [nthWeekday(y, 1, 1, 3),   'Martin Luther King Jr. Day'],
      [nthWeekday(y, 2, 1, 3),   "Washington's Birthday"],
      [lastWeekday(y, 5, 1),     'Memorial Day'],
      [fixedObs(y, 6, 19),       'Juneteenth'],
      [fixedObs(y, 7, 4),        'Independence Day'],
      [nthWeekday(y, 9, 1, 1),   'Labor Day'],
      [nthWeekday(y, 10, 1, 2),  'Columbus Day'],
      [fixedObs(y, 11, 11),      'Veterans Day'],
      [nthWeekday(y, 11, 4, 4),  'Thanksgiving'],
      [fixedObs(y, 12, 25),      'Christmas'],
    ];
  }
  const RULES = {
    NY: y => federal(y).concat([
      [fixedObs(y, 2, 12), "Lincoln's Birthday"],
      [electionDay(y),     'Election Day'],
    ]),
    NJ: y => federal(y).concat([
      [goodFriday(y),  'Good Friday'],
      [electionDay(y), 'Election Day'],
    ]),
  };

  // NJ Supreme Court orders: Legal Holidays and Court Recesses (njcourts.gov).
  const NJ_OFFICIAL = {
    from: '2025-07-01',
    through: '2027-06-30',
    days: {
      // 2025–2026 court year
      '2025-07-04': 'Independence Day',
      '2025-09-01': 'Labor Day',
      '2025-10-13': 'Columbus Day',
      '2025-11-04': 'Election Day',
      '2025-11-11': 'Veterans Day',
      '2025-11-24': 'Judicial College recess',
      '2025-11-25': 'Judicial College recess',
      '2025-11-26': 'Judicial College recess',
      '2025-11-27': 'Thanksgiving',
      '2025-11-28': 'Court recess (day after Thanksgiving)',
      '2025-12-25': 'Christmas',
      '2025-12-26': 'Court recess',
      '2025-12-29': 'Court recess',
      '2025-12-30': 'Court recess',
      '2025-12-31': 'Court recess',
      '2026-01-01': "New Year's Day",
      '2026-01-19': 'Martin Luther King Jr. Day',
      '2026-02-16': "Washington's Birthday",
      '2026-04-03': 'Good Friday',
      '2026-05-25': 'Memorial Day',
      '2026-06-19': 'Juneteenth',
      // 2026–2027 court year
      '2026-07-03': 'Independence Day (observed)',
      '2026-09-07': 'Labor Day',
      '2026-10-12': 'Columbus Day',
      '2026-11-03': 'Election Day',
      '2026-11-11': 'Veterans Day',
      '2026-11-23': 'Judicial College recess',
      '2026-11-24': 'Judicial College recess',
      '2026-11-25': 'Judicial College recess',
      '2026-11-26': 'Thanksgiving',
      '2026-12-25': 'Christmas',
      '2026-12-28': 'Court recess',
      '2026-12-29': 'Court recess',
      '2026-12-30': 'Court recess',
      '2026-12-31': 'Court recess',
      '2027-01-01': "New Year's Day",
      '2027-01-18': 'Martin Luther King Jr. Day',
      '2027-02-15': "Washington's Birthday",
      '2027-03-26': 'Good Friday',
      '2027-05-31': 'Memorial Day',
      '2027-06-18': 'Juneteenth (observed)',
    },
  };

  const cache = {};
  function ruleMap(j, y) {
    const id = j + y;
    if (!cache[id]) {
      const m = {};
      // Include neighbours so a Jan 1 holiday observed on Dec 31 is found.
      [y - 1, y, y + 1].forEach(yr => RULES[j](yr).forEach(([d, name]) => {
        if (d.getFullYear() === y) m[key(d)] = name;
      }));
      cache[id] = m;
    }
    return cache[id];
  }

  function holiday(date, j) {
    const k = key(date);
    if (j === 'NJ' && k >= NJ_OFFICIAL.from && k <= NJ_OFFICIAL.through) {
      const name = NJ_OFFICIAL.days[k];
      return name ? { name, projected: false } : null;
    }
    const name = ruleMap(j, date.getFullYear())[k];
    if (!name) return null;
    return { name, projected: j === 'NJ' };
  }

  function reason(date, j) {
    if (date.getDay() === 6) return 'Saturday';
    if (date.getDay() === 0) return 'Sunday';
    const h = holiday(date, j);
    return h ? h.name : null;
  }
  const isCourtDay = (date, j) => reason(date, j) === null;

  function step(date, j, dir) {
    const d = new Date(date);
    while (!isCourtDay(d, j)) d.setDate(d.getDate() + dir);
    return d;
  }
  function subtractCourtDays(date, n, j) {
    const d = new Date(date);
    let left = n;
    while (left > 0) {
      d.setDate(d.getDate() - 1);
      if (isCourtDay(d, j)) left--;
    }
    return d;
  }
  // True when NJ results depend on dates past the last official order loaded.
  const njProjected = date => key(date) > NJ_OFFICIAL.through || key(date) < NJ_OFFICIAL.from;

  global.CourtDays = {
    holiday, reason, isCourtDay, subtractCourtDays, njProjected,
    prevCourtDay: (d, j) => step(d, j, -1),
    nextCourtDay: (d, j) => step(d, j, +1),
    NJ_OFFICIAL_THROUGH: NJ_OFFICIAL.through,
  };
})(window);
