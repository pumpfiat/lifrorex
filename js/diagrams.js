const GLOSSARY_DIAGRAMS = {
  candlestick: () => `
      <svg viewBox="0 0 260 150" role="img" aria-label="Candlestick diagram">
      <!-- Price axis -->
      <line x1="48" y1="12" x2="48" y2="138"
            stroke="var(--border)" stroke-width="1"/>

      <!-- Main candle -->
      <line x1="105" y1="18" x2="105" y2="132"
            stroke="var(--font-dim)" stroke-width="3"
            stroke-linecap="round"/>

      <rect x="82" y="48" width="46" height="58" rx="2"
            fill="var(--good)" fill-opacity=".18"
            stroke="var(--good)" stroke-width="2"/>

      <!-- High / Low -->
      <text x="28" y="21"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="end">HIGH</text>

      <text x="28" y="137"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="end">LOW</text>

      <!-- Body label -->
      <line x1="128" y1="77" x2="164" y2="77"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="170" y="81"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            font-weight="600">BODY</text>

      <text x="170" y="95"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">open → close</text>

      <!-- Upper wick -->
      <line x1="105" y1="18" x2="150" y2="18"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="156" y="22"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)">upper wick</text>

      <!-- Lower wick -->
      <line x1="105" y1="132" x2="150" y2="132"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="156" y="136"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)">lower wick</text>

      <!-- Direction marker -->
      <text x="105" y="146"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)"
            text-anchor="middle">BULLISH</text>
    </svg>
  `,

  body: () => `
    <svg viewBox="0 0 260 150" role="img" aria-label="Candlestick body showing open and close prices">
      <line x1="70" y1="15" x2="70" y2="135"
            stroke="var(--font-dim)" stroke-width="2"/>

      <rect x="48" y="42" width="44" height="58" rx="2"
            fill="var(--good)" fill-opacity=".18"
            stroke="var(--good)" stroke-width="2"/>

      <!-- Open -->
      <line x1="35" y1="100" x2="48" y2="100"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="30" y="104"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="end">OPEN</text>

      <!-- Close -->
      <line x1="92" y1="42" x2="105" y2="42"
            stroke="var(--good)" stroke-width="1.5"/>

      <text x="111" y="46"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--good)">CLOSE</text>

      <!-- Body explanation -->
      <text x="145" y="62"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            font-weight="600">CANDLE BODY</text>

      <text x="145" y="80"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">The distance between</text>

      <text x="145" y="94"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">open and close.</text>

      <!-- Direction -->
      <path d="M70 118 L70 108"
            stroke="var(--good)"
            stroke-width="2"
            stroke-linecap="round"/>

      <text x="70" y="132"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)"
            text-anchor="middle">PRICE ROSE</text>
    </svg>
  `,

  wick: () => `
    <svg viewBox="0 0 260 150" role="img" aria-label="Candlestick showing upper and lower wicks">
      <!-- Candle -->
      <line x1="78" y1="15" x2="78" y2="135"
            stroke="var(--font-dim)" stroke-width="3"
            stroke-linecap="round"/>

      <rect x="53" y="48" width="50" height="54" rx="2"
            fill="var(--font-dim)" fill-opacity=".12"
            stroke="var(--font-dim)" stroke-width="2"/>

      <!-- Upper wick -->
      <line x1="103" y1="25" x2="150" y2="25"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="156" y="29"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font)"
            font-weight="600">UPPER WICK</text>

      <text x="156" y="43"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">price traded higher</text>

      <!-- Lower wick -->
      <line x1="103" y1="125" x2="150" y2="125"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="156" y="129"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font)"
            font-weight="600">LOWER WICK</text>

      <text x="156" y="143"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">price traded lower</text>

      <!-- Body -->
      <text x="20" y="78"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="end">BODY</text>

      <line x1="26" y1="75" x2="53" y2="75"
            stroke="var(--font-dim)" stroke-width="1"/>
    </svg>
  `,

  doji: () => `
    <svg viewBox="0 0 260 150" role="img" aria-label="Doji candlestick showing nearly equal open and close">
      <!-- Wick -->
      <line x1="78" y1="18" x2="78" y2="132"
            stroke="var(--font-dim)" stroke-width="3"
            stroke-linecap="round"/>

      <!-- Tiny body -->
      <line x1="50" y1="75" x2="106" y2="75"
            stroke="var(--primary)" stroke-width="4"
            stroke-linecap="round"/>

      <!-- Labels -->
      <line x1="106" y1="75" x2="145" y2="75"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="151" y="70"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            font-weight="600">OPEN ≈ CLOSE</text>

      <text x="151" y="86"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">little net movement</text>

      <!-- Wick labels -->
      <text x="78" y="12"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="middle">HIGH</text>

      <text x="78" y="146"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="middle">LOW</text>

      <text x="78" y="108"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--primary)"
            text-anchor="middle">DOJI</text>
    </svg>
  `,

  bullish: () => `
    <svg viewBox="0 0 260 150" role="img" aria-label="Bullish candlestick showing price closing above its open">
      <!-- Candle -->
      <line x1="65" y1="22" x2="65" y2="125"
            stroke="var(--good)" stroke-width="3"/>

      <rect x="40" y="52" width="50" height="52" rx="2"
            fill="var(--good)" fill-opacity=".18"
            stroke="var(--good)" stroke-width="2"/>

      <!-- Open / close -->
      <line x1="27" y1="104" x2="40" y2="104"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="22" y="108"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="end">OPEN</text>

      <line x1="90" y1="52" x2="103" y2="52"
            stroke="var(--good)" stroke-width="1.5"/>

      <text x="109" y="56"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)">CLOSE</text>

      <!-- Direction -->
      <path d="M165 112 V42 M165 42 L151 56 M165 42 L179 56"
            fill="none"
            stroke="var(--good)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <text x="190" y="48"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            font-weight="600">BULLISH</text>

      <text x="190" y="64"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">close above open</text>

      <text x="165" y="135"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)"
            text-anchor="middle">BUYERS DOMINATED</text>
    </svg>
  `,

  bearish: () => `
    <svg viewBox="0 0 260 150" role="img" aria-label="Bearish candlestick showing price closing below its open">
      <!-- Candle -->
      <line x1="65" y1="22" x2="65" y2="125"
            stroke="var(--bad)" stroke-width="3"/>

      <rect x="40" y="48" width="50" height="52" rx="2"
            fill="var(--bad)" fill-opacity=".14"
            stroke="var(--bad)" stroke-width="2"/>

      <!-- Open -->
      <line x1="27" y1="48" x2="40" y2="48"
            stroke="var(--font-dim)" stroke-width="1.5"/>

      <text x="22" y="52"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="end">OPEN</text>

      <!-- Close -->
      <line x1="90" y1="100" x2="103" y2="100"
            stroke="var(--bad)" stroke-width="1.5"/>

      <text x="109" y="104"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--bad)">CLOSE</text>

      <!-- Direction -->
      <path d="M165 38 V108 M165 108 L151 94 M165 108 L179 94"
            fill="none"
            stroke="var(--bad)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <text x="190" y="55"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            font-weight="600">BEARISH</text>

      <text x="190" y="71"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">close below open</text>

      <text x="165" y="135"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--bad)"
            text-anchor="middle">SELLERS DOMINATED</text>
    </svg>
  `,

  support: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Price repeatedly bouncing from a support zone">
      <!-- Price path -->
      <path d="M12 40
               L42 108
               L68 55
               L96 112
               L126 62
               L154 108
               L188 70
               L218 94
               L252 48"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Support zone -->
      <rect x="8" y="103" width="264" height="18"
            fill="var(--good)"
            fill-opacity=".08"/>

      <line x1="8" y1="112" x2="272" y2="112"
            stroke="var(--good)"
            stroke-width="2"
            stroke-dasharray="6 4"/>

      <!-- Reaction points -->
      <circle cx="42" cy="108" r="4"
              fill="var(--good)"/>

      <circle cx="96" cy="112" r="4"
              fill="var(--good)"/>

      <circle cx="154" cy="108" r="4"
              fill="var(--good)"/>

      <!-- Label -->
      <line x1="190" y1="112" x2="190" y2="135"
            stroke="var(--font-dim)" stroke-width="1"/>

      <text x="190" y="148"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            text-anchor="middle"
            font-weight="600">SUPPORT ZONE</text>
    </svg>
  `,

  resistance: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Price repeatedly rejecting from a resistance zone">
      <!-- Price path -->
      <path d="M12 112
               L42 52
               L70 105
               L98 50
               L126 104
               L154 48
               L184 92
               L218 58
               L252 105"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Resistance zone -->
      <rect x="8" y="40" width="264" height="18"
            fill="var(--bad)"
            fill-opacity=".08"/>

      <line x1="8" y1="49" x2="272" y2="49"
            stroke="var(--bad)"
            stroke-width="2"
            stroke-dasharray="6 4"/>

      <!-- Rejection points -->
      <circle cx="42" cy="52" r="4"
              fill="var(--bad)"/>

      <circle cx="98" cy="50" r="4"
              fill="var(--bad)"/>

      <circle cx="154" cy="48" r="4"
              fill="var(--bad)"/>

      <line x1="190" y1="49" x2="190" y2="27"
            stroke="var(--font-dim)" stroke-width="1"/>

      <text x="190" y="18"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            text-anchor="middle"
            font-weight="600">RESISTANCE ZONE</text>
    </svg>
  `,

  breakout: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Price breaking above resistance">
      <!-- Resistance -->
      <line x1="12" y1="88" x2="190" y2="88"
            stroke="var(--font-dim)"
            stroke-width="2"
            stroke-dasharray="6 4"/>

      <!-- Consolidation -->
      <path d="M12 120
               L35 102
               L55 116
               L76 98
               L98 112
               L120 96
               L142 108
               L164 91"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Breakout -->
      <path d="M164 91
               L184 78
               L202 54
               L225 32
               L258 15"
            fill="none"
            stroke="var(--good)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Breakout point -->
      <circle cx="184" cy="78" r="5"
              fill="var(--good)"/>

      <!-- Arrow -->
      <path d="M225 42 L225 18
               M225 18 L217 26
               M225 18 L233 26"
            fill="none"
            stroke="var(--good)"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <text x="70" y="82"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)">RESISTANCE</text>

      <text x="205" y="72"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--good)"
            font-weight="600">BREAKOUT</text>

      <text x="205" y="87"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)">price moves beyond level</text>
    </svg>
  `,

  pullback: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Uptrend followed by a temporary pullback">
      <!-- Main trend -->
      <path d="M12 126
               L62 72
               L92 98
               L136 50
               L170 76
               L218 30
               L260 18"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Trend direction -->
      <path d="M230 45 L230 18
               M230 18 L222 26
               M230 18 L238 26"
            fill="none"
            stroke="var(--good)"
            stroke-width="2"
            stroke-linecap="round"/>

      <!-- Pullback marker -->
      <circle cx="92" cy="98" r="5"
              fill="var(--font-dim)"/>

      <line x1="92" y1="98" x2="92" y2="132"
            stroke="var(--font-dim)"
            stroke-width="1.5"/>

      <text x="92" y="147"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            text-anchor="middle"
            font-weight="600">PULLBACK</text>

      <text x="92" y="158"
            font-family="Noto Sans, sans-serif"
            font-size="8"
            fill="var(--font-dim)"
            text-anchor="middle">temporary move against trend</text>
    </svg>
  `,

  trend: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Uptrend showing higher highs and higher lows">
      <!-- Trend -->
      <path d="M12 126
               L46 84
               L72 108
               L108 66
               L136 94
               L174 48
               L204 76
               L248 25"
            fill="none"
            stroke="var(--primary)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Higher lows -->
      <circle cx="72" cy="108" r="4" fill="var(--good)"/>
      <circle cx="136" cy="94" r="4" fill="var(--good)"/>
      <circle cx="204" cy="76" r="4" fill="var(--good)"/>

      <!-- Higher highs -->
      <circle cx="46" cy="84" r="4" fill="var(--primary)"/>
      <circle cx="108" cy="66" r="4" fill="var(--primary)"/>
      <circle cx="174" cy="48" r="4" fill="var(--primary)"/>

      <!-- Labels -->
      <text x="48" y="72"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--primary)"
            text-anchor="middle">HH</text>

      <text x="74" y="124"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)"
            text-anchor="middle">HL</text>

      <text x="108" y="54"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--primary)"
            text-anchor="middle">HH</text>

      <text x="138" y="110"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--good)"
            text-anchor="middle">HL</text>

      <!-- Trend label -->
      <text x="210" y="145"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--font)"
            text-anchor="middle"
            font-weight="600">UPTREND</text>

      <text x="210" y="157"
            font-family="Noto Sans, sans-serif"
            font-size="8"
            fill="var(--font-dim)"
            text-anchor="middle">higher highs + higher lows</text>
    </svg>
  `,

  spread: () => `
    <svg viewBox="0 0 280 150" role="img" aria-label="Bid and ask prices with the spread between them">
      <!-- Price ladder -->
      <line x1="55" y1="30" x2="55" y2="120"
            stroke="var(--border)"
            stroke-width="1"/>

      <!-- Bid -->
      <line x1="75" y1="48" x2="235" y2="48"
            stroke="var(--bad)"
            stroke-width="3"/>

      <text x="75" y="36"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--bad)"
            font-weight="600">BID</text>

      <text x="235" y="36"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="end">1.0850</text>

      <!-- Ask -->
      <line x1="75" y1="102" x2="235" y2="102"
            stroke="var(--good)"
            stroke-width="3"/>

      <text x="75" y="90"
            font-family="Noto Sans, sans-serif"
            font-size="11"
            fill="var(--good)"
            font-weight="600">ASK</text>

      <text x="235" y="90"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="end">1.0852</text>

      <!-- Spread bracket -->
      <line x1="250" y1="48" x2="250" y2="102"
            stroke="var(--primary)"
            stroke-width="2"/>

      <line x1="244" y1="48" x2="256" y2="48"
            stroke="var(--primary)"
            stroke-width="2"/>

      <line x1="244" y1="102" x2="256" y2="102"
            stroke="var(--primary)"
            stroke-width="2"/>

      <text x="264" y="78"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--primary)"
            font-weight="600">2 pips</text>

      <text x="140" y="136"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)"
            text-anchor="middle">SPREAD = ASK − BID</text>
    </svg>
  `,

  long: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Long position showing entry, target and upward profit direction">
      <!-- Price path -->
      <path d="M25 125
               L65 108
               L100 115
               L140 72
               L178 82
               L220 32"
            fill="none"
            stroke="var(--primary)"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Entry -->
      <line x1="100" y1="115" x2="250" y2="115"
            stroke="var(--font-dim)"
            stroke-width="1"
            stroke-dasharray="5 4"/>

      <text x="255" y="119"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)">ENTRY</text>

      <!-- Target -->
      <line x1="178" y1="82" x2="250" y2="82"
            stroke="var(--good)"
            stroke-width="2"/>

      <text x="255" y="86"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--good)">TARGET</text>

      <!-- Direction arrow -->
      <path d="M100 100 L100 45
               M100 45 L91 54
               M100 45 L109 54"
            fill="none"
            stroke="var(--good)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <text x="100" y="28"
            font-family="Noto Sans, sans-serif"
            font-size="12"
            fill="var(--good)"
            text-anchor="middle"
            font-weight="600">LONG</text>

      <text x="100" y="151"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="middle">profit if price rises</text>
    </svg>
  `,

  short: () => `
    <svg viewBox="0 0 280 160" role="img" aria-label="Short position showing entry, target and downward profit direction">
      <!-- Price path -->
      <path d="M25 35
               L65 52
               L100 44
               L140 88
               L178 76
               L220 128"
            fill="none"
            stroke="var(--primary)"
            stroke-width="2.5"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <!-- Entry -->
      <line x1="100" y1="44" x2="250" y2="44"
            stroke="var(--font-dim)"
            stroke-width="1"
            stroke-dasharray="5 4"/>

      <text x="255" y="48"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--font-dim)">ENTRY</text>

      <!-- Target -->
      <line x1="178" y1="76" x2="250" y2="76"
            stroke="var(--good)"
            stroke-width="2"/>

      <text x="255" y="80"
            font-family="Noto Sans, sans-serif"
            font-size="10"
            fill="var(--good)">TARGET</text>

      <!-- Direction arrow -->
      <path d="M100 58 L100 113
               M100 113 L91 104
               M100 113 L109 104"
            fill="none"
            stroke="var(--bad)"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>

      <text x="100" y="28"
            font-family="Noto Sans, sans-serif"
            font-size="12"
            fill="var(--bad)"
            text-anchor="middle"
            font-weight="600">SHORT</text>

      <text x="100" y="151"
            font-family="Noto Sans, sans-serif"
            font-size="9"
            fill="var(--font-dim)"
            text-anchor="middle">profit if price falls</text>
    </svg>
  `
};

function renderGlossaryDiagram(term) {
  const diagram = GLOSSARY_DIAGRAMS[term.slug];
  return diagram ? diagram() : null;
}
