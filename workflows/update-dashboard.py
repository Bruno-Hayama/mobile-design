#!/usr/bin/env python3
"""
Mobile Design Studio — Dashboard Auto-Update
Lê dados do Google Sheets e atualiza o index.html no repositório
"""

import urllib.request
import csv
import io
import json
import re
import os
from datetime import datetime, timedelta

SHEET_ID = '1gdpd1HQXLnvetABENo8qKPCLTRUXOOC1Qr0CNnFLT_w'

def fetch_sheet(gid):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}'
    with urllib.request.urlopen(url) as r:
        return r.read().decode('utf-8')

def parse_brl(v):
    if not v or v in ('#NUM!', '—', ''):
        return 0.0
    return float(str(v).replace('R$','').replace('.','').replace(',','.').strip())

def parse_pct(v):
    if not v or v in ('#NUM!', '—', ''):
        return 0.0
    return float(str(v).replace('%','').replace(',','.').strip())

def parse_int(v):
    if not v or v in ('#NUM!', '—', ''):
        return 0
    try:
        return int(str(v).replace('.','').replace(',','').strip())
    except:
        return 0

print("📥 Buscando dados do Google Sheets...")

# ── ABA: Dados Diários (Google Ads) ──────────────────────────
# gid=0 é a primeira aba
daily_csv = fetch_sheet(0)
reader = csv.reader(io.StringIO(daily_csv))
rows = list(reader)

# Detecta cabeçalho
header_idx = 0
for i, row in enumerate(rows):
    if row and row[0].strip() == 'Data':
        header_idx = i
        break

headers = rows[header_idx]
data_rows = rows[header_idx+1:]

# Map columns
col = {}
for i, h in enumerate(headers):
    hn = h.strip().lower()
    if hn == 'data': col['date'] = i
    elif 'campanha' in hn: col['camp'] = i
    elif 'custo' in hn and 'conv' not in hn: col['cost'] = i
    elif hn == 'cliques': col['clicks'] = i
    elif 'impress' in hn: col['impr'] = i
    elif 'ctr' in hn: col['ctr'] = i
    elif 'cpc' in hn: col['cpc'] = i
    elif 'convers' in hn and 'taxa' not in hn and 'custo' not in hn: col['conv'] = i
    elif 'taxa' in hn: col['taxa'] = i
    elif 'custo/conv' in hn or 'custo/conv' in hn: col['cpa'] = i

# Parse daily data
CAMP_MAP = {
    '[SC][BC]': 'c1',
    '[PR]': 'c2',
    '[MT/SC]': 'c3',
    '[MS/PR]': 'c4',
    '[SC][FLN]': 'c5',
}

def get_camp_id(name):
    for key, cid in CAMP_MAP.items():
        if key in name:
            return cid
    return None

daily_by_camp = {cid: [] for cid in ['c1','c2','c3','c4','c5']}

for row in data_rows:
    if not row or len(row) < 5:
        continue
    date = row[col.get('date', 0)].strip()
    camp = row[col.get('camp', 1)].strip()
    if not date or not camp or date == 'Data':
        continue

    cid = get_camp_id(camp)
    if not cid:
        continue

    daily_by_camp[cid].append({
        'd': date,
        's': round(parse_brl(row[col['cost']] if 'cost' in col else ''), 2),
        'cl': parse_int(row[col['clicks']] if 'clicks' in col else ''),
        'i': parse_int(row[col['impr']] if 'impr' in col else ''),
        'ctr': round(parse_pct(row[col['ctr']] if 'ctr' in col else ''), 2),
        'cpc': round(parse_brl(row[col['cpc']] if 'cpc' in col else ''), 2),
        'conv': round(parse_brl(row[col['conv']] if 'conv' in col else ''), 2),
        'taxa': round(parse_pct(row[col['taxa']] if 'taxa' in col else ''), 2),
        'cpa': round(parse_brl(row[col['cpa']] if 'cpa' in col else ''), 2),
    })

# Sort each campaign by date
for cid in daily_by_camp:
    daily_by_camp[cid].sort(key=lambda x: x['d'])

print(f"✅ Google Ads: {sum(len(v) for v in daily_by_camp.values())} registros diários")

# ── ABA: Meta Diário ──────────────────────────────────────────
# Precisamos do gid da aba Meta Diário — vamos tentar gid=1
meta_daily = {}
try:
    # Tenta descobrir o gid correto buscando o HTML da planilha
    meta_csv = fetch_sheet(1368491615)  # gid da aba Meta Diário
    meta_reader = csv.reader(io.StringIO(meta_csv))
    meta_rows = list(meta_reader)

    # Encontra cabeçalho
    meta_hdr_idx = 0
    for i, row in enumerate(meta_rows):
        if row and row[0].strip() == 'Data':
            meta_hdr_idx = i
            break

    meta_headers = meta_rows[meta_hdr_idx]
    meta_data = meta_rows[meta_hdr_idx+1:]

    mc = {}
    for i, h in enumerate(meta_headers):
        hn = h.strip().lower()
        if hn == 'data': mc['date'] = i
        elif 'campanha' in hn: mc['camp'] = i
        elif 'gasto' in hn: mc['spend'] = i
        elif hn == 'cliques': mc['clicks'] = i
        elif 'impress' in hn: mc['impr'] = i
        elif 'ctr' in hn: mc['ctr'] = i
        elif 'cpc' in hn: mc['cpc'] = i
        elif 'alcance' in hn: mc['reach'] = i
        elif 'freq' in hn: mc['freq'] = i
        elif 'cpm' in hn: mc['cpm'] = i
        elif 'link' in hn: mc['lc'] = i
        elif 'leads' in hn: mc['leads'] = i

    META_CAMP_MAP = {
        'SC-BC': 'm2',
        'SC-FLN': 'm3',
        '[PR]': 'm1',
    }

    def get_meta_camp_id(name):
        if 'SC-BC' in name: return 'm2'
        if 'SC-FLN' in name or 'SC-FLN' in name: return 'm3'
        if '[PR]' in name: return 'm1'
        return None

    meta_daily = {'m1': [], 'm2': [], 'm3': []}

    for row in meta_data:
        if not row or len(row) < 5: continue
        date = row[mc.get('date', 0)].strip()
        camp = row[mc.get('camp', 1)].strip()
        if not date or not camp: continue
        mid = get_meta_camp_id(camp)
        if not mid: continue

        meta_daily[mid].append({
            'd': date,
            'spend': round(parse_brl(row[mc['spend']] if 'spend' in mc else ''), 2),
            'cl': parse_int(row[mc['clicks']] if 'clicks' in mc else ''),
            'i': parse_int(row[mc['impr']] if 'impr' in mc else ''),
            'ctr': round(parse_pct(row[mc['ctr']] if 'ctr' in mc else ''), 4),
            'cpc': round(parse_brl(row[mc['cpc']] if 'cpc' in mc else ''), 4),
            'r': parse_int(row[mc['reach']] if 'reach' in mc else ''),
            'f': round(parse_brl(row[mc['freq']] if 'freq' in mc else ''), 4),
            'cpm': round(parse_brl(row[mc['cpm']] if 'cpm' in mc else ''), 4),
            'lc': parse_int(row[mc['lc']] if 'lc' in mc else ''),
            'leads': parse_int(row[mc['leads']] if 'leads' in mc else ''),
        })

    for mid in meta_daily:
        meta_daily[mid].sort(key=lambda x: x['d'])

    print(f"✅ Meta Ads: {sum(len(v) for v in meta_daily.values())} registros diários")

except Exception as e:
    print(f"⚠️  Meta Diário: {e} — usando dados vazios")
    meta_daily = {'m1': [], 'm2': [], 'm3': []}

# ── ABA: Meta Resumo ──────────────────────────────────────────
meta_summary = {}
try:
    # gid da aba Meta Resumo
    mres_csv = fetch_sheet(1841345470)
    mres_reader = csv.reader(io.StringIO(mres_csv))
    mres_rows = list(mres_reader)

    for row in mres_rows:
        if not row or len(row) < 10: continue
        camp = row[0].strip()
        if not camp or camp in ('Campanha', '') or 'Atualizado' in camp: continue
        mid = get_meta_camp_id(camp) if 'get_meta_camp_id' in dir() else None
        if not mid: continue

        def safe_float(v):
            try: return float(str(v).replace(',','.').replace('R$','').strip())
            except: return 0.0

        meta_summary[mid] = {
            'spend': safe_float(row[2] if len(row)>2 else ''),
            'imp': int(safe_float(row[3] if len(row)>3 else '')),
            'reach': int(safe_float(row[4] if len(row)>4 else '')),
            'freq': safe_float(row[5] if len(row)>5 else ''),
            'cpm': safe_float(row[6] if len(row)>6 else ''),
            'ctr': safe_float(row[7] if len(row)>7 else ''),
            'cpc': safe_float(row[8] if len(row)>8 else ''),
            'clicks': int(safe_float(row[9] if len(row)>9 else '')),
            'lc': int(safe_float(row[10] if len(row)>10 else '')),
        }
    print(f"✅ Meta Resumo: {len(meta_summary)} campanhas")
except Exception as e:
    print(f"⚠️  Meta Resumo: {e}")

# ── BUILD TOTALS from daily data ──────────────────────────────
def calc_totals(days):
    if not days:
        return {'spend':0,'clicks':0,'impr':0,'conv':0,'ctr':0,'cpc':0,'cpa':0}
    sp = sum(d['s'] for d in days)
    cl = sum(d['cl'] for d in days)
    im = sum(d['i'] for d in days)
    cv = sum(d['conv'] for d in days)
    return {
        'spend': round(sp, 2),
        'clicks': cl,
        'impr': im,
        'conv': round(cv, 0),
        'ctr': round(cl/im*100, 2) if im > 0 else 0,
        'cpc': round(sp/cl, 2) if cl > 0 else 0,
        'cpa': round(sp/cv, 2) if cv > 0 else 0,
    }

g_totals = {cid: calc_totals(daily_by_camp[cid]) for cid in daily_by_camp}

# ── GENERATE UPDATED_AT ───────────────────────────────────────
updated_at = datetime.now().strftime('%d/%m/%Y %H:%M')

# ── READ TEMPLATE ─────────────────────────────────────────────
template_path = 'index.html'
if not os.path.exists(template_path):
    print("❌ index.html não encontrado")
    exit(1)

with open(template_path, 'r', encoding='utf-8') as f:
    html = f.read()

# ── INJECT GOOGLE ADS DAILY DATA ─────────────────────────────
for cid, days in daily_by_camp.items():
    js_arr = json.dumps(days, ensure_ascii=False)
    # Find and replace the array in the JS
    # Pattern: const GD_RAW=[...];
    pass  # Will inject via marker below

# ── INJECT DATA VIA MARKERS ───────────────────────────────────
# We'll replace the entire GD_RAW array and meta daily arrays

# Build GD_RAW from daily_by_camp
gd_raw_rows = []
for cid in ['c1','c2','c3','c4','c5']:
    for d in daily_by_camp[cid]:
        gd_raw_rows.append(
            f"  ['{d['d']}','{cid}',{d['s']},{d['cl']},{d['i']},{d['ctr']},{d['cpc']},{d['conv']},{d['taxa']},{d['cpa']}]"
        )

new_gd_raw = "const GD_RAW=[\n" + ",\n".join(gd_raw_rows) + "\n];"

# Build meta daily
meta_daily_js = ""
for mid in ['m1','m2','m3']:
    days = meta_daily.get(mid, [])
    meta_daily_js += f"const MD_{mid.upper()}={json.dumps(days, ensure_ascii=False)};\n"

# Build meta summary updates for MC array
mc_updates = {}
for mid, s in meta_summary.items():
    mc_updates[mid] = s

# Update timestamp in header
html = re.sub(
    r'(Google Ads:.*?·\s*Meta Ads:.*?)(?=</div>)',
    f'Google Ads: dados atualizados automaticamente · Meta Ads: todo o período disponível · Última atualização: {updated_at}',
    html
)

# Replace GD_RAW
gd_raw_pattern = r'const GD_RAW=\[[\s\S]*?\];'
if re.search(gd_raw_pattern, html):
    html = re.sub(gd_raw_pattern, new_gd_raw, html)
    print("✅ GD_RAW atualizado")
else:
    print("⚠️  GD_RAW marker não encontrado no HTML")

# Replace meta daily arrays
for mid in ['m1','m2','m3']:
    days = meta_daily.get(mid, [])
    pattern = rf'const MD_{mid.upper()}=\[[\s\S]*?\];'
    replacement = f"const MD_{mid.upper()}={json.dumps(days, ensure_ascii=False)};"
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html)
        print(f"✅ MD_{mid.upper()} atualizado ({len(days)} registros)")

# ── WRITE OUTPUT ──────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n🎉 Dashboard atualizado com sucesso! — {updated_at}")
print(f"   Google Ads: {sum(len(v) for v in daily_by_camp.values())} registros")
print(f"   Meta Ads: {sum(len(v) for v in meta_daily.values())} registros")
