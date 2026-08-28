const sampleTraders = [
  { name: 'kalu_fx', rating: 1842 },
  { name: 'pipsqueak', rating: 1701 },
  { name: 'marketminded', rating: 1655 },
  { name: 'tundeReads', rating: 1590 },
  { name: 'range_rider', rating: 1488 },
  { name: 'newtoFX', rating: 1320 },
];

document.addEventListener('DOMContentLoaded', () => {
  const you = { name: 'You', rating: getRating(), isYou: true };
  const all = [...sampleTraders, you].sort((a, b) => b.rating - a.rating);

  document.getElementById('leaderboardBody').innerHTML = all.map((t, i) => `
    <tr class="${t.isYou ? 'you' : ''}">
      <td class="rank">${i + 1}</td>
      <td>${t.name}</td>
      <td class="rating">${t.rating}</td>
    </tr>
  `).join('');
});
