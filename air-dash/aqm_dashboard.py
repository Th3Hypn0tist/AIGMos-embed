#!/usr/bin/env python3
"""AirQualityMonitorSystem: read-only PostgreSQL dashboard, v1.0.14."""
import argparse
import getpass
import json
import logging
import math
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

VERSION = '1.0.14'
# (window seconds, bucket seconds); zero means original stored samples.
RANGES = {'15m': (900, 0), '1h': (3600, 0), '6h': (21600, 30),
          '24h': (86400, 120), '7d': (604800, 600), '30d': (2592000, 3600),
          '90d': (7776000, 10800)}
METRICS = ('temperature_c', 'bmp_temperature_c', 'humidity_rh',
           'pressure_hpa', 'eco2_ppm', 'tvoc_ppb')
NODE_ID = re.compile(r'[0-9a-f]{12}\Z')
DB = {}


def connect():
    import psycopg
    from psycopg.rows import dict_row
    return psycopg.connect(**DB, row_factory=dict_row, autocommit=True,
                           connect_timeout=4,
                           options='-c default_transaction_read_only=on -c statement_timeout=15000')


def utcnow():
    return datetime.now(timezone.utc)


def clean(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        # PostgreSQL avg(integer) returns numeric, decoded as Decimal.
        value = float(value) if value.is_finite() else None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def live():
    with connect() as conn:
        rows = conn.execute('''
            SELECT n.node_id, n.name, n.location, n.platform, n.firmware_version,
                   n.first_seen, n.last_seen, s.received_at, s.boot_id, s.seq,
                   s.uptime_ms, s.temperature_c, s.bmp_temperature_c, s.humidity_rh,
                   s.pressure_hpa, s.eco2_ppm, s.tvoc_ppb, s.ccs_warming_up,
                   s.ccs_error, s.humidity_chip, s.humidity_diag, s.rssi_dbm
            FROM aqm.nodes n
            LEFT JOIN LATERAL (
                SELECT * FROM aqm.samples s WHERE s.node_id = n.node_id
                ORDER BY received_at DESC LIMIT 1
            ) s ON true
            ORDER BY n.node_id
        ''').fetchall()
    return {'now': utcnow(), 'nodes': rows, 'version': VERSION}


def range_params(window):
    # Retain old API presets and numeric minutes; new UI sends dd:hh:mm:ss.
    if window in RANGES:
        return RANGES[window]
    if re.fullmatch(r'[0-9]{1,2}:[0-9]{2}:[0-9]{2}:[0-9]{2}', window):
        days, hours, minutes, secs = map(int, window.split(':'))
        if hours > 23 or minutes > 59 or secs > 59:
            raise ValueError('Invalid duration component')
        seconds = days * 86400 + hours * 3600 + minutes * 60 + secs
    elif re.fullmatch(r'[0-9]{1,6}', window):
        seconds = int(window) * 60
    else:
        raise ValueError('Invalid time range')
    if not 1 <= seconds <= 90 * 86400:
        raise ValueError('Time range must be 1 second to 90 days')
    bucket = next(b for limit, b in RANGES.values() if seconds <= limit)
    return seconds, bucket


def offset_seconds(value):
    if not re.fullmatch(r'[0-9]{1,2}:[0-9]{2}:[0-9]{2}:[0-9]{2}', value):
        raise ValueError('Invalid start offset')
    days, hours, minutes, secs = map(int, value.split(':'))
    seconds = days * 86400 + hours * 3600 + minutes * 60 + secs
    if hours > 23 or minutes > 59 or secs > 59 or seconds > 90 * 86400:
        raise ValueError('Start offset must be 0 seconds to 90 days')
    return seconds


def history(window, nodes, offset='00:00:00:00'):
    seconds, bucket = range_params(window)
    now = utcnow()
    # Nonzero offset anchors the beginning of the window relative to now.
    # Zero retains live mode: show the latest full timeframe.
    age = offset_seconds(offset)
    start = now - timedelta(seconds=age or seconds)
    end = min(now, start + timedelta(seconds=seconds))
    bucket = next(b for limit, b in RANGES.values() if (end - start).total_seconds() <= limit)
    where = 'received_at >= %s AND received_at <= %s'
    cal_where = 'observed_at >= %s AND observed_at <= %s'
    params = [start, end]
    if nodes:
        where += ' AND node_id = ANY(%s)'
        cal_where += ' AND node_id = ANY(%s)'
        params.append(nodes)
    if bucket:
        # Only the fixed column names and a whitelisted bucket interval are used.
        fields = ', '.join(f'avg({m}) AS {m}' for m in METRICS)
        query = f'''SELECT time_bucket(%s::interval, received_at) AS t, node_id,
                           {fields}, avg(bmp_temperature_c - temperature_c) AS delta_c,
                           count(*) AS sample_count
                    FROM aqm.samples WHERE {where}
                    GROUP BY 1, 2 ORDER BY 1, 2'''
        query_params = [f'{bucket} seconds', *params]
    else:
        query = f'''SELECT received_at AS t, node_id, {', '.join(METRICS)},
                           bmp_temperature_c - temperature_c AS delta_c,
                           1 AS sample_count
                    FROM aqm.samples WHERE {where} ORDER BY received_at, node_id'''
        query_params = params
    with connect() as conn:
        rows = conn.execute(query, query_params).fetchall()
        # Fetch newest observations within the chosen time window; keep their raw values.
        cal = conn.execute(f'''SELECT observation_id, observed_at, node_id,
                                      raw_temperature_c, raw_bmp_temperature_c,
                                      raw_humidity_rh, laser_meter_c
                               FROM aqm.calibration_observations WHERE {cal_where}
                               AND laser_meter_c IS NOT NULL
                               ORDER BY observed_at DESC, observation_id DESC LIMIT 101''',
                           params).fetchall()
        # Current calibration is independent of the selected chart window.
        # Use the newest paired laser measurement for each node and sensor.
        offset_where = 'observed_at <= %s AND laser_meter_c IS NOT NULL'
        offset_params = [now]
        if nodes:
            offset_where += ' AND node_id = ANY(%s)'
            offset_params.append(nodes)
        offsets = {}
        for metric, raw in (('temperature_c', 'raw_temperature_c'),
                            ('bmp_temperature_c', 'raw_bmp_temperature_c')):
            latest = conn.execute(f'''SELECT DISTINCT ON (node_id) node_id,
                                      observed_at, observation_id,
                                      laser_meter_c - {raw} AS offset_c
                                      FROM aqm.calibration_observations
                                      WHERE {offset_where} AND {raw} IS NOT NULL
                                      ORDER BY node_id, observed_at DESC, observation_id DESC''',
                                  offset_params).fetchall()
            for row in latest:
                offsets.setdefault(row['node_id'], {})[metric] = row
    return {'start': start, 'end': end, 'bucket_seconds': bucket,
            'samples': rows, 'offsets': offsets, 'calibration': cal[:100],
            'calibration_truncated': len(cal) > 100}


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>AirQualityMonitorSystem</title>
<style>
:root{color-scheme:dark;--bg:#090e16;--panel:#111a27;--line:#26364a;--text:#e5edf7;--muted:#8c9fb6;--accent:#55dfb2;--warn:#ffbd69;--bad:#ff8d83}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif;font-variant-numeric:tabular-nums}main{width:100%;margin:auto;padding:16px 20px 40px}.dashboard{display:flex;flex-direction:column;min-height:calc(100vh - 32px);min-height:calc(100dvh - 32px)}header{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:nowrap}header .badge{flex-shrink:0}header h1{min-width:0}h1{font-size:clamp(23px,3vw,29px);letter-spacing:-.04em;margin:3px 0}h2{font-size:17px;margin:0 0 12px}h3{font-size:14px;margin:0}.muted{color:var(--muted)}.small{font-size:12px}.badge{border:1px solid var(--line);border-radius:7px;padding:7px 11px;white-space:nowrap;color:var(--muted)}.ok{color:var(--accent)}.bad{color:var(--bad)}.warn{color:var(--warn)}.section{margin:15px 0 8px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.section h2{margin:0}.card{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:16px;min-width:0}.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}button{font:inherit;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 11px;cursor:pointer}button.active{color:var(--accent);border-color:var(--accent)}button:hover{color:var(--text)}.selector{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;margin-bottom:0;flex-shrink:0}.selector label{display:flex;align-items:center;gap:7px;padding:6px 10px;background:var(--panel);border:1px solid var(--line);border-radius:6px;cursor:pointer}input{accent-color:var(--accent)}.duration{display:inline-flex;align-items:center;gap:4px}.duration input{width:3.7em;font:inherit;font-variant-numeric:tabular-nums;text-align:center;color:var(--text);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 2px}.duration input:focus{border-color:var(--accent)}.charts{display:flex;flex-wrap:nowrap;gap:6px;width:100%;min-width:0;margin-bottom:8px}.chart-preview{flex:1 1 0;min-width:0;padding:6px;background:var(--panel);border:1px solid var(--line);border-radius:6px;text-align:left;overflow:hidden;color:var(--text)}.chart-preview[aria-pressed=true]{border-color:var(--accent);color:var(--accent)}.chart-preview:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.chart-preview .preview-label{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:12px;font-weight:650}.chart-preview .plot{height:76px;pointer-events:none}.focus-chart{display:flex;flex-direction:column;flex:1 0 auto;min-height:280px;padding:12px;min-width:0}.focus-chart .plot{flex:1 0 0;height:0;min-height:220px}.focus-chart .legend{flex-shrink:0}.chart-time-range{flex-shrink:0;text-align:center;color:var(--muted);font-size:12px;padding-top:4px;overflow-wrap:anywhere}.chart{position:relative}.chart h3{margin-bottom:4px}.legend{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:11px;color:var(--muted);min-height:20px}.legend span{display:inline-flex;gap:6px;align-items:center}.swatch{width:18px;border-top:2px solid currentColor;display:inline-block}.swatch.dash{border-top-style:dashed}.swatch.dot{width:7px;height:7px;border-radius:50%;background:currentColor;border:0}.plot{width:100%;height:235px;display:block;touch-action:pan-y}.tip{position:absolute;pointer-events:none;z-index:2;max-width:calc(100% - 20px);background:#080d15;border:1px solid #40556e;border-radius:6px;padding:8px 10px;font-size:11px;box-shadow:0 5px 15px #0007;white-space:pre-line}.tip[hidden]{display:none}table{width:100%;border-collapse:collapse;white-space:nowrap;text-align:right;font-size:12px}th,td{padding:9px 10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}footer{margin-top:25px;color:var(--muted);font-size:12px}#error{color:var(--bad);margin:8px 0;white-space:pre-wrap}#error:empty{display:none}.empty{padding:24px;color:var(--muted);text-align:center}@media(max-width:800px){main{padding:12px 10px 30px}.dashboard{min-height:calc(100dvh - 24px)}.charts{gap:3px}.chart-preview{padding:3px}.chart-preview .plot{height:52px}.chart-preview .preview-label{font-size:10px}header{gap:8px}header h1{font-size:clamp(17px,4.5vw,23px)}header .badge{font-size:11px;padding:5px 7px}}
</style></head><body><main><div class="dashboard">
<header><h1>Air quality monitor</h1><div id="db" class="badge" role="status">Connecting…</div></header>
<div id="error" role="status"></div>
<div class="section"><div class="controls"><span id="offset-label">Start offset from now (0 = live)</span><span class="duration" role="group" aria-labelledby="offset-label"><input id="offset-days" aria-label="Start offset days" type="number" min="0" max="90" step="1" value="00" required>:<input id="offset-hours" aria-label="Start offset hours" type="number" min="0" max="23" step="1" value="00" required>:<input id="offset-minutes" aria-label="Start offset minutes" type="number" min="0" max="59" step="1" value="00" required>:<input id="offset-seconds" aria-label="Start offset seconds" type="number" min="0" max="59" step="1" value="00" required></span></div><div class="controls"><span id="duration-label">Timeframe (dd:hh:mm:ss)</span><span class="duration" role="group" aria-labelledby="duration-label"><input id="range-days" aria-label="Days" type="number" min="0" max="90" step="1" value="00" required>:<input id="range-hours" aria-label="Hours" type="number" min="0" max="23" step="1" value="01" required>:<input id="range-minutes" aria-label="Minutes" type="number" min="0" max="59" step="1" value="00" required>:<input id="range-seconds" aria-label="Seconds" type="number" min="0" max="59" step="1" value="00" required></span></div></div>
<section id="charts" class="charts" role="group" aria-label="Select chart"></section>
<section id="focus-chart" class="card chart focus-chart" aria-label="Selected chart"><div id="chart-time-range" class="chart-time-range"></div></section>
<div id="selector" class="selector" role="group" aria-label="Select nodes"></div>
</div>
<footer>AirQualityMonitorSystem v1.0.14 · Node discovery every 1 s · History refresh every 1 s · eCO₂ is a VOC-derived estimate, not measured CO₂.</footer>
</main><script>
'use strict';
const $=id=>document.getElementById(id);
const el=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e};
const finite=Number.isFinite, fmt=(v,d=1)=>finite(v)?v.toFixed(d):'—';
const local=t=>t?new Date(t).toLocaleString('en-GB'):'—';
const palette=['#55dfb2','#65b6ff','#ffbd69','#c6a5ff','#ff8e9d','#78dbe8','#d1dd72','#f5a9df'];
const colors=new Map();let nodes=[],selected=new Set(),known=new Set(),windowKey='00:01:00:00',offsetKey='00:00:00:00',hist=null,liveBusy=false,historyBusy=false,historyPending=false,revision=0;
const errors={live:'',history:''};
const label=n=>(n.name||'').trim()||n.node_id;
const name=id=>label(nodes.find(n=>n.node_id===id)||{node_id:id});
function color(id){if(!colors.has(id))colors.set(id,palette[colors.size%palette.length]);return colors.get(id)}
function setError(k,msg){errors[k]=msg;$('error').textContent=Object.values(errors).filter(Boolean).join('\n')}
async function api(path){const r=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(22000)});if(!r.ok)throw Error('HTTP '+r.status);return r.json()}
function renderSelector(){const root=$('selector');root.replaceChildren();if(!nodes.length){root.append(el('span','muted small','No nodes registered'));return}for(const n of nodes){const l=el('label');const box=el('input');box.type='checkbox';box.checked=selected.has(n.node_id);box.addEventListener('change',()=>{box.checked?selected.add(n.node_id):selected.delete(n.node_id);revision++;requestHistory()});const sw=el('i','swatch');sw.style.color=color(n.node_id);l.append(box,sw,document.createTextNode(label(n)));root.append(l)}}
async function refreshLive(){if(liveBusy)return;liveBusy=true;try{const d=await api('/api/live');const old=nodes.map(n=>[n.node_id,n.name]);nodes=d.nodes;let changed=false;for(const n of nodes){if(!known.has(n.node_id)){known.add(n.node_id);selected.add(n.node_id);changed=true}color(n.node_id)}for(const id of [...known])if(!nodes.some(n=>n.node_id===id)){selected.delete(id);known.delete(id);changed=true}if(changed||JSON.stringify(old)!==JSON.stringify(nodes.map(n=>[n.node_id,n.name])))renderSelector();$('db').className='badge ok';$('db').textContent='DATABASE ONLINE';setError('live','');if(changed){revision++;requestHistory()}}catch(e){$('db').className='badge bad';$('db').textContent='DATABASE UNAVAILABLE';setError('live','Live data unavailable: '+e.message+' · displayed values may be stale.')}finally{liveBusy=false}}
const chartSpecs=[
 {short:'Temp',title:'Temperature (BMP280 primary; laser corrected where available)',unit:'°C',series:[['bmp_temperature_c','BMP280 (primary)',false],['temperature_c','RH sensor (secondary)',true]]},
 {short:'ΔT',title:'Temperature difference (corrected when both offsets exist)',unit:'°C',series:[['delta_c','BMP − RH sensor',false]]},
 {short:'RH',title:'Relative humidity',unit:'%',series:[['humidity_rh','RH',false]]},
 {short:'Pressure',title:'Atmospheric pressure',unit:'hPa',series:[['pressure_hpa','Pressure',false]]},
 {short:'eCO₂',title:'Estimated CO₂',unit:'ppm',series:[['eco2_ppm','eCO₂',false]]},
 {short:'TVOC',title:'Volatile organic compounds',unit:'ppb',series:[['tvoc_ppb','TVOC',false]]}
];
const charts=[];
const focusCard=$('focus-chart');
const focusTitle=el('h3','',chartSpecs[0].title);
const focusLegend=el('div','legend');
const focusCanvas=el('canvas','plot');
const focusTip=el('div','tip');focusTip.hidden=true;
focusCard.prepend(focusTitle,focusLegend,focusCanvas);focusCard.append(focusTip);
const focusChart={spec:chartSpecs[0],card:focusCard,legend:focusLegend,canvas:focusCanvas,tip:focusTip,layout:null,preview:false};
charts.push(focusChart);
focusCanvas.addEventListener('pointermove',e=>hover(focusChart,e));
focusCanvas.addEventListener('pointerleave',()=>{focusTip.hidden=true});
new ResizeObserver(()=>draw(focusChart)).observe(focusCanvas);
const previews=[];
function selectChart(index){
 const spec=chartSpecs[index];
 if(!spec)return;
 for(let i=0;i<previews.length;i++)previews[i].card.setAttribute('aria-pressed',String(i===index));
 focusChart.spec=spec;focusChart.layout=null;focusTip.hidden=true;
 focusTitle.textContent=spec.title;
 focusCanvas.setAttribute('aria-label',spec.title+' time series');
 draw(focusChart);
}
for(const [index,spec] of chartSpecs.entries()){
 const card=el('button','chart-preview');card.type='button';card.title=spec.title;
 card.setAttribute('aria-label',spec.title);card.setAttribute('aria-controls','focus-chart');
 card.append(el('span','preview-label',spec.short||spec.title));
 const canvas=el('canvas','plot');canvas.setAttribute('aria-hidden','true');
 card.append(canvas);$('charts').append(card);
 const c={spec,card,legend:null,canvas,tip:null,layout:null,preview:true};
 previews.push(c);charts.push(c);
 card.addEventListener('click',()=>selectChart(index));
 new ResizeObserver(()=>draw(c)).observe(canvas);
}
selectChart(0);
const durationInputs=['days','hours','minutes','seconds'].map(k=>$('range-'+k));
function durationSeconds(key){
 const [d,h,m,s]=key.split(':').map(Number);
 return d*86400+h*3600+m*60+s;
}
function windowBounds(now,range,offset){
 const duration=durationSeconds(range)*1000,age=durationSeconds(offset)*1000;
 const start=now-(age||duration);
 return [start,Math.min(now,start+duration)];
}
function resetDuration(){
 windowKey.split(':').forEach((v,i)=>{durationInputs[i].value=v});
}
function applyDuration(){
 for(const input of durationInputs){
  if(!input.checkValidity()){input.reportValidity();resetDuration();return}
 }
 const next=durationInputs.map(input=>String(input.valueAsNumber).padStart(2,'0')).join(':');
 const seconds=durationSeconds(next);
 if(seconds<1||seconds>90*86400){
  const input=durationInputs[0];
  input.setCustomValidity('Choose a duration from 1 second to 90 days.');
  input.reportValidity();input.setCustomValidity('');resetDuration();return;
 }
 windowKey=next;resetDuration();revision++;requestHistory();
}
for(const input of durationInputs){
 input.addEventListener('change',applyDuration);
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();input.blur()}});
}
const offsetInputs=['days','hours','minutes','seconds'].map(k=>$('offset-'+k));
function resetOffset(){
 offsetKey.split(':').forEach((v,i)=>{offsetInputs[i].value=v});
}
function applyOffset(){
 for(const input of offsetInputs){
  if(!input.checkValidity()){input.reportValidity();resetOffset();return}
 }
 const next=offsetInputs.map(input=>String(input.valueAsNumber).padStart(2,'0')).join(':');
 const seconds=durationSeconds(next);
 if(seconds<0||seconds>90*86400){
  const input=offsetInputs[0];
  input.setCustomValidity('Choose a start offset from 0 seconds to 90 days.');
  input.reportValidity();input.setCustomValidity('');resetOffset();return;
 }
 offsetKey=next;resetOffset();revision++;requestHistory();
}
for(const input of offsetInputs){
 input.addEventListener('change',applyOffset);
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();input.blur()}});
}
function offsetFor(id,key){
 const value=hist?.offsets?.[id]?.[key]?.offset_c;
 return finite(value)?value:null;
}
function chartCorrection(id,key){
 if(key==='temperature_c'||key==='bmp_temperature_c')return offsetFor(id,key);
 if(key==='delta_c'){
  const rh=offsetFor(id,'temperature_c'),bmp=offsetFor(id,'bmp_temperature_c');
  return rh!==null&&bmp!==null?bmp-rh:null;
 }
 return null;
}
function linesFor(spec){
 if(!hist)return[];
 const groups=new Map();
 for(const row of hist.samples){
  if(!groups.has(row.node_id))groups.set(row.node_id,[]);
  groups.get(row.node_id).push(row);
 }
 const out=[];
 for(const [id,rows] of groups){
  for(const [key,l,dash] of spec.series){
   const temperature=['temperature_c','bmp_temperature_c','delta_c'].includes(key);
   const correction=chartCorrection(id,key);
   const suffix=temperature?(correction===null?' (raw; no paired reference)':` (offset ${correction>=0?'+':''}${fmt(correction,2)} °C)`):'';
   out.push({label:name(id)+' · '+l+suffix,color:color(id),dash,
     points:rows.map(r=>[Date.parse(r.t),finite(r[key])?r[key]+(correction??0):null])});
  }
 }
 return out;
}
function tickTime(t,span){return new Date(t).toLocaleString('en-GB',span>86400000?{day:'2-digit',month:'short'}:span<=300000?{hour:'2-digit',minute:'2-digit',second:'2-digit'}:{hour:'2-digit',minute:'2-digit'})}
function draw(c){const {canvas,spec,legend}=c;const w=canvas.clientWidth,h=canvas.clientHeight;if(w<1||h<1)return;const dpr=window.devicePixelRatio||1;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.font='11px system-ui';ctx.fillStyle='#8c9fb6';const lines=linesFor(spec);if(legend){legend.replaceChildren();for(const l of lines){const s=el('span');const sw=el('i','swatch'+(l.dash?' dash':l.shape?' dot':''));sw.style.color=l.color;if(l.shape==='square')sw.style.borderRadius='0';s.append(sw,document.createTextNode(l.label));legend.append(s)}}
 let lo=Infinity,hi=-Infinity;for(const l of lines)for(const [t,v] of l.points)if(finite(v)){lo=Math.min(lo,v);hi=Math.max(hi,v)}if(!hist||!finite(lo)){ctx.textAlign='center';ctx.fillText(c.preview?'—':'No samples in selected range',w/2,h/2);c.layout=null;return}
 const pad=Math.max((hi-lo)*.1,spec.unit==='°C'?.15:spec.unit==='%'?.5:spec.unit==='hPa'?.15:1)/3;lo-=pad;hi+=pad;const start=Date.parse(hist.start)-(hist.bucket_seconds||0)*1000,end=Date.parse(hist.end);const left=c.preview?3:59,right=w-(c.preview?3:12),top=c.preview?3:10,bottom=h-(c.preview?3:28);if(right<=left||bottom<=top){c.layout=null;return}const X=t=>left+(t-start)/(end-start)*(right-left),Y=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
 if(!c.preview){ctx.textAlign='right';ctx.textBaseline='middle';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);ctx.strokeStyle='#26364a';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle='#8c9fb6';ctx.fillText(v.toFixed(spec.unit==='ppm'||spec.unit==='ppb'?0:1),left-7,y)}ctx.textAlign='left';ctx.fillText(spec.unit,2,8);ctx.textBaseline='top';const ticks=w<420?3:5;for(let i=0;i<ticks;i++){const t=start+(end-start)*i/(ticks-1);ctx.textAlign=i===0?'left':i===ticks-1?'right':'center';ctx.fillText(tickTime(t,end-start),X(t),bottom+8)}}
 ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();const maxGap=(hist.bucket_seconds?hist.bucket_seconds*2.1:15)*1000;for(const l of lines){ctx.strokeStyle=l.color;ctx.fillStyle=l.color;ctx.lineWidth=c.preview?1.2:1.7;ctx.setLineDash(l.dash?[5,4]:[]);if(l.shape){for(const [t,v] of l.points){if(!finite(v))continue;ctx.beginPath();if(l.shape==='square')ctx.rect(X(t)-3,Y(v)-3,6,6);else ctx.arc(X(t),Y(v),3.5,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#090e16';ctx.stroke()}continue}ctx.beginPath();let prev=null;for(const [t,v] of l.points){if(!finite(v)){prev=null;continue}if(prev===null||t-prev>maxGap)ctx.moveTo(X(t),Y(v));else ctx.lineTo(X(t),Y(v));prev=t}ctx.stroke();ctx.setLineDash([]);if(l.points.filter(p=>finite(p[1])).length===1){const [t,v]=l.points.find(p=>finite(p[1]));ctx.beginPath();ctx.arc(X(t),Y(v),2.5,0,Math.PI*2);ctx.fill()}}ctx.restore();c.layout={start,end,left,right,lines};
}
function nearest(points,t){let a=0,b=points.length;while(a<b){const m=(a+b)>>1;if(points[m][0]<t)a=m+1;else b=m}const p=points[a],q=points[a-1];return !q?p:!p?q:Math.abs(p[0]-t)<Math.abs(q[0]-t)?p:q}
function hover(c,e){if(!c.layout){c.tip.hidden=true;return}const {start,end,left,right,lines}=c.layout;const r=c.canvas.getBoundingClientRect(),x=e.clientX-r.left;if(x<left||x>right){c.tip.hidden=true;return}const t=start+(x-left)/(right-left)*(end-start);const tolerance=Math.max((end-start)/(right-left)*8,(hist.bucket_seconds||5)*1000);const vals=[];for(const l of lines){const p=nearest(l.points,t);if(p&&finite(p[1])&&Math.abs(p[0]-t)<=tolerance)vals.push(`${l.label}: ${fmt(p[1],2)} ${c.spec.unit} (${tickTime(p[0],end-start)})`)}if(!vals.length){c.tip.hidden=true;return}c.tip.textContent=local(t)+'\n'+vals.join('\n');c.tip.hidden=false;const cr=c.card.getBoundingClientRect();c.tip.style.left=Math.max(8,Math.min(e.clientX-cr.left+10,c.card.clientWidth-c.tip.offsetWidth-8))+'px';c.tip.style.top=Math.max(8,e.clientY-cr.top-c.tip.offsetHeight-10)+'px'}
function renderHistory(){$('chart-time-range').textContent=local(hist.start)+' — '+local(hist.end);for(const c of charts)draw(c)}
async function requestHistory(){if(historyBusy){historyPending=true;return}historyBusy=true;const rev=revision;try{if(!selected.size){const [start,end]=windowBounds(Date.now(),windowKey,offsetKey);hist={start:new Date(start).toISOString(),end:new Date(end).toISOString(),samples:[],offsets:{},calibration:[],bucket_seconds:0};renderHistory();setError('history','');return}const q=new URLSearchParams({range:windowKey,offset:offsetKey});for(const id of selected)q.append('node',id);const d=await api('/api/history?'+q);if(rev!==revision)return;hist=d;renderHistory();setError('history','')}catch(e){if(rev===revision){setError('history','History unavailable: '+e.message)}}finally{historyBusy=false;if(historyPending){historyPending=false;requestHistory()}}}
refreshLive().then(()=>{if(!hist&&!historyBusy)requestHistory()});setInterval(refreshLive,1000);setInterval(()=>{if(!historyBusy)requestHistory()},1000);
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, data, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def json(self, status, obj):
        self.respond(status, json.dumps(clean(obj), allow_nan=False, separators=(',', ':')).encode(),
                     'application/json; charset=utf-8')

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/':
            self.respond(200, HTML.encode(), 'text/html; charset=utf-8')
            return
        if url.path == '/favicon.ico':
            self.respond(204, b'', 'image/x-icon')
            return
        try:
            if url.path == '/api/live':
                self.json(200, live())
            elif url.path == '/api/history':
                try:
                    q = parse_qs(url.query, max_num_fields=128)
                    window = q.get('range', ['00:01:00:00'])[0]
                    nodes = list(dict.fromkeys(q.get('node', [])))
                    range_params(window)
                    offset = q.get('offset', ['00:00:00:00'])[0]
                    offset_seconds(offset)
                    if any(not NODE_ID.fullmatch(n) for n in nodes):
                        raise ValueError('Invalid range or node ID')
                except ValueError as e:
                    self.json(400, {'error': str(e)})
                    return
                self.json(200, history(window, nodes, offset))
            else:
                self.json(404, {'error': 'Not found'})
        except Exception:
            logging.exception('Database/API request failed')
            self.json(503, {'error': 'Database unavailable; see server log'})

    def log_message(self, fmt, *args):
        # Avoid logging each polling request; log HTTP errors only.
        if len(args) >= 2 and str(args[1]).startswith(('4', '5')):
            super().log_message(fmt, *args)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind', default='0.0.0.0')
    p.add_argument('--port', type=int, default=8080)
    p.add_argument('--db-host', default=os.getenv('AQM_DB_HOST', '127.0.0.1'))
    p.add_argument('--db-port', type=int, default=int(os.getenv('AQM_DB_PORT', '5432')))
    p.add_argument('--db-name', default=os.getenv('AQM_DB_NAME', 'AirQualityMon'))
    p.add_argument('--db-user', default=os.getenv('AQM_DB_USER', 'aqm_dashboard'))
    args = p.parse_args()
    try:
        import psycopg  # noqa: F401
    except ImportError:
        p.exit(1, 'Install psycopg: sudo apt install python3-psycopg\n')
    password = os.getenv('AQM_DB_PASSWORD')
    if password is None:
        password = getpass.getpass(f'PostgreSQL password for {args.db_user}: ')
    DB.update(host=args.db_host, port=args.db_port, dbname=args.db_name,
              user=args.db_user, password=password, application_name='aqm_dashboard')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    try:
        d = live()
        logging.info('Database connected: %d registered nodes', len(d['nodes']))
    except Exception as e:
        logging.error('Initial database check failed: %s', e)
        p.exit(1, 'Check PostgreSQL credentials, pg_hba.conf and dashboard grants.\n')
    with ThreadingHTTPServer((args.bind, args.port), Handler) as server:
        logging.info('AirQualityMonitor dashboard %s listening on %s:%s', VERSION, args.bind, args.port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
    main()
