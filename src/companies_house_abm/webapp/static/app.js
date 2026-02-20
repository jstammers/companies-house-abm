/* Economy Simulator — frontend logic */
'use strict';

// ── Plotly layout template ────────────────────────────────────────────

const LAYOUT_BASE = {
  paper_bgcolor: 'transparent',
  plot_bgcolor:  'transparent',
  margin:        { t: 8, r: 12, b: 36, l: 52 },
  font:          { family: 'Inter, system-ui, sans-serif', color: '#8b90ad', size: 11 },
  xaxis: {
    gridcolor:    '#2d3148',
    linecolor:    '#2d3148',
    tickcolor:    '#2d3148',
    zeroline:     false,
    title:        { text: 'Quarter', standoff: 6 },
  },
  yaxis: {
    gridcolor:    '#2d3148',
    linecolor:    '#2d3148',
    tickcolor:    '#2d3148',
    zeroline:     false,
    automargin:   true,
  },
  showlegend:    false,
};

const PLOTLY_CONFIG = {
  displayModeBar:    false,
  responsive:        true,
};

// colour palette
const COLOURS = ['#4f7cff','#34d399','#fbbf24','#f87171','#a78bfa','#38bdf8','#fb923c','#4ade80'];

// ── Chart definitions ─────────────────────────────────────────────────

const CHARTS = [
  {
    id:    'chart-gdp',
    title: 'GDP',
    field: 'gdp',
    fmt:   v => '£' + fmt_compact(v),
    yaxis: { title: { text: '£' } },
    colour: COLOURS[0],
  },
  {
    id:    'chart-inflation',
    title: 'Inflation Rate',
    field: 'inflation',
    fmt:   v => fmt_pct(v),
    yaxis: { title: { text: '%' }, tickformat: '.1%' },
    colour: COLOURS[1],
    refline: { y: 0.02, label: 'Target 2%' },
  },
  {
    id:    'chart-unemployment',
    title: 'Unemployment Rate',
    field: 'unemployment_rate',
    fmt:   v => fmt_pct(v),
    yaxis: { title: { text: '%' }, tickformat: '.1%' },
    colour: COLOURS[2],
  },
  {
    id:    'chart-policy-rate',
    title: 'Policy Interest Rate',
    field: 'policy_rate',
    fmt:   v => fmt_pct(v),
    yaxis: { title: { text: '%' }, tickformat: '.2%' },
    colour: COLOURS[3],
  },
  {
    id:    'chart-wage',
    title: 'Average Wage (quarterly)',
    field: 'average_wage',
    fmt:   v => '£' + fmt_num(v, 0),
    yaxis: { title: { text: '£' } },
    colour: COLOURS[4],
  },
  {
    id:    'chart-deficit',
    title: 'Government Deficit',
    field: 'government_deficit',
    fmt:   v => '£' + fmt_compact(v),
    yaxis: { title: { text: '£' } },
    colour: COLOURS[5],
  },
  {
    id:    'chart-lending',
    title: 'Total Bank Lending',
    field: 'total_lending',
    fmt:   v => '£' + fmt_compact(v),
    yaxis: { title: { text: '£' } },
    colour: COLOURS[6],
  },
  {
    id:    'chart-bankruptcies',
    title: 'Firm Bankruptcies',
    field: 'firm_bankruptcies',
    fmt:   v => fmt_num(v, 0),
    yaxis: { title: { text: 'count' } },
    colour: COLOURS[7],
  },
];

// ── Formatting helpers ────────────────────────────────────────────────

function fmt_compact(v) {
  if (Math.abs(v) >= 1e9) return (v / 1e9).toFixed(1) + 'B';
  if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return v.toFixed(0);
}

function fmt_pct(v) {
  return (v * 100).toFixed(2) + '%';
}

function fmt_num(v, dp = 2) {
  return v.toLocaleString('en-GB', { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

// ── Parameter config ──────────────────────────────────────────────────

const PARAM_GROUPS = [
  {
    label: 'Simulation',
    params: [
      { key: 'periods',        label: 'Quarters',       min: 10,  max: 200, step: 5,    default: 80,  type: 'range' },
      { key: 'seed',           label: 'Random seed',    min: 0,   max: 999, step: 1,    default: 42,  type: 'number' },
    ],
  },
  {
    label: 'Firms',
    params: [
      { key: 'n_firms',        label: 'Number of firms',min: 10,  max: 500, step: 10,   default: 100, type: 'range' },
      { key: 'price_markup',   label: 'Price markup',   min: 0.01,max: 0.50,step: 0.01, default: 0.15,type: 'range', pct: true },
    ],
  },
  {
    label: 'Households',
    params: [
      { key: 'n_households',   label: 'Households',     min: 50,  max: 2000,step: 50,   default: 500, type: 'range' },
      { key: 'mpc_mean',       label: 'Avg MPC',        min: 0.3, max: 0.99,step: 0.01, default: 0.8, type: 'range', pct: true },
    ],
  },
  {
    label: 'Banks',
    params: [
      { key: 'n_banks',        label: 'Banks',          min: 1,   max: 20,  step: 1,    default: 10,  type: 'range' },
      { key: 'capital_requirement', label: 'Capital req.',min:0.04,max:0.30,step:0.01,  default: 0.10,type: 'range', pct: true },
    ],
  },
  {
    label: 'Central Bank',
    params: [
      { key: 'inflation_target',     label: 'Inflation target', min:0.005,max:0.10,step:0.005,default:0.02, type:'range', pct:true },
      { key: 'inflation_coefficient',label: 'π coefficient',    min:1.0,  max:3.0, step:0.1,  default:1.5,  type:'range' },
      { key: 'output_gap_coefficient',label:'Gap coefficient',  min:0.0,  max:1.5, step:0.1,  default:0.5,  type:'range' },
    ],
  },
  {
    label: 'Government',
    params: [
      { key: 'spending_gdp_ratio', label: 'Gov. spending / GDP', min:0.15,max:0.65,step:0.01,default:0.40,type:'range',pct:true },
      { key: 'corporate_tax_rate', label: 'Corporate tax',       min:0.05,max:0.40,step:0.01,default:0.19,type:'range',pct:true },
      { key: 'income_tax_rate',    label: 'Income tax (base)',   min:0.05,max:0.50,step:0.01,default:0.20,type:'range',pct:true },
    ],
  },
];

// ── State ─────────────────────────────────────────────────────────────

const state = {
  running:    false,
  hasResults: false,
  params:     {},       // filled during init
};

// ── DOM helpers ───────────────────────────────────────────────────────

const $ = id => document.getElementById(id);

function setStatus(mode, text) {
  const dot  = $('status-dot');
  const span = $('status-text');
  dot.className  = 'status-dot ' + mode;
  span.textContent = text;
}

function showSummary(periods) {
  const bar = $('summary-chips');
  bar.innerHTML = '';
  const last = periods[periods.length - 1];
  const chips = [
    ['GDP', '£' + fmt_compact(last.gdp)],
    ['Inflation', fmt_pct(last.inflation)],
    ['Unemployment', fmt_pct(last.unemployment_rate)],
    ['Policy rate', fmt_pct(last.policy_rate)],
  ];
  chips.forEach(([k, v]) => {
    const c = document.createElement('div');
    c.className = 'chip';
    c.innerHTML = `${k} <strong>${v}</strong>`;
    bar.appendChild(c);
  });
}

// ── Build sidebar controls ─────────────────────────────────────────────

function buildSidebar() {
  const container = $('param-groups');
  container.innerHTML = '';

  PARAM_GROUPS.forEach(group => {
    const grp = document.createElement('div');
    grp.className = 'param-group open';

    const hdr = document.createElement('div');
    hdr.className = 'param-group-header';
    hdr.innerHTML = `${group.label} <span class="chevron">▼</span>`;
    hdr.addEventListener('click', () => {
      grp.classList.toggle('open');
    });

    const body = document.createElement('div');
    body.className = 'param-group-body';

    group.params.forEach(p => {
      state.params[p.key] = p.default;
      const row = document.createElement('div');
      row.className = 'param-row';

      const labelRow = document.createElement('div');
      labelRow.className = 'param-label';
      const labelSpan = document.createElement('span');
      labelSpan.textContent = p.label;
      const valSpan = document.createElement('span');
      valSpan.className = 'val';
      valSpan.id = `val-${p.key}`;
      valSpan.textContent = fmtParamVal(p, p.default);
      labelRow.append(labelSpan, valSpan);

      const input = document.createElement('input');
      input.type  = p.type === 'number' ? 'number' : 'range';
      input.min   = p.min;
      input.max   = p.max;
      input.step  = p.step;
      input.value = p.default;
      input.id    = `input-${p.key}`;

      input.addEventListener('input', () => {
        const v = parseFloat(input.value);
        state.params[p.key] = v;
        valSpan.textContent = fmtParamVal(p, v);
      });

      row.append(labelRow, input);
      body.appendChild(row);
    });

    grp.append(hdr, body);
    container.appendChild(grp);
  });
}

function fmtParamVal(p, v) {
  if (p.pct) return (v * 100).toFixed(p.step < 0.01 ? 1 : 1) + '%';
  if (Number.isInteger(v) || p.step >= 1) return Math.round(v).toString();
  return v.toFixed(2);
}

// ── Build chart cards ─────────────────────────────────────────────────

function buildCharts() {
  const grid = $('charts-grid');
  grid.innerHTML = '';

  CHARTS.forEach(c => {
    const card = document.createElement('div');
    card.className = 'chart-card';
    card.innerHTML = `<div class="chart-title">${c.title}</div>
                      <div class="chart-plot" id="${c.id}"></div>`;
    grid.appendChild(card);
  });
}

// ── Render charts from data ───────────────────────────────────────────

function renderCharts(periods) {
  const xs = periods.map(p => p.period);

  CHARTS.forEach(c => {
    const ys = periods.map(p => p[c.field]);

    const trace = {
      x:    xs,
      y:    ys,
      type: 'scatter',
      mode: 'lines',
      line: { color: c.colour, width: 2 },
      hovertemplate: `Q%{x}<br>${c.title}: %{y}<extra></extra>`,
    };

    const traces = [trace];

    // optional reference line (e.g. inflation target)
    if (c.refline) {
      traces.push({
        x:    [xs[0], xs[xs.length - 1]],
        y:    [c.refline.y, c.refline.y],
        type: 'scatter',
        mode: 'lines',
        line: { color: '#fff', width: 1, dash: 'dot' },
        hoverinfo: 'none',
      });
    }

    const layout = {
      ...LAYOUT_BASE,
      yaxis: { ...LAYOUT_BASE.yaxis, ...(c.yaxis || {}) },
    };

    Plotly.react(c.id, traces, layout, PLOTLY_CONFIG);
  });
}

// ── Run simulation ────────────────────────────────────────────────────

async function runSimulation() {
  if (state.running) return;

  state.running = true;
  const btn = $('btn-run');
  btn.disabled = true;
  btn.innerHTML = '<div class="spinner"></div> Running…';
  setStatus('running', 'Simulation running…');
  $('summary-chips').innerHTML = '';

  // hide empty state, show charts grid
  $('empty-state').style.display = 'none';
  $('charts-grid').style.display = 'grid';

  try {
    const resp = await fetch('/api/simulate', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(state.params),
    });

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ detail: resp.statusText }));
      throw new Error(err.detail || 'Server error');
    }

    const data = await resp.json();
    renderCharts(data.periods);
    showSummary(data.periods);
    state.hasResults = true;
    setStatus('ready', `Completed — ${data.periods.length} quarters simulated`);
  } catch (err) {
    setStatus('error', 'Error: ' + err.message);
    console.error(err);
  } finally {
    state.running = false;
    btn.disabled = false;
    btn.innerHTML = '▶ Run Simulation';
  }
}

// ── Reset ─────────────────────────────────────────────────────────────

function resetParams() {
  PARAM_GROUPS.forEach(group => {
    group.params.forEach(p => {
      const input = $(`input-${p.key}`);
      const val   = $(`val-${p.key}`);
      if (input) {
        input.value = p.default;
        state.params[p.key] = p.default;
      }
      if (val) val.textContent = fmtParamVal(p, p.default);
    });
  });
}

// ── Init ──────────────────────────────────────────────────────────────

function init() {
  buildSidebar();
  buildCharts();

  // hide charts grid, show empty state initially
  $('charts-grid').style.display = 'none';
  $('empty-state').style.display = 'flex';

  $('btn-run').addEventListener('click', runSimulation);
  $('btn-reset').addEventListener('click', resetParams);

  setStatus('ready', 'Configure parameters and run a simulation');
}

document.addEventListener('DOMContentLoaded', init);
