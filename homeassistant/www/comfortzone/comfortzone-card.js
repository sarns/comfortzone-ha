/*
 * comfortzone-card — schematic dashboard card for the Comfortzone EX heat pump.
 *
 * One SVG: the schematic PNG is the background and all value panels live in the
 * image's own coordinate system (viewBox), so text scales together with the
 * drawing on every screen. When the card itself gets narrow (phone), a CSS
 * container query switches to a responsive grid built from the same panel
 * definitions — no per-screen copies to maintain.
 *
 * Install: copy to /config/www/comfortzone/comfortzone-card.js and add the
 * dashboard resource /local/comfortzone/comfortzone-card.js?v=1 (JavaScript module).
 *
 * Config:
 *   type: custom:comfortzone-card
 *   entity_prefix: technikkeller_comfortzone_ex     # optional
 *   image: /local/comfortzone/comfortzone-ex-schema.png  # optional
 *   compact_below: 900        # card width (px) below which the grid layout is used
 *   compact_image: true       # show the schematic (without panels) above the grid
 *   panels:                   # optional per-panel overrides (viewBox units, 1672 x 941)
 *     kaeltekreis: { x: 995, y: 20, w: 255 }
 *     energie: { hidden: true }
 */

const VERSION = '1.0.0';
const VB_W = 1672;
const VB_H = 941;
const ROW_H = 26;
const HEAD_H = 30;
const PAD_B = 8;
const PAD_X = 14;

const BIN = {
  run: ['Läuft', 'Aus'],
  active: ['Aktiv', 'Aus'],
  online: ['Online', 'Offline'],
};
const ENUM = { Low: 'Niedrig', Normal: 'Normal', High: 'Hoch' };
const UNIT = { d: 'Tage' };

// Panel layout in image pixels (viewBox 1672 x 941). Rows:
//   e: entity (domain.suffix, prefix is inserted), l: label, p: decimals,
//   bin: binary texts key, enum: translate select/enum states,
//   c: value colour override, showIf: only show row for this state,
//   cop: [output, input] derived ratio.
const PANELS = [
  { id: 'aussen', title: 'Außen', color: '#8bdcff', x: 440, y: 30, w: 190, rows: [
    { e: 'sensor.outdoor_temperature', l: 'Temperatur', p: 1 },
  ] },
  { id: 'raum', title: 'Raum', color: '#ffffff', x: 110, y: 235, w: 170, rows: [
    { e: 'sensor.indoor_temperature', l: 'Ist', p: 1 },
    { e: 'sensor.room_setpoint', l: 'Soll', p: 1, c: '#d9e8f5' },
  ] },
  { id: 'fortluft', title: 'Fortluft', color: '#8bdcff', x: 760, y: 110, w: 220, rows: [
    { e: 'sensor.exhaust_air_temperature', l: 'Temperatur', p: 1 },
    { e: 'sensor.fan_speed', l: 'Lüfter', enum: true },
    { e: 'sensor.fan_power', l: 'Leistung', p: 0 },
  ] },
  { id: 'kaeltekreis', title: 'Kältekreis', color: '#c9b8ff', x: 995, y: 20, w: 255, rows: [
    { e: 'sensor.high_pressure', l: 'Hochdruck', p: 1 },
    { e: 'sensor.low_pressure', l: 'Niederdruck', p: 1 },
    { e: 'sensor.pressure_ratio', l: 'Druckverhältnis', p: 1 },
    { e: 'sensor.condenser_temperature', l: 'Kondensation', p: 1 },
    { e: 'sensor.superheat', l: 'Überhitzung', p: 1 },
    { e: 'sensor.target_superheat', l: 'Überhitzung Soll', p: 1 },
    { e: 'sensor.expansion_valve_position', l: 'Expansionsventil', p: 0 },
  ] },
  { id: 'warmwasser', title: 'Warmwasser', color: '#ffad93', x: 1265, y: 20, w: 225,
    status: 'binary_sensor.hot_water_boost', rows: [
    { e: 'sensor.hot_water_temperature', l: 'Ist', p: 1 },
    { e: 'sensor.hot_water_target', l: 'Soll', p: 1, c: '#ffd4c9' },
    { e: 'sensor.active_hot_water_target', l: 'Aktiv-Soll', p: 1, c: '#ffd4c9' },
    { e: 'sensor.hot_water_flow', l: 'Durchfluss', p: 1, c: '#ffd4c9' },
    { e: 'binary_sensor.hot_water_boost', l: 'Boost', bin: 'active', c: '#ffe08a', showIf: 'on' },
  ] },
  { id: 'verdampfer', title: 'Verdampfer', color: '#72dcff', x: 420, y: 365, w: 180, rows: [
    { e: 'sensor.evaporator_inlet_temperature', l: 'Eintritt', p: 1 },
  ] },
  { id: 'waermetauscher', title: 'Wärmetauscher', color: '#ffad8e', x: 840, y: 262, w: 190, rows: [
    { e: 'sensor.exchanger_outlet_temperature', l: 'Austritt', p: 1 },
  ] },
  { id: 'heissgas', title: 'Heißgas', color: '#ff9675', x: 815, y: 618, w: 205, rows: [
    { e: 'sensor.hot_gas_temperature', l: 'Temperatur', p: 1 },
  ] },
  { id: 'heizkreis', title: 'Heizkreis', color: '#ffad93', x: 1430, y: 450, w: 230, rows: [
    { e: 'sensor.flow_temperature', l: 'Vorlauf', p: 1 },
    { e: 'sensor.calculated_flow_temperature', l: 'Berechnet', p: 1, c: '#ffd4c9' },
    { e: 'sensor.return_temperature', l: 'Rücklauf', p: 1, c: '#79ceff' },
  ] },
  { id: 'energie', title: 'Energie', color: '#e7f2fa', x: 20, y: 735, w: 270, rows: [
    { e: 'sensor.compressor_energy', l: 'Kompressor', p: 0 },
    { e: 'sensor.additional_heater_energy', l: 'Zusatzheizung', p: 0 },
    { e: 'sensor.hot_water_energy', l: 'Warmwasser', p: 0 },
  ] },
  { id: 'laufzeit', title: 'Laufzeit', color: '#e7f2fa', x: 305, y: 735, w: 240, rows: [
    { e: 'sensor.compressor_runtime', l: 'Kompressor', p: 0 },
    { e: 'sensor.total_runtime', l: 'Gesamt', p: 0 },
  ] },
  { id: 'kompressor', title: 'Kompressor', color: '#ffad93', x: 610, y: 735, w: 280,
    status: 'binary_sensor.compressor_running', rows: [
    { e: 'binary_sensor.compressor_running', l: 'Status', bin: 'run' },
    { e: 'sensor.compressor_frequency', l: 'Frequenz', p: 1 },
    { e: 'sensor.compressor_target_frequency', l: 'Soll-Frequenz', p: 1 },
    { e: 'sensor.compressor_input_power', l: 'Aufnahme', p: 0 },
    { e: 'sensor.compressor_output_power', l: 'Abgabe', p: 0 },
    { cop: ['sensor.compressor_output_power', 'sensor.compressor_input_power'], l: 'COP (live)', p: 2, c: '#9df3b0' },
  ] },
  { id: 'zusatzheizung', title: 'Zusatzheizung', color: '#ffc778', x: 905, y: 735, w: 230,
    status: 'binary_sensor.additional_heater_active', rows: [
    { e: 'binary_sensor.additional_heater_active', l: 'Status', bin: 'active' },
    { e: 'sensor.additional_heater_power', l: 'Leistung', p: 0, c: '#ffd166' },
  ] },
  { id: 'leistung', title: 'Heizleistung', color: '#ffd166', x: 1150, y: 735, w: 255, rows: [
    { e: 'sensor.total_output_power', l: 'Abgabe', p: 0 },
    { e: 'sensor.required_heating_power', l: 'Bedarf', p: 0 },
    { e: 'sensor.heating_flow', l: 'Heizfluss', p: 1, c: '#79ceff' },
  ] },
  { id: 'status', title: 'System', color: '#9df3b0', x: 1420, y: 735, w: 240, rows: [
    { e: 'binary_sensor.rs485_bus_online', l: 'RS485', bin: 'online' },
    { e: 'sensor.filter_change_time', l: 'Filterwechsel', p: 0, c: '#e7f2fa' },
  ] },
];

// Panel order in the compact grid (most-looked-at first).
const GRID_ORDER = ['raum', 'aussen', 'heizkreis', 'warmwasser', 'kompressor', 'leistung',
  'zusatzheizung', 'fortluft', 'kaeltekreis', 'verdampfer', 'waermetauscher', 'heissgas',
  'energie', 'laufzeit', 'status'];

const SVG_NS = 'http://www.w3.org/2000/svg';

function el(tag, attrs = {}, parent, ns) {
  const n = ns ? document.createElementNS(ns, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') n.textContent = v;
    else n.setAttribute(k, v);
  }
  if (parent) parent.appendChild(n);
  return n;
}
const svg = (tag, attrs, parent) => el(tag, attrs, parent, SVG_NS);

const STYLE = (compactBelow) => `
  :host { display: block; }
  ha-card { overflow: hidden; }
  .wrap { container-type: inline-size; position: relative; }
  svg.schema { display: block; width: 100%; height: auto; font-family: var(--ha-font-family-body, Roboto, sans-serif); }
  .panel .bg { fill: rgba(5, 18, 32, 0.84); stroke: var(--c); stroke-opacity: 0.45; stroke-width: 1.5; }
  .panel .title { fill: var(--c); font-size: 13px; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase; }
  .panel .lbl { fill: #9fb3c8; font-size: 17px; }
  .panel .val { fill: var(--vc, var(--c)); font-size: 17px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .panel .hit { fill: transparent; cursor: pointer; }
  .panel .row:hover .hit { fill: rgba(255, 255, 255, 0.07); }
  .panel .dot { fill: #3b4a5a; }
  .panel.on .dot { fill: #9df3b0; animation: pulse 1.6s ease-in-out infinite; }
  .unavail .val, .unavail .gval { opacity: 0.45; }
  @keyframes pulse { 50% { opacity: 0.35; } }
  .banner { fill: #ffb4a8; font-size: 18px; font-weight: 600; }
  .wrap:not(.stale) .banner { display: none; }
  .wrap.stale .panel { opacity: 0.55; }

  .grid { display: none; gap: 12px; padding: 12px;
          grid-template-columns: repeat(auto-fill, minmax(min(100%, 220px), 1fr)); }
  .gpanel { border-left: 3px solid var(--gc); border-radius: 8px; padding: 8px 12px;
            background: var(--secondary-background-color, rgba(127,127,127,0.08)); }
  .gpanel h3 { margin: 0 0 4px; font-size: 12px; font-weight: 600; letter-spacing: 1.2px;
               text-transform: uppercase; color: var(--secondary-text-color); display: flex;
               align-items: center; justify-content: space-between; }
  .gpanel h3 i { width: 8px; height: 8px; border-radius: 50%; background: var(--disabled-text-color, #888); }
  .gpanel.on h3 i { background: var(--success-color, #43a047); animation: pulse 1.6s ease-in-out infinite; }
  .grow { display: flex; justify-content: space-between; gap: 8px; padding: 3px 0; cursor: pointer;
          font-size: 14px; color: var(--secondary-text-color); }
  .grow:hover { color: var(--primary-text-color); }
  .gval { font-weight: 600; color: var(--primary-text-color); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .gbanner { display: none; margin: 12px 12px 0; padding: 8px 12px; border-radius: 8px;
             background: var(--error-color, #db4437); color: #fff; font-size: 14px; }

  @container (max-width: ${compactBelow - 0.02}px) {
    .schema .panel, .schema .banner { display: none; }
    .grid { display: grid; }
    .wrap.stale .gbanner { display: block; }
    .wrap.noimg svg.schema { display: none; }
  }
`;

class ComfortzoneCard extends HTMLElement {
  setConfig(config) {
    this._config = {
      entity_prefix: 'technikkeller_comfortzone_ex',
      image: '/local/comfortzone/comfortzone-ex-schema.png',
      compact_below: 900,
      compact_image: true,
      panels: {},
      ...config,
    };
    this._built = false;
    if (this._hass) this._render();
  }

  set hass(hass) {
    const prev = this._hass;
    this._hass = hass;
    if (!this._built) { this._render(); return; }
    // Only touch the DOM when one of our entities changed.
    if (prev && this._ids.every((id) => prev.states[id] === hass.states[id])) return;
    this._update();
  }

  getCardSize() { return 9; }
  getGridOptions() { return { columns: 'full', rows: 'auto' }; }
  static getStubConfig() { return {}; }

  _id(e) {
    const [domain, suffix] = e.split('.');
    return `${domain}.${this._config.entity_prefix}_${suffix}`;
  }

  _render() {
    if (!this._config || !this._hass) return;
    const cfg = this._config;
    const root = this.shadowRoot || this.attachShadow({ mode: 'open' });
    root.innerHTML = '';
    el('style', { text: STYLE(Number(cfg.compact_below) || 900) }, root);
    const card = el('ha-card', {}, root);
    this._wrap = el('div', { class: `wrap${cfg.compact_image ? '' : ' noimg'}` }, card);

    const s = svg('svg', { class: 'schema', viewBox: `0 0 ${VB_W} ${VB_H}`, role: 'img',
      'aria-label': 'Comfortzone Wärmepumpe Schema' }, this._wrap);
    svg('image', { href: cfg.image, x: 0, y: 0, width: VB_W, height: VB_H,
      preserveAspectRatio: 'xMidYMid slice' }, s);
    svg('text', { class: 'banner', x: VB_W / 2, y: 26, 'text-anchor': 'middle',
      text: 'RS485-Bus offline – Werte sind veraltet' }, s);

    this._gbanner = el('div', { class: 'gbanner', text: 'RS485-Bus offline – Werte sind veraltet' }, this._wrap);
    const grid = el('div', { class: 'grid' }, this._wrap);

    this._rows = [];
    this._panels = [];
    for (const base of PANELS) {
      const p = { ...base, ...(cfg.panels[base.id] || {}) };
      if (p.hidden) continue;

      // SVG panel
      const g = svg('g', { class: 'panel', transform: `translate(${p.x} ${p.y})`, style: `--c:${p.color}` }, s);
      const bg = svg('rect', { class: 'bg', x: 0, y: 0, width: p.w, rx: 10 }, g);
      svg('text', { class: 'title', x: PAD_X, y: 21, text: p.title }, g);
      if (p.status) svg('circle', { class: 'dot', cx: p.w - PAD_X, cy: 16, r: 5 }, g);

      // Grid panel
      const order = GRID_ORDER.indexOf(p.id);
      const gp = el('div', { class: 'gpanel', style: `--gc:${p.color};order:${order < 0 ? 99 : order}` }, grid);
      const h3 = el('h3', { text: p.title }, gp);
      if (p.status) el('i', {}, h3);

      const panel = { def: p, g, bg, gp, rows: [] };
      for (const r of p.rows) {
        const entityId = this._id(r.e || r.cop[0]);
        const rowG = svg('g', { class: 'row' }, g);
        svg('rect', { class: 'hit', x: 4, y: 0, width: p.w - 8, height: ROW_H, rx: 6 }, rowG);
        svg('text', { class: 'lbl', x: PAD_X, y: 19, text: r.l }, rowG);
        const v = svg('text', { class: 'val', x: p.w - PAD_X, y: 19, 'text-anchor': 'end',
          style: r.c ? `--vc:${r.c}` : '' }, rowG);
        const gr = el('div', { class: 'grow' }, gp);
        el('span', { text: r.l }, gr);
        const gv = el('span', { class: 'gval' }, gr);
        const open = () => this._moreInfo(entityId);
        rowG.addEventListener('click', open);
        gr.addEventListener('click', open);
        const row = { def: r, entityId, rowG, v, gr, gv, text: null, shown: true };
        panel.rows.push(row);
        this._rows.push(row);
      }
      this._panels.push(panel);
    }

    const ids = new Set();
    for (const row of this._rows) {
      if (row.def.e) ids.add(this._id(row.def.e));
      if (row.def.cop) row.def.cop.forEach((e) => ids.add(this._id(e)));
    }
    for (const p of this._panels) if (p.def.status) ids.add(this._id(p.def.status));
    ids.add(this._id('binary_sensor.rs485_bus_online'));
    this._ids = [...ids];

    this._built = true;
    this._update();
  }

  _fmt(n, p) {
    const lang = this._hass.locale?.language || this._hass.language || 'de';
    const key = `${lang}|${p}`;
    this._nf = this._nf || {};
    this._nf[key] = this._nf[key] || new Intl.NumberFormat(lang, { minimumFractionDigits: p, maximumFractionDigits: p });
    return this._nf[key].format(n);
  }

  _value(r) {
    const st = this._hass.states;
    if (r.cop) {
      const out = Number(st[this._id(r.cop[0])]?.state);
      const inp = Number(st[this._id(r.cop[1])]?.state);
      if (!Number.isFinite(out) || !Number.isFinite(inp) || inp < 50) return { text: '—', ok: false };
      return { text: this._fmt(out / inp, r.p), ok: true };
    }
    const so = st[this._id(r.e)];
    if (!so || so.state === 'unavailable' || so.state === 'unknown') return { text: '—', ok: false, state: so?.state };
    if (r.bin) return { text: BIN[r.bin][so.state === 'on' ? 0 : 1], ok: true, state: so.state };
    if (r.enum) return { text: ENUM[so.state] || so.state, ok: true, state: so.state };
    const num = Number(so.state);
    if (!Number.isFinite(num)) return { text: so.state, ok: true, state: so.state };
    const u = so.attributes.unit_of_measurement;
    const unit = u ? ` ${UNIT[u] || u}` : '';
    return { text: this._fmt(num, r.p ?? 1) + unit, ok: true, state: so.state };
  }

  _update() {
    const st = this._hass.states;
    for (const row of this._rows) {
      const { text, ok, state } = this._value(row.def);
      if (text !== row.text) {
        row.v.textContent = text;
        row.gv.textContent = text;
        row.text = text;
      }
      row.rowG.classList.toggle('unavail', !ok);
      row.gr.classList.toggle('unavail', !ok);
      row.shown = !row.def.showIf || state === row.def.showIf;
    }
    for (const p of this._panels) {
      // Lay out rows (conditional rows collapse) and size the background.
      let i = 0;
      for (const row of p.rows) {
        row.rowG.style.display = row.shown ? '' : 'none';
        row.gr.style.display = row.shown ? '' : 'none';
        if (row.shown) row.rowG.setAttribute('transform', `translate(0 ${HEAD_H + i++ * ROW_H})`);
      }
      p.bg.setAttribute('height', HEAD_H + i * ROW_H + PAD_B);
      if (p.def.status) {
        const on = st[this._id(p.def.status)]?.state === 'on';
        p.g.classList.toggle('on', on);
        p.gp.classList.toggle('on', on);
      }
    }
    const bus = st[this._id('binary_sensor.rs485_bus_online')];
    this._wrap.classList.toggle('stale', !!bus && bus.state !== 'on');
  }

  _moreInfo(entityId) {
    this.dispatchEvent(new CustomEvent('hass-more-info', {
      detail: { entityId }, bubbles: true, composed: true,
    }));
  }
}

customElements.define('comfortzone-card', ComfortzoneCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'comfortzone-card',
  name: 'Comfortzone Schema',
  description: 'Skalierendes Wärmepumpen-Schema mit Live-Werten',
});
console.info(`%c comfortzone-card ${VERSION} `, 'background:#0b2236;color:#8bdcff');
