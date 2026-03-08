"""
Suzuki F_info Earthquake Monitor
Copyright: Suzuki Yukiya 2026
Theory: GER / Suzuki Information Emergence Theory
"""
import urllib.request, json, math, os
from datetime import datetime, timezone, timedelta
from collections import Counter

phi = (1 + math.sqrt(5)) / 2

class FInfoDetector:
    def __init__(self, window=14):
        self.window = window
        self.history = []

    def _I(self, data):
        n = len(data)
        if n < 4: return 0.0
        h = n // 2
        p = [x+1e-10 for x in data[:h]]
        q = [x+1e-10 for x in data[h:]]
        sp=sum(p); sq=sum(q)
        p=[x/sp for x in p]; q=[x/sq for x in q]
        q2=[q[min(int(i*(len(q))//len(p)),len(q)-1)] for i in range(len(p))]
        sq2=sum(q2)+1e-10; q2=[x/sq2+1e-10 for x in q2]
        def kl(a,b): return sum(ai*math.log(ai/bi) for ai,bi in zip(a,b))
        sym_kl=kl(p,q2)+kl(q2,p)
        P_int=max(1-0.5*sum(abs(pi-qi) for pi,qi in zip(p,q2)),0)
        return P_int*sym_kl

    def update(self, x):
        self.history.append(float(x))
        w=self.window*2
        if len(self.history)<w+1: return None
        I_now=self._I(self.history[-w:])
        I_prev=self._I(self.history[-w-1:-1])
        F=I_now-I_prev
        xm=sum(self.history[-self.window:])/self.window
        G=max(xm,1e-10); E=math.log(1+G); S=G/E
        phi_d=abs(S-phi)/phi
        thr=phi**(-3)*max(abs(I_now),1e-10)
        if abs(F)<thr:        state="STABLE"
        elif F>0 and S<phi:   state="EMERGENCE"
        elif F<0 and S>phi:   state="REFLUX"
        elif F>0:             state="EMERGENCE+"
        else:                 state="REFLUX+"
        return dict(state=state,S=round(S,4),F_info=round(F,4),
                    I=round(I_now,4),phi_dist=round(phi_d,4))

    def run(self, series):
        self.history=[]
        return [r for x in series for r in [self.update(x)] if r]

def fetch_quakes(days=3650, min_mag=5.0):
    end=datetime.now(timezone.utc)
    start=end-timedelta(days=days)
    url=("https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
         "&starttime="+start.strftime('%Y-%m-%d')
         +"&endtime="+end.strftime('%Y-%m-%d')
         +"&minmagnitude="+str(min_mag)+"&orderby=time&limit=20000")
    with urllib.request.urlopen(url,timeout=20) as r:
        data=json.loads(r.read())
    quakes=[]
    for q in data['features']:
        p=q['properties']; c=q['geometry']['coordinates']
        quakes.append({
            'time':datetime.utcfromtimestamp(p['time']/1000).strftime('%Y-%m-%d'),
            'mag':p['mag'],
            'place':p['place'] or '',
            'lat':round(c[1],2),
            'lon':round(c[0],2)
        })
    return sorted(quakes,key=lambda x:x['time'])

def calc_ifsp(latest):
    if not latest: return None
    I=latest.get('I',0)
    F=abs(latest.get('F_info',0))
    S=latest.get('S',1)
    pd=latest.get('phi_dist',0)
    phi3=phi**(-3); phi2=phi**(-2); phi1=phi**(-1); phi3u=phi**3
    I_norm=min(I/phi3,1.0)
    F_norm=min(F/phi3,1.0)
    S_norm=min(max(S-1,0)/(phi3u-1),1.0)
    p_norm=min(pd/1.0,1.0)
    w_I=phi3; w_F=phi1; w_S=phi2; w_p=phi3
    total_w=w_I+w_F+w_S+w_p
    ifsp=(w_I*I_norm+w_F*F_norm+w_S*S_norm+w_p*p_norm)/total_w
    if ifsp<phi3:   zone='SAFE'
    elif ifsp<phi1: zone='CAUTION'
    else:           zone='DANGER'
    return dict(value=round(ifsp,4),zone=zone,
                I_norm=round(I_norm,4),F_norm=round(F_norm,4),
                S_norm=round(S_norm,4),phi_norm=round(p_norm,4))
def analyze(quakes):
    daily={}
    for q in quakes:
        d=q['time']; daily[d]=max(daily.get(d,0),q['mag'])
    dates=sorted(daily.keys()); series=[daily[d] for d in dates]
    det=FInfoDetector(window=14); results=det.run(series)
    offset=len(series)-len(results)
    recent=[]
    for i,r in enumerate(results[-30:]):
        idx=offset+len(results)-30+i
        if idx<len(dates):
            recent.append({'date':dates[idx],'mag':round(series[idx],1),**r})
    state_counts=Counter(r['state'] for r in results)
    total=len(results)
    state_pct={k:round(v/total*100,1) for k,v in state_counts.items()}
    latest=results[-1] if results else {}
    pred=make_prediction(results,series)
    ifsp=calc_ifsp(latest)
    return dict(recent=recent,state_pct=state_pct,latest=latest,
                prediction=pred,total_days=len(series),
                total_quakes=len(quakes),ifsp=ifsp)

def make_prediction(results,series):
    now=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    if len(results)<7:
        return dict(text='insufficient data',confidence='low',detail='',generated=now)
    recent7=results[-7:]
    em=sum(1 for r in recent7 if 'EMERGENCE' in r['state'])
    rf=sum(1 for r in recent7 if 'REFLUX' in r['state'])
    avg_mag=sum(series[-14:])/min(14,len(series))
    phi_d=results[-1]['phi_dist']
    if em>=5:
        text='Activating (EMERGENCE dominant)'
        confidence='medium'
        detail=str(em)+'/7 days EMERGENCE. Energy accumulation possible.'
    elif rf>=5:
        text='Quieting (REFLUX dominant)'
        confidence='medium'
        detail=str(rf)+'/7 days REFLUX. Post-release quiet period possible.'
    else:
        text='Transitional (direction unclear)'
        confidence='low'
        detail='EM='+str(em)+' RF='+str(rf)+' in last 7 days. Continue monitoring.'
    return dict(text=text,confidence=confidence,detail=detail,
                phi_dist=round(phi_d,4),avg_mag=round(avg_mag,2),generated=now)

def make_html(result,updated):
    sc={'EMERGENCE':'#e74c3c','EMERGENCE+':'#c0392b',
        'REFLUX':'#27ae60','REFLUX+':'#1e8449','STABLE':'#2980b9'}
    ls=result['latest'].get('state','STABLE')
    color=sc.get(ls,'#888')
    rows=''
    for r in result['recent']:
        c=sc.get(r['state'],'#888')
        rows+=('<tr><td>'+r['date']+'</td><td>'+str(r['mag'])+'</td>'
               +'<td style="color:'+c+';font-weight:bold">'+r['state']+'</td>'
               +'<td>'+str(r['F_info'])+'</td><td>'+str(r['phi_dist'])+'</td></tr>')
    pred=result['prediction']
    cc={'high':'#27ae60','medium':'#f39c12','low':'#888'}.get(pred['confidence'],'#888')
    pct=''
    for k,v in sorted(result['state_pct'].items()):
        pct+='<span style="color:'+sc.get(k,'#888')+'">'+k+':'+str(v)+'%</span> '
    html=('<!DOCTYPE html><html lang="ja"><head>'
          '<meta charset="UTF-8">'
          '<meta name="viewport" content="width=device-width,initial-scale=1">'
          '<title>Suzuki F_info Earthquake Monitor</title>'
          '<style>'
          'body{font-family:sans-serif;background:#0a0a0a;color:#e0e0e0;margin:0;padding:20px;max-width:800px}'
          'h1{color:#f0f0f0;font-size:1.4em;border-bottom:1px solid #333;padding-bottom:10px}'
          '.card{background:#1a1a1a;border-radius:8px;padding:16px;margin:12px 0;border:1px solid #2a2a2a}'
          '.state{font-size:2.2em;font-weight:bold;color:'+color+';margin:8px 0}'
          '.pred{border-left:4px solid '+cc+';padding:12px;background:#111820;border-radius:4px}'
          'table{width:100%;border-collapse:collapse;font-size:0.85em}'
          'th{background:#222;padding:8px;text-align:left;color:#aaa}'
          'td{padding:6px 8px;border-bottom:1px solid #1a1a1a}'
          '.note{color:#555;font-size:0.78em;margin-top:20px;border-top:1px solid #222;padding-top:12px;font-family:monospace}'
          '</style></head><body>'
          '<h1>Suzuki F_info Earthquake Monitor</h1>'
          '<div class="card">'
          '<div style="color:#888">Current State</div>'
          '<div class="state">'+ls+'</div>'
          '<div style="color:#f39c12">phi_dist:'+str(result['latest'].get('phi_dist',0))
          +'  S:'+str(result['latest'].get('S',0))
          +'  phi='+str(round(phi,4))+'</div>'
          '<div style="color:#555;font-size:0.85em;margin-top:6px">'
          'Quakes:'+str(result['total_quakes'])+' / '+str(result['total_days'])+' days</div>'
          '</div>'
          '<div class="card pred">'
          '<div style="color:'+cc+';font-weight:bold">Prediction: '+pred['text']+'</div>'
          '<div style="margin-top:6px;font-size:0.9em">'+pred['detail']+'</div>'
          '<div style="color:#555;font-size:0.8em;margin-top:6px">'
          'confidence:'+pred['confidence']+'  avg_M:'+str(pred['avg_mag'])+'  '+pred['generated']+'</div>'
          '</div>'
          '<div class="card"><div style="margin-bottom:8px;color:#888">State distribution</div>'
          '<div>'+pct+'</div></div>'
          '<div class="card"><table>'
          '<tr><th>Date</th><th>Max M</th><th>State</th><th>F_info</th><th>phi_dist</th></tr>'
          +rows+'</table></div>'
          '<div class="note">'
          'F_info = dI_suzuki/dt | I_suzuki = P(interact) x [H(X|Y)+H(Y|X)]<br>'
          'threshold = phi^(-3) = '+str(round(phi**-3,4))
          +' | EMERGENCE: accumulating  REFLUX: releasing<br><br>'
          'Theory: Suzuki Information Emergence Theory / GER Theory<br>'
          'Copyright Suzuki Yukiya 2026 | Data: USGS Earthquake Hazards Program<br>'
          'Updated: '+updated
          +'</div></body></html>')
    return html

def main():
    print("Fetching USGS data...")
    quakes=fetch_quakes(days=3650,min_mag=5.0)
    print("Fetched: "+str(len(quakes))+" quakes")
    result=analyze(quakes)
    print("State: "+result['latest'].get('state','')
          +"  Prediction: "+result['prediction']['text'])
    updated=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    os.makedirs('docs',exist_ok=True)
    with open('docs/index.html','w',encoding='utf-8') as f:
        f.write(make_html(result,updated))
    with open('docs/result.json','w',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print("Done: docs/index.html")

if __name__=='__main__':
    main()
