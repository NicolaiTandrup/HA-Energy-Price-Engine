/* Energy Price Engine: local, dependency-free, read-only Lovelace card.
 * Supported HA custom-card interface + authenticated HA WebSocket commands.
 * Stored amounts stay unrounded; formatting below is presentation only.
 */
const WORDS = {
  en: {
    title: "Electricity prices", today: "Today", tomorrow: "Tomorrow", now: "Now",
    raw: "Nord Pool spot", final: "Final electricity price", ex: "Excluding VAT & charges",
    incl: "Including all variable charges & VAT", grid: "Today's network tariffs",
    schedule: "Every quarter-hour", inspect: "Inspect a quarter", current: "Current quarter",
    next: "Next quarter", history: "Today's full-day history", publication: "Tomorrow's coverage",
    missing: "Unavailable", ready: "Ready", incomplete: "Incomplete", stale: "Stale", error: "Error",
    loading: "Loading stored prices…", retry: "Refresh", source: "Source / verification",
    slot: "Local interval (UTC offset)", vat: "VAT", dso: "DSO / network", supplier: "Supplier markup",
    energinet_net: "Energinet network", energinet_system: "Energinet system", electricity_tax: "Electricity tax",
    spot: "Nord Pool spot", finalLabel: "Verified final", status: "Status", revision: "Revision",
    from: "From", to: "To", rate: "Applied tariff (excl. VAT)", component: "Component",
    amount: "øre/kWh", precision: "Amounts shown with two decimals. Totals use unrounded stored prices; rounded rows may differ by 0.01. Fixed subscriptions excluded.",
    gaps: "Gaps are unavailable prices, never zero. Select a bar or interval to inspect its stored components.",
    verified: "Verified", rawOnly: "Raw spot is verified independently of final pricing.",
    wait: "Waiting for Nord Pool publication or complete source coverage. See the reason and next scheduled check below.",
    fix: "Corrective action", checked: "Source checked", update: "Next scheduled check", generated: "Dashboard read",
    noRecord: "No verified final record for this quarter. Missing components stay unavailable; no tariffs are reconstructed on this read.",
    retained: "Retained stored amount (not currently Ready)", applied: "Applied in the stored price", utc: "UTC identity",
    config: "Set entity to an entity belonging to your Energy Price Engine site.",
  },
  da: {
    title: "Elpriser", today: "I dag", tomorrow: "I morgen", now: "Nu",
    raw: "Nord Pool spot", final: "Samlet elpris", ex: "Uden moms og tillæg",
    incl: "Med alle variable tillæg og moms", grid: "Dagens nettariffer",
    schedule: "Hvert kvarter", inspect: "Undersøg et kvarter", current: "Nuværende kvarter",
    next: "Næste kvarter", history: "Hele dagens historik", publication: "Morgendagens dækning",
    missing: "Ikke tilgængelig", ready: "Klar", incomplete: "Ufuldstændig", stale: "Forældet", error: "Fejl",
    loading: "Indlæser gemte priser…", retry: "Opdater", source: "Kilde / kontrol",
    slot: "Lokalt tidsrum (UTC-offset)", vat: "Moms", dso: "DSO / net", supplier: "Leverandørtillæg",
    energinet_net: "Energinet net", energinet_system: "Energinet system", electricity_tax: "Elafgift",
    spot: "Nord Pool spot", finalLabel: "Verificeret slutpris", status: "Status", revision: "Revision",
    from: "Fra", to: "Til", rate: "Anvendt tarif (ekskl. moms)", component: "Komponent",
    amount: "øre/kWh", precision: "Beløb vises med to decimaler. Totaler bruger uafrundede gemte priser; afrundede rækker kan afvige med 0,01. Faste abonnementer er udeladt.",
    gaps: "Huller er manglende priser, aldrig nul. Vælg en søjle eller et tidsrum for at se de gemte komponenter.",
    verified: "Verificeret", rawOnly: "Rå spot kontrolleres uafhængigt af slutprisen.",
    wait: "Afventer Nord Pool-offentliggørelse eller komplet kildedækning. Se årsag og næste planlagte kontrol nedenfor.",
    fix: "Afhjælpning", checked: "Kilden kontrolleret", update: "Næste planlagte kontrol", generated: "Dashboard læst",
    noRecord: "Ingen verificeret slutpris for dette kvarter. Manglende komponenter er utilgængelige; tariffer genberegnes ikke ved læsning.",
    retained: "Beholdt gemt beløb (ikke Klar nu)", applied: "Anvendt i den gemte pris", utc: "UTC-identitet",
    config: "Angiv entity som en entitet fra dit Energy Price Engine-sted.",
  },
};
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;"}[c]));
const present = (v) => typeof v === "number" && Number.isFinite(v);
const KEYS = ["spot", "dso", "energinet_net", "energinet_system", "supplier", "electricity_tax", "vat", "final"];
const STYLE = `
:host{display:block;color:var(--primary-text-color,#202b36);font-family:var(--paper-font-body1_-_font-family,Roboto,sans-serif)}
*{box-sizing:border-box}ha-card{overflow:hidden;background:var(--ha-card-background,var(--card-background-color,#fff))}
header{padding:24px 24px 12px;display:flex;justify-content:space-between;gap:12px;align-items:flex-start}h1{font-size:24px;line-height:1.2;font-weight:500;margin:4px 0 8px}h2{font-size:18px;font-weight:500;margin:0 0 6px}h3{font-size:15px;margin:0 0 4px}.eyebrow{font-size:11px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:var(--secondary-text-color,#667)}p{line-height:1.5;margin:6px 0;font-size:13px}.muted,small{color:var(--secondary-text-color,#667);font-size:12px}.body{padding:0 24px 24px;min-width:0}button,select{font:inherit}button{color:var(--primary-color,#167d7f);background:transparent;border:1px solid var(--divider-color,#ddd);border-radius:8px;padding:8px 12px;cursor:pointer}button:hover{background:var(--secondary-background-color,#f5f7f8)}button:focus-visible,select:focus-visible,[tabindex]:focus-visible{outline:2px solid var(--primary-color,#167d7f);outline-offset:2px}.health{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:10px 0 20px}.health>div{background:var(--secondary-background-color,#f4f7f8);padding:12px;border-radius:10px;min-width:0}.health p{font-size:12px;margin:0 0 6px}.badge{display:inline-block;border-radius:6px;padding:3px 7px;font-size:12px;background:var(--secondary-background-color,#eef2f4);white-space:nowrap}.ready{color:var(--success-color,#18714c)}.incomplete,.stale{color:var(--warning-color,#90610b)}.error{color:var(--error-color,#c63838)}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:16px 0}.chart{border:1px solid var(--divider-color,#ddd);border-radius:12px;padding:16px 12px 8px;min-width:0}.chart h2,.chart p{padding:0 4px}.chart svg{display:block;width:100%;height:240px;overflow:visible}.axis{fill:var(--secondary-text-color,#667);font-size:10px}.gridline{stroke:var(--divider-color,#ddd);stroke-width:1}.zero{stroke:var(--secondary-text-color,#667);stroke-width:1}.bar{cursor:pointer;stroke-width:.2;stroke:var(--ha-card-background,#fff)}.bar:hover,.bar:focus{opacity:.65}.spot-bar{fill:var(--primary-color,#168a91)}.final-bar{fill:var(--accent-color,#725abb)}.boundary{stroke:var(--secondary-text-color,#667);stroke-dasharray:4 4}.now{stroke:var(--error-color,#cf4a42);stroke-width:1.5}.now-label{fill:var(--error-color,#cf4a42);font-size:13px;font-weight:600}.section{margin-top:24px;padding-top:20px;border-top:1px solid var(--divider-color,#ddd)}.scroll{overflow:auto;max-height:520px;border:1px solid var(--divider-color,#ddd);border-radius:10px;margin-top:12px;overscroll-behavior-x:contain}table{border-collapse:collapse;width:100%;font-size:12px;font-variant-numeric:tabular-nums}th{position:sticky;top:0;z-index:1;background:var(--card-background-color,#fff);font-weight:500;text-align:left;white-space:nowrap;color:var(--secondary-text-color,#667)}th,td{padding:10px 12px;border-bottom:1px solid var(--divider-color,#eee);vertical-align:top}td.numeric{text-align:right;white-space:nowrap}td.time{white-space:nowrap}td.source{min-width:180px;max-width:360px;overflow-wrap:anywhere}tbody tr:last-child td{border-bottom:0}tr.selected{background:var(--secondary-background-color,#f4f7f8)}.time button{border:0;padding:0;text-align:left;white-space:nowrap;color:var(--primary-text-color,#222)}.source small{display:block;line-height:1.5}.inspector select{max-width:100%;width:100%;margin:8px 0 4px;padding:10px;border:1px solid var(--divider-color,#ddd);border-radius:8px;background:var(--card-background-color,#fff);color:inherit}.notice{padding:10px 12px;background:var(--secondary-background-color,#f5f7f8);border-left:3px solid var(--warning-color,#c39123);border-radius:4px;margin:10px 0;overflow-wrap:anywhere}.footer{margin-top:16px;line-height:1.6;font-size:12px;color:var(--secondary-text-color,#667);overflow-wrap:anywhere}details{margin-top:12px}summary{cursor:pointer;padding:10px 0;font-size:14px}.value{font-variant-numeric:tabular-nums;font-weight:500}.chips{display:flex;gap:8px;flex-wrap:wrap}.tiny{font-size:11px}a{color:var(--primary-color,#167d7f)}
@media(max-width:900px){.charts{grid-template-columns:1fr}.health{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:480px){header{padding:18px 14px 10px}h1{font-size:22px}.body{padding:0 14px 18px}.chart{padding:12px 6px 4px}.chart svg{height:210px}.health{gap:8px}.health>div{padding:10px}th,td{padding:9px 10px}.chart h2{font-size:17px}}
`;

export class EnergyPriceEngineCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this.shadowRoot.addEventListener("click", (event) => {
      const refresh = event.target.closest?.("[data-refresh]");
      if (refresh) this._load();
      const target = event.target.closest?.("[data-start]");
      if (target) { this._selected = target.dataset.start; this._render(); }
    });
    this.shadowRoot.addEventListener("keydown", (event) => {
      if (["Enter", " "].includes(event.key) && event.target.matches("rect[data-start]")) {
        event.preventDefault(); this._selected = event.target.dataset.start; this._render();
      }
    });
    this.shadowRoot.addEventListener("change", (event) => {
      if (event.target.matches("select")) { this._selected = event.target.value; this._render(); }
    });
  }
  setConfig(config) {
    if (!config.entity || !config.entity.startsWith("sensor.")) throw new Error(WORDS.en.config);
    const changed = this._config?.entity !== config.entity;
    this._config = {...config};
    if (changed) { this._data = undefined; this._selected = undefined; this._stamp = undefined; }
    this._render();
    if (this.isConnected) this._load();
  }
  set hass(hass) {
    const state = hass.states[this._config?.entity];
    const changed = this._stamp !== state?.last_updated || this._hass?.connection !== hass.connection;
    const localeChanged = JSON.stringify(this._hass?.locale) !== JSON.stringify(hass.locale);
    this._hass = hass;
    this._stamp = state?.last_updated;
    if (this.isConnected && (!this._data || changed)) this._load();
    else if (localeChanged) this._render();
  }
  connectedCallback() {
    this._timer ??= setInterval(() => this._load(), 60000);
    this._observer ??= new ResizeObserver((entries) => {
      const width = Math.round(entries[0].contentRect.width);
      if (width !== this._width) { this._width = width; this._render(); }
    });
    this._observer.observe(this);
    this._load();
  }
  disconnectedCallback() { clearInterval(this._timer); this._timer = undefined; this._observer?.disconnect(); }
  getCardSize() { return 22; }
  static getStubConfig(hass) {
    return {entity: Object.keys(hass.states).find((id) => hass.states[id].attributes?.api_version === 1 && hass.states[id].attributes?.site_id) || "sensor.your_site_final_now"};
  }
  async _load() {
    if (!this._hass || !this._config || this._pending || !this.isConnected) return;
    this._pending = true;
    const entity = this._config.entity;
    try {
      const data = await this._hass.callWS({type: "ha_energy_price_engine/price_schedule", entity_id: entity});
      if (entity !== this._config.entity || !this.isConnected) return;
      if (data.schema_version !== 1) throw new Error("Unsupported Energy Price Engine dashboard schema");
      this._data = data; this._error = undefined;
    } catch (err) { this._error = err.message || String(err); }
    finally { this._pending = false; this._render(); }
  }
  _words() { return this._hass?.locale?.language?.startsWith("da") ? WORDS.da : WORDS.en; }
  _format(value) {
    if (!present(value)) return "—";
    const pref = this._hass?.locale?.number_format;
    const locale = ({decimal_comma: "de-DE", space_comma: "fr-FR", comma_decimal: "en-US", quote_decimal: "de-CH", none: "en-US", system: navigator.language})[pref] || this._hass?.locale?.language || "en";
    return new Intl.NumberFormat(locale, {minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: false}).format(Math.abs(value) < 0.005 ? 0 : value);
  }
  _status(value) {
    const key = ["READY", "INCOMPLETE", "STALE", "ERROR"].includes(value) ? value.toLowerCase() : "incomplete";
    return `<span class="badge ${key}">${this._words()[key]}</span>`;
  }
  _local(stamp) {
    if (!stamp) return "—";
    return new Intl.DateTimeFormat(this._hass?.locale?.language || "en", {timeZone: this._data.site.timezone, month: "short", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23", timeZoneName: "shortOffset"}).format(new Date(stamp));
  }
  _interval(row) {
    return `${row.local_start.slice(11,16)} ${row.local_start.slice(16)} → ${row.local_end.slice(11,16)} ${row.local_end.slice(16)}`;
  }
  _source(row, key) {
    const p = this._data.provenance[row.provenance];
    const part = p?.components[key];
    const source = part?.source || (key === "spot" ? (this._data.site.source_type === "nordpool" ? "Official Nord Pool" : p?.source.entity_id || "Configured spot source") : key === "dso" ? p?.source.dso?.provider : key === "vat" || key === "final" ? "Energy Price Engine · stored component snapshot" : undefined);
    const stamp = part?.verified_on || (key === "dso" ? p?.source.dso?.fetched_at : p?.source.verified_at) || (key === "spot" ? row.raw_verified_at : undefined);
    const period = part?.valid_from ? `${part.valid_from} → ${part.valid_to}` : "";
    return `${esc(source || this._words().missing)}${stamp ? `<small>${esc(this._words().checked)}: ${esc(stamp)}</small>` : ""}${period ? `<small>${esc(period)}</small>` : ""}`;
  }
  _chart(key) {
    const t = this._words(), data = this._data;
    const slots = data.days.flatMap(d => d.slots);
    const first = Date.parse(data.days[0].start), last = Date.parse(data.days[1].end);
    const hostWidth = this._width || this.getBoundingClientRect().width || 800;
    const width = Math.max(300, hostWidth > 900 ? (hostWidth - 108) / 2 : hostWidth - 76);
    const right = width - 10, span = right - 50;
    const x = (stamp) => 50 + (Date.parse(stamp) - first) / (last - first) * span;
    const good = (r) => present(r[key]) && (key === "spot" ? r.raw_status : r.status) === "READY";
    const values = slots.filter(good).map(r => r[key]);
    let low = Math.min(0, ...values), high = Math.max(0, ...values);
    if (low === high) high = low + 1;
    const range = high - low; low -= range * .10; high += range * .12;
    const y = (value) => 220 - (value - low) / (high - low) * 175;
    const zero = y(0);
    const ticks = [low + (high - low) * .15, low + (high - low) * .55, low + (high - low) * .9];
    const bars = slots.filter(good).map(r => {
      const top = y(r[key]);
      const evidence = data.provenance[r.provenance];
      const source = key === "spot" ? (data.site.source_type === "nordpool" ? "Official Nord Pool" : evidence?.source.entity_id || "Configured spot source") : "Energy Price Engine";
      const label = `${r.local_start} → ${r.local_end} · ${this._format(r[key])} øre/kWh · ${t.ready} · ${source} · ${t.checked}: ${r.raw_verified_at || "—"} · ${t.revision} ${r.revision ?? "—"}`;
      return `<rect class="bar ${key === "spot" ? "spot" : "final"}-bar" x="${x(r.start)}" y="${Math.min(top,zero)}" width="${Math.max(.6,x(r.end)-x(r.start)-.5)}" height="${Math.max(.8,Math.abs(top-zero))}" tabindex="0" role="button" data-start="${esc(r.start)}" aria-label="${esc(label)}"><title>${esc(label)}</title></rect>`;
    }).join("");
    const boundary = x(data.days[1].start);
    const now = Date.parse(data.generated_at), nx = 50 + (now-first)/(last-first)*span;
    return `<section class="chart" data-chart="${key}"><h2>${key === "spot" ? t.raw : t.final}</h2><p class="muted">${key === "spot" ? t.ex : t.incl} · øre/kWh</p><svg viewBox="0 0 ${width} 265" role="group" aria-label="${key === "spot" ? t.raw : t.final}">
      ${ticks.map(v => `<line class="gridline" x1="50" x2="${right}" y1="${y(v)}" y2="${y(v)}"/><text class="axis" x="44" y="${y(v)+4}" text-anchor="end">${esc(this._format(v))}</text>`).join("")}
      <line class="zero" x1="50" x2="${right}" y1="${zero}" y2="${zero}"/>${bars}
      <line class="boundary" x1="${boundary}" x2="${boundary}" y1="30" y2="224"/>
      <text class="axis" x="${(50+boundary)/2}" y="22" text-anchor="middle">${t.today} · ${data.days[0].date}</text><text class="axis" x="${(boundary+right)/2}" y="22" text-anchor="middle">${t.tomorrow} · ${data.days[1].date}</text>
      ${slots.filter(r => r.local_start.slice(11,16) === "00:00" || r.local_start.slice(11,16) === "12:00").map(r => `<text class="axis" x="${x(r.start)}" y="246">${r.local_start.slice(11,16)}</text>`).join("")}
      ${now >= first && now < last ? `<line class="now" x1="${nx}" x2="${nx}" y1="32" y2="224"/><text class="now-label" x="${Math.min(right-30,nx+5)}" y="40">${t.now}</text>` : ""}
    </svg></section>`;
  }
  _inspector() {
    const t = this._words(), all = this._data.days.flatMap(d => d.slots);
    const row = all.find(r => r.start === this._selected) || all.find(r => r.start === this._data.current_start) || all[0];
    this._selected = row.start;
    return `<section class="section inspector" id="inspect"><h2>${t.inspect}</h2><label class="muted" for="quarter">${t.slot}</label><select id="quarter" aria-label="${t.inspect}">${all.map(r => `<option value="${esc(r.start)}" ${r.start === row.start ? "selected" : ""}>${esc(r.local_start)} → ${esc(r.local_end)} · ${this._words()[(r.status || "INCOMPLETE").toLowerCase()] || t.incomplete}</option>`).join("")}</select>
      <div class="chips">${this._status(row.status)}<span class="muted">${t.revision} ${row.revision ?? "—"}</span></div>
      ${!present(row.final) ? `<p class="notice">${esc(row.reason || t.noRecord)}</p>` : ""}
      <div class="scroll"><table><thead><tr><th>${t.component}</th><th>${t.amount}</th><th>${t.status}</th><th>${t.source}</th></tr></thead><tbody>${KEYS.map(k => {
        const state = k === "spot" ? row.raw_status : present(row[k]) ? row.status : "INCOMPLETE";
        return `<tr><td>${esc(k === "final" ? t.finalLabel : t[k])}<small style="display:block">${k === "final" ? t.incl : k === "vat" ? "" : t.ex}</small></td><td class="numeric value">${esc(this._format(row[k]))}</td><td>${this._status(state)}</td><td class="source">${this._source(row,k)}</td></tr>`;
      }).join("")}</tbody></table></div>
      ${row.stored_final !== row.final && present(row.stored_final) ? `<p class="notice">${t.retained}: ${esc(this._format(row.stored_final))} øre/kWh</p>` : ""}
      <p class="muted">${t.utc}: ${esc(row.start)} → ${esc(row.end)}</p><p class="muted">${t.precision}</p></section>`;
  }
  _tariffs() {
    const t = this._words();
    return `<section class="section" data-table="tariffs"><h2>${t.grid}</h2><p class="muted">${this._data.site.dso_mode === "radius_c" ? "Radius C · " : ""}${this._data.days[0].date} · ${esc(this._data.site.timezone)} · ${t.applied}</p><div class="scroll"><table><thead><tr><th>${t.slot}</th><th>${t.rate}</th><th>${t.status}</th><th>${t.source}</th></tr></thead><tbody>${this._data.dso_today.map(r => `<tr><td class="time">${esc(this._interval(r))}</td><td class="numeric value">${esc(this._format(r.value))}</td><td>${this._status(r.status)}</td><td class="source">${esc(r.source || t.missing)}<small>${esc(r.verified_on || r.verified_at || "")}</small>${r.valid_from ? `<small>${esc(r.valid_from)} → ${esc(r.valid_to)}</small>` : ""}</td></tr>`).join("")}</tbody></table></div></section>`;
  }
  _schedule() {
    const t = this._words();
    return `<section class="section" data-table="schedule"><h2>${t.schedule}</h2><p class="muted">øre/kWh · ${t.ex} · ${t.finalLabel}: ${t.incl}</p>${this._data.days.map((day,i) => `<details ${i === 0 ? "open" : ""} data-day="${day.date}"><summary>${i === 0 ? t.today : t.tomorrow} · ${day.date} · ${day.ready_slots}/${day.expected_slots} ${t.verified.toLowerCase()} · ${this._status(day.status)}</summary>${day.reason ? `<p class="notice">${esc(day.reason)}</p>` : ""}<div class="scroll"><table><thead><tr><th>${t.slot}</th>${KEYS.map(k => `<th>${k === "final" ? t.finalLabel : t[k]}</th>`).join("")}<th>${t.status}</th><th>${t.revision}</th></tr></thead><tbody>${day.slots.map(r => `<tr class="${r.start === this._selected ? "selected" : ""}"><td class="time"><button data-start="${esc(r.start)}" title="${esc(r.start)}">${esc(this._interval(r))}</button></td>${KEYS.map(k => `<td class="numeric">${esc(this._format(r[k]))}${k === "spot" && r.raw_status !== "READY" && present(r[k]) ? " *" : ""}</td>`).join("")}<td>${this._status(r.status)}</td><td>${r.revision ?? "—"}</td></tr>`).join("")}</tbody></table></div></details>`).join("")}<p class="muted">* ${t.stale} · ${t.utc}: ${t.inspect}</p></section>`;
  }
  _render() {
    if (!this.shadowRoot || !this._config) return;
    // Keep expanded days/scroll positions across the once-per-minute update.
    const hadDetails = !!this.shadowRoot.querySelector("details");
    const active = this.shadowRoot.activeElement;
    const focusId = active?.id;
    const focusStart = active?.dataset?.start;
    const focusChart = active?.closest?.("[data-chart]")?.dataset.chart;
    const open = new Set([...this.shadowRoot.querySelectorAll("details[open]")].map(e => e.dataset.day));
    const scrolls = [...this.shadowRoot.querySelectorAll(".scroll")].map(e => [e.scrollLeft,e.scrollTop]);
    const t = this._words(), d = this._data;
    const body = d ? `<header><div><div class="eyebrow">Energy Price Engine · ${esc(d.site.area)}</div><h1>${esc(d.site.name)}</h1><div class="muted">${esc(d.site.timezone)} · øre/kWh</div></div><button data-refresh aria-label="${t.retry}">${t.retry}</button></header><div class="body"><div class="health">${[[t.current,d.current],[t.next,d.next],[t.history,d.days[0]],[t.publication,d.days[1]]].map(([name,f]) => `<div><p>${name}</p>${this._status(f.status)}<p class="muted" style="margin-top:6px">${f.stored_slots}/${f.expected_slots}</p></div>`).join("")}</div>
      ${this._error ? `<p role="alert" class="notice error">${esc(this._error)}</p>` : ""}
      ${d.days.map((day,i) => day.status !== "READY" ? `<div class="notice"><strong>${i === 0 ? t.today : t.tomorrow} · ${this._words()[day.status.toLowerCase()] || t.incomplete}</strong><p>${esc(day.reason || t.noRecord)}</p>${i === 1 && day.status === "INCOMPLETE" && day.failure_stage === "source" && day.raw_ready_slots === 0 ? `<p>${t.wait}</p>` : ""}<p>${t.update}: ${esc(this._local(d.next_scheduled_update))}</p>${day.required_action ? `<p>${t.fix}: ${esc(day.required_action)}</p>` : ""}${day.missing_components.length ? `<p>${esc(day.missing_components.map(k => t[k] || k).join(", "))}</p>` : ""}</div>` : "").join("")}
      <div class="charts">${this._chart("spot")}${this._chart("final")}</div><p class="muted">${t.gaps} ${t.rawOnly}</p>${this._inspector()}${this._tariffs()}${this._schedule()}<footer class="footer">${t.update}: ${esc(this._local(d.next_scheduled_update))}<br>${t.generated}: ${esc(this._local(d.generated_at))} · ${t.revision} ${d.revision}</footer></div>` : `<header><h1>${t.title}</h1></header><div class="body"><p role="status">${esc(this._error || t.loading)}</p><button data-refresh>${t.retry}</button></div>`;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style><ha-card>${body}</ha-card>`;
    if (hadDetails) for (const e of this.shadowRoot.querySelectorAll("details")) e.open = open.has(e.dataset.day);
    [...this.shadowRoot.querySelectorAll(".scroll")].forEach((e,i) => { if (scrolls[i]) [e.scrollLeft,e.scrollTop] = scrolls[i]; });
    const focus = focusId ? this.shadowRoot.getElementById(focusId) : focusStart ? this.shadowRoot.querySelector(`${focusChart ? `[data-chart="${CSS.escape(focusChart)}"] ` : ""}[data-start="${CSS.escape(focusStart)}"]`) : null;
    focus?.focus({preventScroll: true});
  }
}
if (!customElements.get("energy-price-engine-card")) customElements.define("energy-price-engine-card", EnergyPriceEngineCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === "energy-price-engine-card")) window.customCards.push({type: "energy-price-engine-card", name: "Energy Price Engine", description: "Stored today/tomorrow spot, final prices, tariffs and components", preview: false});
