#!/usr/bin/env python3
"""
Mobile Design Studio — Dashboard Auto-Update
Lê Google Sheets públicos e atualiza index.html automaticamente
Roda via GitHub Actions toda segunda-feira às 08:00 (Brasília)
"""

import urllib.request
import csv
import io
import json
import re
import os
from datetime import datetime

SHEET_ID = '1gdpd1HQXLnvetABENo8qKPCLTRUXOOC1Qr0CNnFLT_w'

def fetch_sheet_by_name(sheet_name):
    """Fetch a sheet by name using the gid discovery method"""
    # First get the HTML to find the gid
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8')
        # Find gid for this sheet name
        pattern = rf'"name":"{re.escape(sheet_name)}".*?"gid":"?(\d+)"?'
        m = re.search(pattern, html)
        if m:
            return fetch_sheet_by_gid(m.group(1))
    except:
        pass
    return None

def fetch_sheet_by_gid(gid):
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8')

def fetch_sheet_first():
    url = f'https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8')

def p_brl(v):
    if not v or str(v).strip() in ('#NUM!', '—', '', '#VALUE!'):
        return 0.0
    try:
        return float(str(v).replace('R$','').replace('.','').replace(',','.').strip())
    except:
        return 0.0

def p_pct(v):
    if not v or str(v).strip() in ('#NUM!', '—', ''):
        return 0.0
    try:
        return float(str(v).replace('%','').replace(',','.').strip())
    except:
        return 0.0

def p_int(v):
    if not v or str(v).strip() in ('#NUM!', '—', ''):
        return 0
    try:
        return int(float(str(v).replace('.','').replace(',','.').strip()))
    except:
        return 0

print("=" * 50)
print("Mobile Design Dashboard — Auto Update")
print(f"Iniciado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
print("=" * 50)

# ── GOOGLE ADS: Dados Diários ─────────────────────────────────
print("\n📥 Buscando Google Ads (Dados Diários)...")

try:
    raw = fetch_sheet_first()
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    print(f"   {len(rows)} linhas lidas")
except Exception as e:
    print(f"❌ Erro ao ler planilha: {e}")
    exit(1)

# Find header row
col = {}
data_start = 0
for i, row in enumerate(rows):
    if row and row[0].strip() == 'Data':
        for j, h in enumerate(row):
            hn = h.strip().lower()
            if hn == 'data': col['date'] = j
            elif 'campanha' in hn: col['camp'] = j
            elif 'custo' in hn and 'conv' not in hn: col['cost'] = j
            elif hn == 'cliques': col['clicks'] = j
            elif 'impress' in hn: col['impr'] = j
            elif 'ctr' in hn: col['ctr'] = j
            elif 'cpc' in hn: col['cpc'] = j
            elif 'convers' in hn and 'taxa' not in hn and 'custo' not in hn: col['conv'] = j
            elif 'taxa' in hn: col['taxa'] = j
        data_start = i + 1
        break

CAMP_MAP = {
    '[SC][FLN]': 'c5',
    '[SC][BC]': 'c1',
    '[PR]':     'c2',
    '[MT/SC]':  'c3',
    '[MS/PR]':  'c4',
}

def get_cid(name):
    for k, v in CAMP_MAP.items():
        if k in name:
            return v
    return None

daily = {c: [] for c in ['c1','c2','c3','c4','c5']}

for row in rows[data_start:]:
    if not row or len(row) < 5: continue
    date = row[col.get('date',0)].strip()
    camp = row[col.get('camp',1)].strip()
    if not date or not camp or date == 'Data': continue
    cid = get_cid(camp)
    if not cid: continue
    daily[cid].append({
        'd':    date,
        's':    round(p_brl(row[col['cost']]  if 'cost'   in col else ''), 2),
        'cl':   p_int(row[col['clicks']] if 'clicks' in col else ''),
        'i':    p_int(row[col['impr']]   if 'impr'   in col else ''),
        'ctr':  round(p_pct(row[col['ctr']]   if 'ctr'    in col else ''), 2),
        'cpc':  round(p_brl(row[col['cpc']]   if 'cpc'    in col else ''), 2),
        'conv': round(p_brl(row[col['conv']]  if 'conv'   in col else ''), 2),
        'taxa': round(p_pct(row[col['taxa']]  if 'taxa'   in col else ''), 2),
        'cpa':  round(p_brl(row[col.get('cpa',99)] if 'cpa' in col else ''), 2) if 'cpa' in col else 0,
    })

for cid in daily:
    daily[cid].sort(key=lambda x: x['d'])

total_g = sum(len(v) for v in daily.values())
print(f"✅ Google Ads: {total_g} registros ({', '.join(f'{k}:{len(v)}' for k,v in daily.items() if v)})")

# ── META ADS: Meta Diário ─────────────────────────────────────
print("\n📥 Buscando Meta Ads (Meta Diário)...")

meta_daily = {'m1': [], 'm2': [], 'm3': []}

# Try known GIDs for Meta Diário sheet
for gid in ['1368491615', '856532054', '2', '3', '4', '5']:
    try:
        raw_meta = fetch_sheet_by_gid(gid)
        reader_m = csv.reader(io.StringIO(raw_meta))
        rows_m = list(reader_m)
        # Check if this is the Meta Diário sheet
        if any('Campanha' in str(r) and 'Gasto' in str(r) and 'Alcance' in str(r) for r in rows_m[:5]):
            print(f"   ✅ Meta Diário encontrado (gid={gid})")

            mc = {}
            hdr_idx = 0
            for i, row in enumerate(rows_m):
                if row and row[0].strip() == 'Data':
                    for j, h in enumerate(row):
                        hn = h.strip().lower()
                        if hn == 'data': mc['date'] = j
                        elif 'campanha' in hn: mc['camp'] = j
                        elif 'gasto' in hn: mc['spend'] = j
                        elif hn == 'cliques': mc['clicks'] = j
                        elif 'impress' in hn: mc['impr'] = j
                        elif 'ctr' in hn: mc['ctr'] = j
                        elif 'cpc' in hn: mc['cpc'] = j
                        elif 'alcance' in hn: mc['reach'] = j
                        elif 'freq' in hn: mc['freq'] = j
                        elif 'cpm' in hn: mc['cpm'] = j
                        elif 'link' in hn: mc['lc'] = j
                        elif 'leads' in hn: mc['leads'] = j
                    hdr_idx = i + 1
                    break

            def get_mid(name):
                if 'SC-BC' in name: return 'm2'
                if 'SC-FLN' in name or 'SC-FLN' in name: return 'm3'
                if '[PR]' in name: return 'm1'
                return None

            for row in rows_m[hdr_idx:]:
                if not row or len(row) < 5: continue
                date = row[mc.get('date',0)].strip()
                camp = row[mc.get('camp',1)].strip()
                if not date or not camp: continue
                mid = get_mid(camp)
                if not mid: continue
                meta_daily[mid].append({
                    'd':     date,
                    'spend': round(p_brl(row[mc['spend']] if 'spend' in mc else ''), 2),
                    'cl':    p_int(row[mc['clicks']] if 'clicks' in mc else ''),
                    'i':     p_int(row[mc['impr']]   if 'impr'   in mc else ''),
                    'ctr':   round(p_pct(row[mc['ctr']]   if 'ctr'    in mc else ''), 4),
                    'cpc':   round(p_brl(row[mc['cpc']]   if 'cpc'    in mc else ''), 4),
                    'r':     p_int(row[mc['reach']]  if 'reach'  in mc else ''),
                    'f':     round(p_brl(row[mc['freq']]  if 'freq'   in mc else ''), 4),
                    'cpm':   round(p_brl(row[mc['cpm']]   if 'cpm'    in mc else ''), 4),
                    'lc':    p_int(row[mc['lc']]     if 'lc'     in mc else ''),
                    'leads': p_int(row[mc['leads']]  if 'leads'  in mc else ''),
                })

            for mid in meta_daily:
                meta_daily[mid].sort(key=lambda x: x['d'])
            break
    except Exception as e:
        continue

total_m = sum(len(v) for v in meta_daily.values())
print(f"✅ Meta Ads: {total_m} registros ({', '.join(f'{k}:{len(v)}' for k,v in meta_daily.items() if v)})")

# ── BUILD JS ARRAYS ───────────────────────────────────────────
print("\n🔧 Gerando arrays JavaScript...")

# GD_RAW
gd_rows = []
for cid in ['c1','c2','c3','c4','c5']:
    for d in daily[cid]:
        gd_rows.append(
            f"  ['{d['d']}','{cid}',{d['s']},{d['cl']},{d['i']},{d['ctr']},{d['cpc']},{d['conv']},{d['taxa']},{d['cpa']}]"
        )
new_gd_raw = "const GD_RAW=[\n" + ",\n".join(gd_rows) + "\n];"

# Meta daily arrays
new_md = {
    'MD_M1': json.dumps(meta_daily['m1'], ensure_ascii=False),
    'MD_M2': json.dumps(meta_daily['m2'], ensure_ascii=False),
    'MD_M3': json.dumps(meta_daily['m3'], ensure_ascii=False),
}

# ── READ index.html ───────────────────────────────────────────
if not os.path.exists('index.html'):
    print("❌ index.html não encontrado no repositório")
    exit(1)

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ── INJECT DATA ───────────────────────────────────────────────
# 1. Replace GD_RAW
gd_pattern = r'const GD_RAW=\[[\s\S]*?\];'
if re.search(gd_pattern, html):
    html = re.sub(gd_pattern, new_gd_raw, html)
    print(f"✅ GD_RAW: {len(gd_rows)} registros injetados")
else:
    print("⚠️  GD_RAW marker não encontrado")

# 2. Replace Meta daily arrays
for var, data in new_md.items():
    pattern = rf'const {var}=\[[\s\S]*?\];'
    replacement = f'const {var}={data};'
    if re.search(pattern, html):
        html = re.sub(pattern, replacement, html)
        count = len(json.loads(data))
        print(f"✅ {var}: {count} registros injetados")
    else:
        print(f"⚠️  {var} marker não encontrado")

# 3. Update timestamp
updated_at = datetime.now().strftime('%d/%m/%Y %H:%M')
html = re.sub(
    r'Última atualização: [\d/: ]+',
    f'Última atualização: {updated_at}',
    html
)
# If no existing timestamp, add to subtitle
if 'Última atualização' not in html:
    html = re.sub(
        r'(Meta Ads: todo o período disponível)',
        f'\\1 · Última atualização: {updated_at}',
        html
    )

# ── WRITE OUTPUT ──────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n🎉 Dashboard atualizado com sucesso!")
print(f"   Timestamp: {updated_at}")
print(f"   Google Ads: {total_g} registros")
print(f"   Meta Ads: {total_m} registros")
print(f"   Arquivo: {len(html):,} bytes")
