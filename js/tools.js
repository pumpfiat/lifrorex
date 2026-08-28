function calcPositionSize(){
  const bal = parseFloat(document.getElementById('posBalance').value) || 0;
  const riskPct = parseFloat(document.getElementById('posRisk').value) || 0;
  const stopPips = parseFloat(document.getElementById('posStop').value) || 0;
  const pipValue = parseFloat(document.getElementById('posPipValue').value) || 0;
  const out = document.getElementById('posOutput');
  if(stopPips <= 0 || pipValue <= 0){
    out.innerHTML = 'Enter a stop distance and pip value to calculate.';
    return;
  }
  const riskAmount = bal * (riskPct / 100);
  const lots = riskAmount / (stopPips * pipValue);
  out.innerHTML = `Risking <b>$${riskAmount.toFixed(2)}</b> on a ${stopPips}-pip stop →
    position size ≈ <b>${lots.toFixed(2)} standard lots</b> (${(lots * 10).toFixed(2)} mini lots).`;
}

function calcRR(){
  const entry = parseFloat(document.getElementById('rrEntry').value);
  const stop = parseFloat(document.getElementById('rrStop').value);
  const target = parseFloat(document.getElementById('rrTarget').value);
  const out = document.getElementById('rrOutput');
  if(isNaN(entry) || isNaN(stop) || isNaN(target)){
    out.innerHTML = 'Enter entry, stop, and target prices.';
    return;
  }
  const risk = Math.abs(entry - stop);
  const reward = Math.abs(target - entry);
  if(risk === 0){ out.innerHTML = "Stop can't equal entry."; return; }
  out.innerHTML = `Risk: <b>${risk.toFixed(4)}</b> · Reward: <b>${reward.toFixed(4)}</b> ·
    Risk:Reward = <b>1 : ${(reward / risk).toFixed(2)}</b>`;
}

document.addEventListener('DOMContentLoaded', () => {
  const sessionsCard = [...document.querySelectorAll('.tool-card')].find(card => card.querySelector('h2')?.textContent.trim() === 'Market sessions');
  if(sessionsCard && !sessionsCard.querySelector('a[href="sessions.html"]')){
    const sessionsLink = document.createElement('a');
    sessionsLink.className = 'button';
    sessionsLink.href = 'sessions.html';
    sessionsLink.textContent = 'Open sessions →';
    sessionsCard.appendChild(sessionsLink);
  }
  const linkRow = document.querySelector('.tools-grid + * .link-row') || document.querySelector('.link-row');
  if(linkRow && !linkRow.querySelector('a[href="glossary.html"]')){
    const glossaryLink = document.createElement('a');
    glossaryLink.className = 'button';
    glossaryLink.href = 'glossary.html';
    glossaryLink.textContent = 'Forex Glossary →';
    linkRow.appendChild(glossaryLink);
  }
  ['posBalance','posRisk','posStop','posPipValue'].forEach(id =>
    document.getElementById(id).addEventListener('input', calcPositionSize));
  ['rrEntry','rrStop','rrTarget'].forEach(id =>
    document.getElementById(id).addEventListener('input', calcRR));
  calcPositionSize();
  calcRR();
});
