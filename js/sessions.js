const SESSION_DEFINITIONS = [
  {name: 'Sydney', zone: 'Australia/Sydney'},
  {name: 'Tokyo', zone: 'Asia/Tokyo'},
  {name: 'London', zone: 'Europe/London'},
  {name: 'New York', zone: 'America/New_York'}
];
const DISPLAY_ZONES = [
  ['Local time', Intl.DateTimeFormat().resolvedOptions().timeZone],
  ['UTC', 'UTC'],
  ['London', 'Europe/London'],
  ['New York', 'America/New_York'],
  ['Chicago', 'America/Chicago'],
  ['Denver', 'America/Denver'],
  ['Los Angeles', 'America/Los_Angeles'],
  ['Sao Paulo', 'America/Sao_Paulo'],
  ['Johannesburg', 'Africa/Johannesburg'],
  ['Dubai', 'Asia/Dubai'],
  ['Singapore', 'Asia/Singapore'],
  ['Tokyo', 'Asia/Tokyo'],
  ['Sydney', 'Australia/Sydney']
];

let displayZone = DISPLAY_ZONES[0][1];
const parts = (date, timeZone, options) => Object.fromEntries(new Intl.DateTimeFormat('en-US', {timeZone, ...options}).formatToParts(date).filter(part => part.type !== 'literal').map(part => [part.type, part.value]));
const pad = value => String(value).padStart(2, '0');

function zonedTimeToUtc(year, month, day, hour, timeZone){
  let guess = new Date(Date.UTC(year, month - 1, day, hour));
  for(let i = 0; i < 3; i++){
    const local = parts(guess, timeZone, {year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', hourCycle:'h23', minute:'2-digit'});
    const localAsUtc = Date.UTC(Number(local.year), Number(local.month) - 1, Number(local.day), Number(local.hour), Number(local.minute));
    guess = new Date(guess.getTime() + Date.UTC(year, month - 1, day, hour) - localAsUtc);
  }
  return guess;
}

function selectedDate(date){
  const current = parts(date, displayZone, {year:'numeric', month:'numeric', day:'numeric'});
  return {year:Number(current.year), month:Number(current.month), day:Number(current.day)};
}

function addDays(date, amount){
  const result = new Date(date);
  result.setUTCDate(result.getUTCDate() + amount);
  return result;
}

function sessionWindow(session, date, bounds){
  const local = selectedDate(date);
  const windows = [-1, 0, 1].map(offset => {
    const day = addDays(new Date(Date.UTC(local.year, local.month - 1, local.day)), offset);
    const sessionDate = {year: day.getUTCFullYear(), month: day.getUTCMonth() + 1, day: day.getUTCDate()};
    return {start: zonedTimeToUtc(sessionDate.year, sessionDate.month, sessionDate.day, 9, session.zone), end: zonedTimeToUtc(sessionDate.year, sessionDate.month, sessionDate.day, 17, session.zone)};
  });
  let best = windows[1];
  let bestOverlap = -Infinity;
  for(const w of windows){
    const overlap = Math.min(w.end.getTime(), bounds.end.getTime()) - Math.max(w.start.getTime(), bounds.start.getTime());
    if(overlap > bestOverlap){ bestOverlap = overlap; best = w; }
  }
  return best;
}

function displayDayBounds(date){
  const local = selectedDate(date);
  const start = zonedTimeToUtc(local.year, local.month, local.day, 0, displayZone);
  return {start, end: new Date(start.getTime() + 86400000)};
}

function timelinePosition(date, bounds){
  return ((date.getTime() - bounds.start.getTime()) / (bounds.end.getTime() - bounds.start.getTime())) * 100;
}

function renderClock(date){
  const clock = parts(date, displayZone, {hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23'});
  const dateParts = parts(date, displayZone, {weekday:'long', year:'numeric', month:'long', day:'numeric'});
  document.getElementById('localClock').textContent = `${clock.hour}:${clock.minute}:${clock.second}`;
  document.getElementById('localDate').textContent = `${dateParts.weekday}, ${dateParts.month} ${dateParts.day}, ${dateParts.year}`;
}

function renderSessions(date){
  const rows = document.getElementById('sessionRows');
  const bounds = displayDayBounds(date);
  const windows = SESSION_DEFINITIONS.map(session => sessionWindow(session, date, bounds));
  rows.innerHTML = SESSION_DEFINITIONS.map(session => {
    const sessionIndex = SESSION_DEFINITIONS.indexOf(session);
    const window = windows[sessionIndex];
    const rawStart = timelinePosition(window.start, bounds);
    const rawEnd = timelinePosition(window.end, bounds);
    const start = Math.max(rawStart, 0);
    const end = Math.min(rawEnd, 100);
 
    const isOpen = date >= window.start && date < window.end;
    const width = Math.max(end - start, 1);
    const overlapSegments = windows.map((other, otherIndex) => {
  if(otherIndex === sessionIndex) return '';
  const overlapStart = new Date(Math.max(window.start.getTime(), other.start.getTime()));
  const overlapEnd = new Date(Math.min(window.end.getTime(), other.end.getTime()));
  if(overlapEnd <= overlapStart) return '';
  const overlapLeft = Math.max(timelinePosition(overlapStart, bounds), 0);
  const overlapWidth = Math.min(timelinePosition(overlapEnd, bounds), 100) - overlapLeft;
  return overlapWidth > 0 ? `<i class="session-overlap" style="left:${overlapLeft}%;width:${overlapWidth}%" title="${session.name} and ${SESSION_DEFINITIONS[otherIndex].name} overlap"></i>` : '';
}).join('');

    return `<div class="session-row"><div class="session-label"><strong>${session.name}</strong><span>${session.zone.split('/').pop().replace('_', ' ')}</span></div><div class="session-track">${overlapSegments}<span class="session-open${isOpen ? ' is-open' : ''}" style="left:${start}%;width:${width}%"><b>${isOpen ? 'OPEN' : 'CLOSED'}</b></span></div></div>`;
  }).join('');
  const marker = document.getElementById('nowMarker');
  const plot = document.querySelector('.timeline-plot');
  const track = document.querySelector('.session-track');
  if(plot && track){
    const plotBox = plot.getBoundingClientRect();
    const trackBox = track.getBoundingClientRect();
    const position = timelinePosition(date, bounds) / 100;
    marker.style.left = `${trackBox.left - plotBox.left + (trackBox.width * position)}px`;
  }
}

function render(date = new Date()){
  renderClock(date);
  renderSessions(date);
}

function populateZones(){
  const select = document.getElementById('timezoneSelect');
  const seen = new Set();
  select.innerHTML = DISPLAY_ZONES.filter(([, zone]) => zone && !seen.has(zone) && seen.add(zone)).map(([label, zone]) => `<option value="${zone}">${label} (${zone})</option>`).join('');
  select.value = displayZone;
  select.addEventListener('change', () => { displayZone = select.value; render(); });
}

document.addEventListener('DOMContentLoaded', () => {
  populateZones();
  render();
  setInterval(() => render(), 1000);
});
