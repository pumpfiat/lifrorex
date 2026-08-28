const CATEGORY_NAMES = ['All', 'Forex Basics', 'Trading', 'Analysis', 'Risk Management'];
const LETTERS = '#ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
let glossaryTerms = [];
let selectedCategory = 'All';
let selectedTerm = null;

const byTerm = (a, b) => a.term.localeCompare(b.term);
const escapeHtml = value => String(value).replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[char]));

function filteredTerms(){
  const query = document.getElementById('glossarySearch').value.trim().toLowerCase();
  return glossaryTerms.filter(term => {
    const matchesCategory = selectedCategory === 'All' || term.category === selectedCategory || (selectedCategory === 'Analysis' && ['Technical Analysis', 'Fundamental Analysis'].includes(term.category));
    const haystack = `${term.term} ${term.shortDefinition} ${term.category}`.toLowerCase();
    return matchesCategory && (!query || haystack.includes(query));
  }).sort(byTerm);
}

function renderCategories(){
  document.getElementById('categoryFilters').innerHTML = CATEGORY_NAMES.map(category => `<button type="button" class="glossary-tab${category === selectedCategory ? ' active' : ''}" data-category="${escapeHtml(category)}">${escapeHtml(category)}</button>`).join('');
  document.querySelectorAll('.glossary-tab').forEach(button => button.addEventListener('click', () => {
    selectedCategory = button.dataset.category;
    renderCategories();
    renderResults();
  }));
}

function renderAlphabet(terms){
  const available = new Set(terms.map(term => term.term[0].toUpperCase()));
  document.getElementById('alphabetNav').innerHTML = LETTERS.map(letter => {
    const enabled = available.has(letter) || (letter === '#' && terms.some(term => !/[A-Z]/i.test(term.term[0])));
    return `<a class="alphabet-letter${enabled ? '' : ' disabled'}"${enabled ? ` href="#letter-${letter === '#' ? 'number' : letter.toLowerCase()}"` : ''}>${letter}</a>`;
  }).join('');
}

function renderResults(){
  const terms = filteredTerms();
  renderAlphabet(terms);
  const groups = terms.reduce((result, term) => {
    const letter = /^[A-Z]/i.test(term.term) ? term.term[0].toUpperCase() : '#';
    (result[letter] ||= []).push(term);
    return result;
  }, {});
  const letters = Object.keys(groups).sort((a, b) => a === '#' ? -1 : b === '#' ? 1 : a.localeCompare(b));
  const results = document.getElementById('glossaryResults');
  if (!terms.length) {
    results.innerHTML = '<div class="glossary-empty"><h2>No terms found.</h2><p>Try another search or reset the category filter.</p></div>';
    return;
  }
  results.innerHTML = `<div class="glossary-result-count">${terms.length} terms</div>${letters.map(letter => `<section class="term-group" id="letter-${letter === '#' ? 'number' : letter.toLowerCase()}"><h2>${letter}</h2><div class="term-list">${groups[letter].map(renderTerm).join('')}</div></section>`).join('')}`;
  results.querySelectorAll('.term-row').forEach(row => row.addEventListener('click', () => showDetail(row.dataset.slug)));
  if (selectedTerm && terms.some(term => term.slug === selectedTerm)) showDetail(selectedTerm, false);
}

function renderTerm(term){
  return `<button type="button" class="term-row${selectedTerm === term.slug ? ' selected' : ''}" data-slug="${escapeHtml(term.slug)}"><span class="term-row-name">${escapeHtml(term.term)}</span><span class="term-row-definition">${escapeHtml(term.shortDefinition)}</span><span class="term-row-category">${escapeHtml(term.category)}</span><span class="term-row-arrow">›</span></button>`;
}

function showDetail(slug, rerender = true){
  const term = glossaryTerms.find(item => item.slug === slug);
  if (!term) return;
  selectedTerm = slug;
  const diagram = renderGlossaryDiagram(term);
  document.getElementById('termDetail').innerHTML = `<div class="detail-content"><div class="section-label">${escapeHtml(term.category)}</div><h2>${escapeHtml(term.term)}</h2><p class="detail-short">${escapeHtml(term.shortDefinition)}</p>${diagram ? `<div class="detail-diagram">${diagram}</div>` : ''}<p>${escapeHtml(term.longDefinition)}</p><div class="detail-example"><strong>Example</strong><p>${escapeHtml(term.example)}</p></div><a class="detail-learn-link" href="learn.html">Learn more in Learn</a><div class="detail-related"><strong>Related terms</strong><div>${term.relatedTerms.map(related => { const match = glossaryTerms.find(item => item.slug === related); return match ? `<button type="button" data-related="${escapeHtml(match.slug)}">${escapeHtml(match.term)}</button>` : ''; }).join('')}</div></div></div>`;
  document.querySelectorAll('[data-related]').forEach(button => button.addEventListener('click', () => { showDetail(button.dataset.related); document.querySelector(`[data-slug="${button.dataset.related}"]`)?.focus(); }));
  if (rerender) renderResults();
}

async function loadGlossary(){
  const response = await fetch('data/glossary.json');
  glossaryTerms = await response.json();
  renderCategories();
  renderResults();
}

document.addEventListener('DOMContentLoaded', () => {
  const search = document.getElementById('glossarySearch');
  const clear = document.getElementById('clearSearch');
  search.addEventListener('input', () => { renderResults(); clear.hidden = !search.value; });
  clear.addEventListener('click', () => { search.value = ''; clear.hidden = true; search.focus(); renderResults(); });
  clear.hidden = true;
  loadGlossary().catch(() => { document.getElementById('glossaryResults').innerHTML = '<div class="glossary-empty"><h2>Glossary unavailable.</h2><p>Run Liforex from a local web server to load the glossary data.</p></div>'; });
});
