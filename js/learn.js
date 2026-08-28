const ICONS = {
  exchange: '<path d="M4 8h13M14 5l3 3-3 3"/><path d="M20 16H7M10 13l-3 3 3 3"/>',
  pair: '<circle cx="8" cy="12" r="5"/><circle cx="16" cy="12" r="5"/><line x1="12" y1="6" x2="12" y2="18"/>',
  pip: '<circle cx="10" cy="10" r="6"/><line x1="7" y1="10" x2="13" y2="10"/><line x1="14.5" y1="14.5" x2="20" y2="20"/>',
  lot: '<rect x="4" y="10" width="7" height="7" rx="1"/><rect x="13" y="10" width="7" height="7" rx="1"/><rect x="8.5" y="3" width="7" height="7" rx="1"/>',
  leverage: '<line x1="4" y1="17" x2="20" y2="7"/><circle cx="12" cy="12" r="1.8" fill="currentColor" stroke="none"/><line x1="4" y1="17" x2="4" y2="20"/><line x1="20" y1="7" x2="20" y2="4"/>',
  spread: '<rect x="3" y="8" width="7" height="8" rx="1"/><rect x="14" y="8" width="7" height="8" rx="1"/><line x1="10.5" y1="12" x2="13.5" y2="12" stroke-dasharray="1.5 2"/>',
  longshort: '<path d="M7 20V6M4 9l3-3 3 3"/><path d="M17 4v14M14 15l3 3 3-3"/>',
  supportresistance: '<line x1="4" y1="7" x2="20" y2="7"/><line x1="4" y1="17" x2="20" y2="17"/><path d="M5 12c3 0 3-5 6-5s3 10 6 10" stroke-dasharray="2 2"/>',
  trendrange: '<path d="M3 17l4-4 3 3 6-8 5 5"/>',
  candlestick: '<line x1="6" y1="4" x2="6" y2="20"/><rect x="4" y="8" width="4" height="6"/><line x1="12" y1="2" x2="12" y2="20"/><rect x="10" y="6" width="4" height="10"/><line x1="18" y1="6" x2="18" y2="20"/><rect x="16" y="10" width="4" height="6"/>',
  scale: '<line x1="12" y1="3" x2="12" y2="21"/><line x1="5" y1="7" x2="19" y2="7"/><path d="M5 7l-3 6a3 3 0 0 0 6 0z"/><path d="M19 7l-3 6a3 3 0 0 0 6 0z"/>',
  riskreward: '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3"/><line x1="12" y1="1" x2="12" y2="5"/>',
  shield: '<path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6z"/>',
  brain: '<circle cx="12" cy="11" r="7"/><path d="M8 11c1-2 2-2 2 0s1 2 2 0 2-2 2 0"/><line x1="12" y1="18" x2="12" y2="21"/>',
  link: '<path d="M9 15l6-6"/><path d="M8 12l-2 2a3 3 0 0 0 4 4l2-2"/><path d="M16 12l2-2a3 3 0 0 0-4-4l-2 2"/>',
  clock: '<circle cx="12" cy="12" r="8"/><line x1="12" y1="12" x2="12" y2="7"/><line x1="12" y1="12" x2="16" y2="14"/>',
  target: '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none"/>',
  flame: '<path d="M12 3c1 3-3 4-3 8a3 3 0 0 0 6 0c0-1-1-2-1-3 2 1 3 3 3 5a5 5 0 0 1-10 0c0-4 3-6 5-10z"/>',
  wrench: '<path d="M15 4a4 4 0 0 0-5.3 4.6L4 14.3V18h3.7l5.7-5.7A4 4 0 0 0 18 8l-3 3-2-2z"/>',
  people: '<circle cx="8" cy="8" r="3"/><circle cx="16" cy="9" r="2.6"/><path d="M2.5 19c.5-3.5 3-5.5 5.5-5.5s5 2 5.5 5.5"/><path d="M14 14c2 .2 4 1.8 4.5 5"/>'
};

function svgIcon(name){
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ''}</svg>`;
}

function getDoneLessons(){
  try{ return JSON.parse(localStorage.getItem('liforex_lessons_done') || '[]'); }
  catch(e){ return []; }
}
function setDoneLessons(list){
  localStorage.setItem('liforex_lessons_done', JSON.stringify(list));
}
function isDone(id){
  return getDoneLessons().includes(id);
}
function toggleDone(id){
  const done = getDoneLessons();
  const i = done.indexOf(id);
  if(i === -1) done.push(id); else done.splice(i, 1);
  setDoneLessons(done);
}

let sections = [];

async function loadLessons(){
  const res = await fetch('data/lessons.json');
  const data = await res.json();
  sections = data.sections;
  render();
}

function allLessonIds(){
  return sections.filter(s => s.style !== 'next').flatMap(s => s.lessons.map(l => l.id));
}

function render(){
  renderSections();
  renderProgress();
}

function renderSections(){
  document.getElementById('lessonSections').innerHTML = sections.map(section => `
    <section class="lesson-section">
      <div class="lesson-section-label">${section.label}</div>
      <div class="tile-grid">
        ${section.lessons.map(l => renderTile(l, section.style)).join('')}
      </div>
    </section>
  `).join('');

  document.querySelectorAll('.lesson-tile[data-href]').forEach(el => {
    el.addEventListener('click', () => { window.location.href = el.dataset.href; });
  });
  document.querySelectorAll('.lesson-tile[data-id]').forEach(el => {
    el.addEventListener('click', () => openModal(el.dataset.id));
  });
}

function renderTile(l, sectionStyle){
  const done = sectionStyle !== 'next' && isDone(l.id);
  const classes = ['lesson-tile'];
  if(sectionStyle === 'next') classes.push('next');
  else if(l.start) classes.push('active');
  if(done) classes.push('done');
  const attr = l.href ? `data-href="${l.href}"` : `data-id="${l.id}"`;
  return `
    <button type="button" class="${classes.join(' ')}" ${attr}>
      <span class="tile-icon">${svgIcon(l.icon)}</span>
      <span>
        <h3>${l.title}</h3>
        <p>${l.subtitle}</p>
      </span>
    </button>
  `;
}

function renderProgress(){
  const ids = allLessonIds();
  const done = getDoneLessons().filter(id => ids.includes(id));
  const pct = ids.length ? Math.round((done.length / ids.length) * 100) : 0;
  document.getElementById('progressText').textContent = `${done.length} of ${ids.length} topics complete`;
  document.getElementById('progressBar').style.width = pct + '%';
  document.getElementById('progressPill').textContent = pct + '%';
}

function findLesson(id){
  for(const s of sections){
    const l = s.lessons.find(x => x.id === id);
    if(l) return l;
  }
  return null;
}

function openModal(id){
  const l = findLesson(id);
  if(!l) return;
  document.getElementById('modalIcon').innerHTML = svgIcon(l.icon);
  document.getElementById('modalTitle').textContent = l.title;
  document.getElementById('modalBody').textContent = l.body;
  updateModalDoneBtn(id);
  document.getElementById('modalDoneBtn').onclick = () => {
    toggleDone(id);
    updateModalDoneBtn(id);
    render();
  };
  document.getElementById('lessonModal').classList.add('show');
}

function updateModalDoneBtn(id){
  const btn = document.getElementById('modalDoneBtn');
  const done = isDone(id);
  btn.textContent = done ? '✓ Marked as complete' : 'Mark as complete';
  btn.className = 'button' + (done ? ' primary' : '');
}

function closeModal(){
  document.getElementById('lessonModal').classList.remove('show');
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('modalClose').addEventListener('click', closeModal);
  document.getElementById('lessonModal').addEventListener('click', e => {
    if(e.target.id === 'lessonModal') closeModal();
  });
  document.addEventListener('keydown', e => {
    if(e.key === 'Escape') closeModal();
  });
  loadLessons();
});
