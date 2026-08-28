// Shared across every page: rating display, active nav highlighting.

function getRating(){
  return parseInt(localStorage.getItem('liforex_rating') || '1200');
}
function setRating(r){
  localStorage.setItem('liforex_rating', r);
  renderRating();
}
function renderRating(){
  const el = document.getElementById('ratingDisplay');
  if(el) el.textContent = getRating();
  const home = document.getElementById('homeRating');
  if(home) home.textContent = getRating();
}
renderRating();

// Highlight the current page in the nav based on data-page on <body>
document.addEventListener('DOMContentLoaded', () => {
  const current = document.body.dataset.page;
  const nav = document.querySelector('nav.site-nav');
  if(nav && !nav.querySelector('[data-page="glossary"]')){
    const glossary = document.createElement('a');
    glossary.href = 'glossary.html';
    glossary.dataset.page = 'glossary';
    glossary.textContent = 'Glossary';
    nav.appendChild(glossary);
  }
  document.querySelectorAll('nav.site-nav a').forEach(a => {
    if(a.dataset.page === current) a.classList.add('active');
  });
});
