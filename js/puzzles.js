let puzzles = [];
let currentPuzzle = null;
let answered = false;

async function loadPuzzles(){
  const res = await fetch('data/puzzles.json');
  puzzles = await res.json();
  pickPuzzle();
}

function pickPuzzle(){
  currentPuzzle = puzzles[Math.floor(Math.random() * puzzles.length)];
  answered = false;
  document.getElementById('puzzleId').textContent = currentPuzzle.id;
  document.getElementById('puzzlePair').innerHTML =
    `${currentPuzzle.pair} <small>${currentPuzzle.frame}</small>`;
  document.getElementById('scenarioText').textContent = currentPuzzle.scenario;
  document.getElementById('resultBox').classList.remove('show');
  document.querySelectorAll('.choice').forEach(b => b.disabled = false);
  drawChart(currentPuzzle.chart);
}

function drawChart(type){
  const svg = document.getElementById('chartSvg');
  const candleSets = {
    breakout:  [40,55,50,65,60,72,68,80,75,90,85,70,95,88,100],
    fakeout:   [50,55,52,60,58,90,75,60,55,58,50,52,48,50,53],
    range:     [55,60,52,58,50,56,53,59,51,57,54,58,52,56,55],
    breakdown: [80,75,78,68,72,60,65,50,55,45,48,38,42,35,40]
  };
  const data = candleSets[type] || candleSets.range;
  const w = 720, h = 280, left = 14, top = 16, bottom = 28;
  const chartH = h - top - bottom, gap = (w-left*2) / data.length;
  const min = Math.min(...data)-8, max = Math.max(...data)+8;
  const y = v => top + (max-v)/(max-min)*chartH;
  let grid='';
  for(let i=0;i<5;i++){ const gy=top+i*(chartH/4); grid += `<line x1="${left}" y1="${gy}" x2="${w-left}" y2="${gy}" stroke="#e3e0dc" stroke-width="1"/>`; }
  let bars='';
  data.forEach((close,i)=>{
    const prev=i===0?close: data[i-1];
    const open=prev + ((i%3)-1)*2.2;
    const high=Math.max(open,close)+3+(i%4);
    const low=Math.min(open,close)-3-(i%3);
    const x=left+i*gap+gap/2;
    const up=close>=open;
    const color=up?'#629924':'#cc3333';
    const bodyY=Math.min(y(open),y(close));
    const bodyH=Math.max(3,Math.abs(y(open)-y(close)));
    bars += `<line x1="${x}" y1="${y(high)}" x2="${x}" y2="${y(low)}" stroke="${color}" stroke-width="1.2"/>`;
    bars += `<rect x="${x-4}" y="${bodyY}" width="8" height="${bodyH}" fill="${color}" rx="1"/>`;
  });
  const lastY=y(data[data.length-1]);
  svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
  svg.innerHTML = `${grid}<line x1="${left}" y1="${lastY}" x2="${w-left}" y2="${lastY}" stroke="#1b78d0" stroke-width="1" stroke-dasharray="4 4" opacity=".7"/>${bars}<text x="${w-left-2}" y="${lastY-5}" fill="#145da8" font-size="10" text-anchor="end">current</text>`;
}

function handleDecision(choice){
  if(answered) return;
  answered = true;
  document.querySelectorAll('.choice').forEach(b => b.disabled = true);

  const ev = currentPuzzle.ev;
  const best = Object.keys(ev).reduce((a, b) => ev[a] > ev[b] ? a : b);
  const correct = choice === best;

  const delta = correct
    ? Math.round(8 + Math.random() * 10)
    : -Math.round(4 + Math.random() * 6);
  setRating(getRating() + delta);

  const title = document.getElementById('resultTitle');
  title.textContent = correct
    ? `Strong choice — ${best.toUpperCase()} was the strongest option in this example (${delta > 0 ? '+' : ''}${delta} rating)`
    : `${best.toUpperCase()} was the strongest option in this example (${delta} rating)`;
  title.className = 'result-title ' + (correct ? 'good' : 'bad');

  const rows = ['buy', 'sell', 'wait'].map(k => {
    let cls = '';
    if(k === best) cls += 'best ';
    if(k === choice) cls += 'chosen';
    const tags = [k === choice ? 'your pick' : null, k === best ? 'best' : null].filter(Boolean).join(', ');
    return `<tr class="${cls.trim()}"><td>${k.toUpperCase()}${tags ? ' (' + tags + ')' : ''}</td><td>${ev[k] >= 0 ? '+' : ''}${ev[k].toFixed(2)}R</td></tr>`;
  }).join('');
  document.getElementById('evTable').innerHTML = rows;
  document.getElementById('explainText').textContent = currentPuzzle.note;
  document.getElementById('resultBox').classList.add('show');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.choice').forEach(btn => {
    btn.addEventListener('click', () => handleDecision(btn.dataset.choice));
  });
  document.getElementById('nextBtn').addEventListener('click', pickPuzzle);
  loadPuzzles();
});
