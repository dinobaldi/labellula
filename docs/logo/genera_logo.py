import math
T="#0b7a75"; D="#0b4f4c"; A="#c98a06"; MONO="Courier New, Courier, monospace"
seq="LABELLULA"; k=[0]
def nxt():
    c=seq[k[0]%len(seq)]; k[0]+=1; return c
def ell_pt(cx,cy,rx,ry,rot,t):
    a=math.radians(rot); x,y=rx*math.cos(t),ry*math.sin(t)
    return cx+x*math.cos(a)-y*math.sin(a), cy+x*math.sin(a)+y*math.cos(a)
def wing_solid(cx,cy,rx,ry,rot):
    a=math.radians(rot); dx,dy=math.cos(a)*rx*.88,math.sin(a)*rx*.88
    return (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" fill="{T}" fill-opacity=".16" stroke="{T}" stroke-width="1.2"/>'
            f'<line x1="{cx-dx:.1f}" y1="{cy-dy:.1f}" x2="{cx+dx:.1f}" y2="{cy+dy:.1f}" stroke="{T}" stroke-width=".8" stroke-opacity=".7"/>')
def wing_text(cx,cy,rx,ry,rot,n,size):
    out=[f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" transform="rotate({rot} {cx} {cy})" fill="none" stroke="{T}" stroke-width=".6" stroke-opacity=".35" stroke-dasharray="2 3"/>']
    # punti a distanza uguale lungo il contorno (non a passo d'angolo: sulle punte si ammasserebbero)
    M=720; ts=[2*math.pi*m/M for m in range(M+1)]; pts=[ell_pt(cx,cy,rx,ry,rot,t) for t in ts]
    cum=[0.0]
    for a_,b_ in zip(pts,pts[1:]): cum.append(cum[-1]+math.dist(a_,b_))
    scelti=[]; j=0
    for i in range(n):
        target=cum[-1]*i/n
        while cum[j]<target: j+=1
        scelti.append(ts[j])
    for i,t in enumerate(scelti):
        x,y=ell_pt(cx,cy,rx,ry,rot,t)
        if x<110: continue  # sopra il corpo: niente lettere
        # distanza dal corpo: piu' lontano = piu' chiaro e piu' "sciolto"
        f=(x-100)/(2*rx); op=max(.35,1-f*.9)
        dx,dy=-rx*math.sin(t),ry*math.cos(t); ang=math.degrees(math.atan2(dy,dx))+rot
        if ang>90: ang-=180
        if ang<-90: ang+=180
        col=[D,T,A][i%3]
        out.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="700" text-anchor="middle" dominant-baseline="central" transform="rotate({ang:.0f} {x:.1f} {y:.1f})" fill="{col}" fill-opacity="{op:.2f}" font-family="{MONO}">{nxt()}</text>')
    # nervatura centrale fatta di lettere
    for j in range(1,6):
        t=j/6; x,y=ell_pt(cx,cy,rx*(2*t-1)*1.0 if False else rx,ry,rot,0)
        px=cx+(2*t-1)*rx*.8*math.cos(math.radians(rot)); py=cy+(2*t-1)*rx*.8*math.sin(math.radians(rot))
        out.append(f'<text x="{px:.1f}" y="{py:.1f}" font-size="{size-2}" text-anchor="middle" dominant-baseline="central" transform="rotate({rot} {px:.1f} {py:.1f})" fill="{T}" fill-opacity=".45" font-family="{MONO}">{nxt().lower()}</text>')
    return out
p=[]
# ali sinistre: ancora disegnate
p+=[wing_solid(56,52,44,11,12), wing_solid(60,88,40,10,-14)]
# ali destre: gia' diventate lettere
p+=wing_text(144,52,44,11,-12,24,9)
p+=wing_text(140,88,40,10,14,22,9)
# testa e torace (meta' destra gia' "scritta": occhio destro come lettera)
p.append(f'<ellipse cx="100" cy="62" rx="10" ry="15" fill="{D}"/>')
p.append(f'<circle cx="100" cy="40" r="9" fill="{D}"/><circle cx="95" cy="38" r="4.5" fill="{T}"/>')
p.append(f'<text x="105.5" y="37.5" font-size="11" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="{A}" font-family="{MONO}">o</text>')
# addome: in alto segmenti, in basso lettere
for i,(y,rx) in enumerate([(84,6),(95,5.6),(106,5.2)]):
    p.append(f'<ellipse cx="100" cy="{y}" rx="{rx}" ry="5.2" fill="{D}" fill-opacity="{1-i*.1:.2f}"/>')
p.append(f'<rect x="93" y="112" width="14" height="64" rx="6" fill="none" stroke="{T}" stroke-width=".6" stroke-opacity=".35" stroke-dasharray="2 3"/>')
for i,(ch,col,s) in enumerate([("L",D,13),("A",T,12.5),("B",A,12),("E",T,11.5),("L",D,11)]):
    y=120+i*12
    p.append(f'<text x="100" y="{y:.1f}" font-size="{s}" font-weight="700" text-anchor="middle" dominant-baseline="central" fill="{col}" font-family="{MONO}">{ch}</text>')
marchio="\n  ".join(p)
logo=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 620 200" role="img" aria-labelledby="t">
  <title id="t">Labellula: una libellula a meta' trasformata in lettere</title>
  {marchio}
  <text x="222" y="108" font-size="62" fill="{D}" font-family="Georgia, 'Times New Roman', serif">Label<tspan fill="{T}">lula</tspan></text>
  <text x="225" y="142" font-size="15" fill="#5d6670" font-family="Segoe UI, Helvetica, Arial, sans-serif" letter-spacing=".5">catalogazione locale delle fotografie con l'AI</text>
</svg>
'''
mark=f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" role="img" aria-labelledby="t">
  <title id="t">Labellula</title>
  {marchio}
</svg>
'''
from pathlib import Path
d=str(Path(__file__).resolve().parent)
open(d+r"\labellula-logo.svg","w",encoding="utf-8").write(logo)
open(d+r"\labellula-marchio.svg","w",encoding="utf-8").write(mark)
