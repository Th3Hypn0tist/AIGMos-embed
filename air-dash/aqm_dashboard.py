#!/usr/bin/env python3
"""AirQualityMonitorSystem: read-only PostgreSQL dashboard, v1.0.1."""
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

VERSION = '1.0.1'
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


def history(window, nodes):
    seconds, bucket = RANGES[window]
    end = utcnow()
    start = end - timedelta(seconds=seconds)
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
                                      raw_humidity_rh, thermal_camera_c, laser_meter_c
                               FROM aqm.calibration_observations WHERE {cal_where}
                               ORDER BY observed_at DESC, observation_id DESC LIMIT 101''',
                           params).fetchall()
    return {'start': start, 'end': end, 'bucket_seconds': bucket,
            'samples': rows, 'calibration': cal[:100], 'calibration_truncated': len(cal) > 100}


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><title>AirQualityMonitorSystem</title>
<style>
:root{color-scheme:dark;--bg:#090e16;--panel:#111a27;--line:#26364a;--text:#e5edf7;--muted:#8c9fb6;--accent:#55dfb2;--warn:#ffbd69;--bad:#ff8d83}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.5 system-ui,sans-serif;font-variant-numeric:tabular-nums}main{max-width:1500px;margin:auto;padding:16px 20px 40px}header{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;margin-bottom:12px}h1{font-size:clamp(23px,3vw,29px);letter-spacing:-.04em;margin:3px 0}h2{font-size:17px;margin:0 0 12px}h3{font-size:14px;margin:0}.eyebrow{font-size:11px;color:var(--accent);font-weight:750;letter-spacing:.15em;text-transform:uppercase}.muted{color:var(--muted)}.small{font-size:12px}.badge{border:1px solid var(--line);border-radius:7px;padding:7px 11px;white-space:nowrap;color:var(--muted)}.ok{color:var(--accent)}.bad{color:var(--bad)}.warn{color:var(--warn)}.section{margin:15px 0 8px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}.section h2{margin:0}.nodes{border:1px solid var(--line);background:var(--panel);border-radius:8px;overflow:auto}.card{border:1px solid var(--line);background:var(--panel);border-radius:10px;padding:16px;min-width:0}.live-table{min-width:920px;font-size:12px}.live-table th,.live-table td{padding:7px 10px;vertical-align:middle}.live-table th{font-size:10px;line-height:1.3}.live-table tr:last-child td{border-bottom:0}.live-table .node-name{font-weight:700;display:flex;align-items:center;gap:7px}.node-dot{display:inline-block;width:7px;height:7px;border-radius:50%;flex:none}.live-table .node-meta{font-size:10px;color:var(--muted)}.live-table .live-value{font-size:15px;font-weight:600}.live-table .live-status{font-size:11px;font-weight:650}.live-table .diag-button{font-size:11px;padding:3px 7px}.live-table .diag-row td{text-align:left;color:var(--muted);white-space:normal;background:var(--bg);font-size:12px}.diag-row[hidden]{display:none}.diag-line{display:flex;flex-wrap:wrap;gap:6px 22px}.live-table .stale-row .live-value{color:var(--muted)}.controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center}button{font:inherit;color:var(--muted);background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px 11px;cursor:pointer}button.active{color:var(--accent);border-color:var(--accent)}button:hover{color:var(--text)}.selector{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px}.selector label{display:flex;align-items:center;gap:7px;padding:6px 10px;background:var(--panel);border:1px solid var(--line);border-radius:6px;cursor:pointer}input{accent-color:var(--accent)}.charts{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.chart{position:relative}.chart h3{margin-bottom:4px}.legend{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:11px;color:var(--muted);min-height:20px}.legend span{display:inline-flex;gap:6px;align-items:center}.swatch{width:18px;border-top:2px solid currentColor;display:inline-block}.swatch.dash{border-top-style:dashed}.swatch.dot{width:7px;height:7px;border-radius:50%;background:currentColor;border:0}.plot{width:100%;height:235px;display:block;touch-action:pan-y}.tip{position:absolute;pointer-events:none;z-index:2;max-width:calc(100% - 20px);background:#080d15;border:1px solid #40556e;border-radius:6px;padding:8px 10px;font-size:11px;box-shadow:0 5px 15px #0007;white-space:pre-line}.tip[hidden]{display:none}.tablewrap{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap;text-align:right;font-size:12px}th,td{padding:9px 10px;border-bottom:1px solid var(--line)}th{color:var(--muted);font-weight:600}th:nth-child(-n+2),td:nth-child(-n+2){text-align:left}footer{margin-top:25px;color:var(--muted);font-size:12px}#error{color:var(--bad);margin:8px 0;white-space:pre-wrap}#error:empty{display:none}#history-status{margin:5px 0 8px}.empty{padding:24px;color:var(--muted);text-align:center}.chartnote{color:var(--muted);font-size:11px;margin-top:4px}@media(max-width:800px){main{padding:12px 10px 30px}.charts{grid-template-columns:1fr}header{flex-wrap:wrap;gap:8px}}
</style></head><body><main>
<header><div><div class="eyebrow">AirQualityMon / PostgreSQL + TimescaleDB</div><h1>Air quality monitor</h1><div class="muted">Multi-node telemetry · read-only · uncorrected sensor values</div></div><div id="db" class="badge">Connecting…</div></header>
<div id="error" role="status"></div>
<div class="section"><h2>Live nodes</h2><span class="muted small" id="live-time">Waiting for database</span></div><section id="nodes" class="nodes"></section>
<div class="section"><h2>History &amp; comparison</h2><div id="ranges" class="controls"></div></div>
<div id="selector" class="selector"></div><p id="history-status" class="muted small">Loading history…</p>
<section id="charts" class="charts"></section>
<div class="section"><h2>Calibration observations</h2><span class="muted small" id="cal-count"></span></div>
<section class="card tablewrap"><table><thead><tr><th>Observed at</th><th>Node</th><th>RH sensor °C</th><th>BMP280 °C</th><th>RH %</th><th>Thermal camera °C</th><th>Laser meter °C</th></tr></thead><tbody id="cal"></tbody></table><p class="chartnote">Manual surface-temperature observations are independent of the original sensor samples. No correction is applied.</p></section>
<footer>AirQualityMonitorSystem v1.0.1 · Latest sample every 5 s · History refresh every 15 s · eCO₂ is a VOC-derived estimate, not measured CO₂.</footer>
</main><script>
'use strict';
const $=id=>document.getElementById(id);
const el=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e};
const finite=Number.isFinite, fmt=(v,d=1)=>finite(v)?v.toFixed(d):'—';
const delta=n=>finite(n.temperature_c)&&finite(n.bmp_temperature_c)?n.bmp_temperature_c-n.temperature_c:null;
const local=t=>t?new Date(t).toLocaleString('en-GB'):'—';
const palette=['#55dfb2','#65b6ff','#ffbd69','#c6a5ff','#ff8e9d','#78dbe8','#d1dd72','#f5a9df'];
const colors=new Map();let nodes=[],selected=new Set(),known=new Set(),windowKey='1h',hist=null,liveBusy=false,historyBusy=false,historyPending=false,revision=0;
const errors={live:'',history:''};
const label=n=>n.name||n.node_id;
const name=id=>label(nodes.find(n=>n.node_id===id)||{node_id:id});
function color(id){if(!colors.has(id))colors.set(id,palette[colors.size%palette.length]);return colors.get(id)}
function setError(k,msg){errors[k]=msg;$('error').textContent=Object.values(errors).filter(Boolean).join('\n')}
async function api(path){const r=await fetch(path,{cache:'no-store',signal:AbortSignal.timeout(22000)});if(!r.ok)throw Error('HTTP '+r.status);return r.json()}
const metricSpecs=[['temperature_c','RH sensor','°C',2],['bmp_temperature_c','BMP280','°C',2],['delta_c','BMP − RH sensor','°C',2],['humidity_rh','Humidity','%',1],['pressure_hpa','Pressure','hPa',1],['eco2_ppm','eCO₂','ppm',0],['tvoc_ppb','TVOC','ppb',0]];
const expandedNodes=new Set();
function renderNodes(now){const root=$('nodes');root.replaceChildren();if(!nodes.length){root.append(el('div','empty','No nodes registered yet. Waiting for the first successful ingest.'));return}
 const table=el('table','live-table');table.setAttribute('aria-label','Live node readings');const thead=el('thead'),head=el('tr');
 for(const title of ['Node','Status','RH sensor °C','BMP280 °C','ΔT °C','RH %','hPa','eCO₂ ppm','TVOC ppb','RSSI dBm','Age','Diagnostics']){const th=el('th','',title);th.scope='col';head.append(th)}thead.append(head);table.append(thead);const body=el('tbody');
 for(const n of nodes){const age=n.received_at?Math.max(0,(Date.parse(now)-Date.parse(n.received_at))/1000):Infinity;const tr=el('tr',age<=20?'':'stale-row');const ident=el('td'),title=el('div','node-name'),dot=el('i','node-dot');dot.style.backgroundColor=color(n.node_id);title.append(dot,document.createTextNode(label(n)));ident.append(title,el('div','node-meta',`${n.platform}${n.name?' · '+n.node_id:''}${n.location?' · '+n.location:''}`));tr.append(ident,el('td','live-status '+(age<=20?'ok':'bad'),age<=20?'ONLINE':n.received_at?'STALE':'NO DATA'));
 for(const [k,l,u,d] of metricSpecs){const td=el('td','live-value',fmt(k==='delta_c'?delta(n):n[k],d));td.title=(k==='temperature_c'?(n.humidity_chip||'RH sensor'):l)+' · '+u;tr.append(td)}
 tr.append(el('td','',fmt(n.rssi_dbm,0)),el('td','',finite(age)?Math.round(age)+' s':'—'));
 const cell=el('td'),open=expandedNodes.has(n.node_id),button=el('button','diag-button'+(n.ccs_error?' bad':n.ccs_warming_up?' warn':''),open?'Hide':n.ccs_error?'CCS error':n.ccs_warming_up?'Warming up':'Details');button.type='button';button.setAttribute('aria-expanded',String(open));button.setAttribute('aria-controls','diag-'+n.node_id);cell.append(button);tr.append(cell);body.append(tr);
 const diag=el('tr','diag-row');diag.id='diag-'+n.node_id;diag.hidden=!open;const detail=el('td');detail.colSpan=12;const line=el('div','diag-line');const up=finite(n.uptime_ms)?(n.uptime_ms/3600000).toFixed(2)+' h':'—';line.append(el('span','',`Last sample: ${local(n.received_at)}`),el('span','',`Uptime: ${up} · FW: ${n.firmware_version}`),el('span',n.ccs_error?'bad':n.ccs_warming_up?'warn':'',`CCS811: ${n.ccs_error?'error 0x'+n.ccs_error.toString(16):n.ccs_warming_up?'warming up':n.received_at?'no error reported':'—'}`),el('span','',`RH: ${n.humidity_chip||'—'} · ${n.humidity_diag||'—'}`));detail.append(line);diag.append(detail);body.append(diag);
 button.addEventListener('click',()=>{const next=diag.hidden;diag.hidden=!next;if(next)expandedNodes.add(n.node_id);else expandedNodes.delete(n.node_id);button.setAttribute('aria-expanded',String(next));button.textContent=next?'Hide':n.ccs_error?'CCS error':n.ccs_warming_up?'Warming up':'Details'});
 }table.append(body);root.append(table);
}
function renderSelector(){const root=$('selector');root.replaceChildren();for(const n of nodes){const l=el('label');const box=el('input');box.type='checkbox';box.checked=selected.has(n.node_id);box.addEventListener('change',()=>{box.checked?selected.add(n.node_id):selected.delete(n.node_id);revision++;requestHistory()});const sw=el('i','swatch');sw.style.color=color(n.node_id);l.append(box,sw,document.createTextNode(label(n)));root.append(l)}}
async function refreshLive(){if(liveBusy)return;liveBusy=true;try{const d=await api('/api/live');const old=nodes.map(n=>[n.node_id,n.name]);nodes=d.nodes;let changed=false;for(const n of nodes){if(!known.has(n.node_id)){known.add(n.node_id);selected.add(n.node_id);changed=true}color(n.node_id)}for(const id of [...selected])if(!nodes.some(n=>n.node_id===id)){selected.delete(id);known.delete(id);changed=true}renderNodes(d.now);if(changed||JSON.stringify(old)!==JSON.stringify(nodes.map(n=>[n.node_id,n.name])))renderSelector();$('db').className='badge ok';$('db').textContent='DATABASE ONLINE';$('live-time').textContent='Updated '+local(d.now);setError('live','');if(changed){revision++;requestHistory()}}catch(e){$('db').className='badge bad';$('db').textContent='DATABASE UNAVAILABLE';setError('live','Live data unavailable: '+e.message+' · displayed values may be stale.')}finally{liveBusy=false}}
const chartSpecs=[
 {title:'Temperature',unit:'°C',series:[['temperature_c','RH sensor',false],['bmp_temperature_c','BMP280',true]],cal:true},
 {title:'Temperature difference',unit:'°C',series:[['delta_c','BMP − RH sensor',false]]},
 {title:'Relative humidity',unit:'%',series:[['humidity_rh','RH',false]]},
 {title:'Atmospheric pressure',unit:'hPa',series:[['pressure_hpa','Pressure',false]]},
 {title:'Estimated CO₂',unit:'ppm',series:[['eco2_ppm','eCO₂',false]]},
 {title:'Volatile organic compounds',unit:'ppb',series:[['tvoc_ppb','TVOC',false]]}
];
const charts=[];
for(const spec of chartSpecs){const card=el('article','card chart');card.append(el('h3','',spec.title));const legend=el('div','legend'),canvas=el('canvas','plot'),tip=el('div','tip');tip.hidden=true;canvas.setAttribute('aria-label',spec.title+' time series');card.append(legend,canvas,tip);$('charts').append(card);const c={spec,card,legend,canvas,tip,layout:null};charts.push(c);canvas.addEventListener('pointermove',e=>hover(c,e));canvas.addEventListener('pointerleave',()=>{tip.hidden=true});new ResizeObserver(()=>draw(c)).observe(canvas)}
for(const k of ['15m','1h','6h','24h','7d','30d','90d']){const b=el('button',k===windowKey?'active':'',k);b.dataset.range=k;b.onclick=()=>{windowKey=k;for(const x of $('ranges').children)x.classList.toggle('active',x===b);revision++;requestHistory()};$('ranges').append(b)}
function linesFor(spec){if(!hist)return[];const groups=new Map();for(const row of hist.samples){if(!groups.has(row.node_id))groups.set(row.node_id,[]);groups.get(row.node_id).push(row)}const out=[];for(const [id,rows] of groups){for(const [key,l,dash] of spec.series){out.push({label:name(id)+' · '+l,color:color(id),dash,points:rows.map(r=>[Date.parse(r.t),r[key]])})}}if(spec.cal){const cg=new Map();for(const r of hist.calibration){if(!cg.has(r.node_id))cg.set(r.node_id,[]);cg.get(r.node_id).push(r)}for(const [id,rows] of cg){for(const [key,l,shape] of [['thermal_camera_c','Thermal camera','circle'],['laser_meter_c','Laser meter','square']]){const points=rows.filter(r=>finite(r[key])).map(r=>[Date.parse(r.observed_at),r[key]]).sort((a,b)=>a[0]-b[0]);if(points.length)out.push({label:name(id)+' · '+l,color:color(id),shape,points})}}}return out}
function tickTime(t,span){return new Date(t).toLocaleString('en-GB',span>86400000?{day:'2-digit',month:'short'}:{hour:'2-digit',minute:'2-digit'})}
function draw(c){const {canvas,spec,legend}=c;const w=canvas.clientWidth,h=canvas.clientHeight;if(w<1||h<1)return;const dpr=window.devicePixelRatio||1;canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);const ctx=canvas.getContext('2d');ctx.scale(dpr,dpr);ctx.font='11px system-ui';ctx.fillStyle='#8c9fb6';const lines=linesFor(spec);legend.replaceChildren();for(const l of lines){const s=el('span');const sw=el('i','swatch'+(l.dash?' dash':l.shape?' dot':''));sw.style.color=l.color;if(l.shape==='square')sw.style.borderRadius='0';s.append(sw,document.createTextNode(l.label));legend.append(s)}
 let lo=Infinity,hi=-Infinity;for(const l of lines)for(const [t,v] of l.points)if(finite(v)){lo=Math.min(lo,v);hi=Math.max(hi,v)}if(!hist||!finite(lo)){ctx.textAlign='center';ctx.fillText('No samples in selected range',w/2,h/2);c.layout=null;return}
 const pad=Math.max((hi-lo)*.1,spec.unit==='°C'?.15:spec.unit==='%'?.5:spec.unit==='hPa'?.15:1);lo-=pad;hi+=pad;const start=Date.parse(hist.start)-(hist.bucket_seconds||0)*1000,end=Date.parse(hist.end);const left=59,right=w-12,top=10,bottom=h-28;if(right<=left)return;const X=t=>left+(t-start)/(end-start)*(right-left),Y=v=>bottom-(v-lo)/(hi-lo)*(bottom-top);
 ctx.textAlign='right';ctx.textBaseline='middle';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);ctx.strokeStyle='#26364a';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();ctx.fillStyle='#8c9fb6';ctx.fillText(v.toFixed(spec.unit==='ppm'||spec.unit==='ppb'?0:1),left-7,y)}ctx.textAlign='left';ctx.fillText(spec.unit,2,8);ctx.textBaseline='top';const ticks=w<420?3:5;for(let i=0;i<ticks;i++){const t=start+(end-start)*i/(ticks-1);ctx.textAlign=i===0?'left':i===ticks-1?'right':'center';ctx.fillText(tickTime(t,end-start),X(t),bottom+8)}
 ctx.save();ctx.beginPath();ctx.rect(left,top,right-left,bottom-top);ctx.clip();const maxGap=(hist.bucket_seconds?hist.bucket_seconds*2.1:15)*1000;for(const l of lines){ctx.strokeStyle=l.color;ctx.fillStyle=l.color;ctx.lineWidth=1.7;ctx.setLineDash(l.dash?[5,4]:[]);if(l.shape){for(const [t,v] of l.points){if(!finite(v))continue;ctx.beginPath();if(l.shape==='square')ctx.rect(X(t)-3,Y(v)-3,6,6);else ctx.arc(X(t),Y(v),3.5,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#090e16';ctx.stroke()}continue}ctx.beginPath();let prev=null;for(const [t,v] of l.points){if(!finite(v)){prev=null;continue}if(prev===null||t-prev>maxGap)ctx.moveTo(X(t),Y(v));else ctx.lineTo(X(t),Y(v));prev=t}ctx.stroke();ctx.setLineDash([]);if(l.points.filter(p=>finite(p[1])).length===1){const [t,v]=l.points.find(p=>finite(p[1]));ctx.beginPath();ctx.arc(X(t),Y(v),2.5,0,Math.PI*2);ctx.fill()}}ctx.restore();c.layout={start,end,left,right,lines};
}
function nearest(points,t){let a=0,b=points.length;while(a<b){const m=(a+b)>>1;if(points[m][0]<t)a=m+1;else b=m}const p=points[a],q=points[a-1];return !q?p:!p?q:Math.abs(p[0]-t)<Math.abs(q[0]-t)?p:q}
function hover(c,e){if(!c.layout){c.tip.hidden=true;return}const {start,end,left,right,lines}=c.layout;const r=c.canvas.getBoundingClientRect(),x=e.clientX-r.left;if(x<left||x>right){c.tip.hidden=true;return}const t=start+(x-left)/(right-left)*(end-start);const tolerance=Math.max((end-start)/(right-left)*8,(hist.bucket_seconds||5)*1000);const vals=[];for(const l of lines){const p=nearest(l.points,t);if(p&&finite(p[1])&&Math.abs(p[0]-t)<=tolerance)vals.push(`${l.label}: ${fmt(p[1],2)} ${c.spec.unit} (${tickTime(p[0],end-start)})`)}if(!vals.length){c.tip.hidden=true;return}c.tip.textContent=local(t)+'\n'+vals.join('\n');c.tip.hidden=false;const cr=c.card.getBoundingClientRect();c.tip.style.left=Math.max(8,Math.min(e.clientX-cr.left+10,c.card.clientWidth-c.tip.offsetWidth-8))+'px';c.tip.style.top=Math.max(8,e.clientY-cr.top-c.tip.offsetHeight-10)+'px'}
function renderHistory(){const root=$('cal');root.replaceChildren();for(const r of hist.calibration){const tr=el('tr');for(const v of [local(r.observed_at),name(r.node_id),fmt(r.raw_temperature_c,2),fmt(r.raw_bmp_temperature_c,2),fmt(r.raw_humidity_rh,1),fmt(r.thermal_camera_c,2),fmt(r.laser_meter_c,2)])tr.append(el('td','',v));root.append(tr)}if(!hist.calibration.length){const tr=el('tr'),td=el('td','empty','No calibration observations in selected range');td.colSpan=7;tr.append(td);root.append(tr)}$('cal-count').textContent=hist.calibration_truncated?'Latest 100 observations in range':hist.calibration.length+' observations';const count=hist.samples.reduce((s,r)=>s+r.sample_count,0);$('history-status').textContent=`${count.toLocaleString('en-GB')} stored samples · ${hist.bucket_seconds?'Mean / '+(hist.bucket_seconds<60?hist.bucket_seconds+' s':hist.bucket_seconds/60+' min'):'Raw samples'} · ${local(hist.start)} — ${local(hist.end)}`;for(const c of charts)draw(c)}
async function requestHistory(){if(historyBusy){historyPending=true;return}historyBusy=true;const rev=revision;try{if(!selected.size){const end=Date.now(),dur={'15m':900,'1h':3600,'6h':21600,'24h':86400,'7d':604800,'30d':2592000,'90d':7776000}[windowKey];hist={start:new Date(end-dur*1000).toISOString(),end:new Date(end).toISOString(),samples:[],calibration:[],bucket_seconds:0};renderHistory();$('history-status').textContent='Select at least one node.';return}const q=new URLSearchParams({range:windowKey});for(const id of selected)q.append('node',id);const d=await api('/api/history?'+q);if(rev!==revision)return;hist=d;renderHistory();setError('history','')}catch(e){if(rev===revision){setError('history','History unavailable: '+e.message);$('history-status').textContent='History refresh failed · displayed data may be stale.'}}finally{historyBusy=false;if(historyPending){historyPending=false;requestHistory()}}}
refreshLive().then(()=>{if(!hist&&!historyBusy)requestHistory()});setInterval(refreshLive,5000);setInterval(requestHistory,15000);
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
                    window = q.get('range', ['1h'])[0]
                    nodes = list(dict.fromkeys(q.get('node', [])))
                    if window not in RANGES or any(not NODE_ID.fullmatch(n) for n in nodes):
                        raise ValueError('Invalid range or node ID')
                except ValueError as e:
                    self.json(400, {'error': str(e)})
                    return
                self.json(200, history(window, nodes))
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
