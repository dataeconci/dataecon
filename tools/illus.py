# Générateur d'illustrations SVG originales (palette DataEcon.Ci)
NAVY="#0b2a4a"; BLUE="#1f5f99"; SKY="#dbe8f6"; GOLD="#c2a15a"; INK="#1f2933"; MUTE="#6b7a8c"; BG="#f5f8fc"; GREEN="#2f8f6b"; RED="#b5473f"
F="font-family='Inter,Segoe UI,Arial,sans-serif'"
def wrap(body, w=480, h=250):
    return (f"<svg viewBox='0 0 {w} {h}' xmlns='http://www.w3.org/2000/svg' role='img'>"
            f"<rect x='1' y='1' width='{w-2}' height='{h-2}' rx='14' fill='{BG}' stroke='#d9e3ef'/>{body}</svg>")
def T(x,y,s,size=14,fill=INK,weight=500,anchor='middle'):
    s=str(s).replace('&','&amp;').replace('<','&lt;')
    return f"<text x='{x}' y='{y}' text-anchor='{anchor}' font-size='{size}' font-weight='{weight}' fill='{fill}' {F}>{s}</text>"
def R(x,y,w,h,fill=SKY,stroke=BLUE,rx=8,sw=2):
    return f"<rect x='{x}' y='{y}' width='{w}' height='{h}' rx='{rx}' fill='{fill}' stroke='{stroke}' stroke-width='{sw}'/>"
def arrow(x1,y1,x2,y2,c=GOLD):
    return (f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='{c}' stroke-width='3' stroke-linecap='round'/>"
            f"<circle cx='{x2}' cy='{y2}' r='4' fill='{c}'/>")
def title(t): return T(240,28,t,15,NAVY,700)

def boxes(t, items):
    n=len(items); w=130; gap=(480-n*w)/(n+1); b=title(t)
    for i,(name,val,kind) in enumerate(items):
        x=gap+i*(w+gap)
        b+=R(x,70,w,100,"#ffffff",BLUE)+T(x+w/2,102,name,17,NAVY,700)+T(x+w/2,134,val,16,BLUE,600)+T(x+w/2,160,kind,12,MUTE,500)
    b+=T(240,215,"Une variable = un nom + une valeur",13,MUTE)
    return wrap(b)
def cells(t, items, caption, hl=None):
    n=len(items); w=min(70,420//n); x0=(480-n*w)/2; b=title(t)
    for i,v in enumerate(items):
        fill=GOLD if hl==i else SKY
        b+=R(x0+i*w,90,w,56,fill,BLUE,4)+T(x0+i*w+w/2,124,v,14,NAVY,700)+T(x0+i*w+w/2,168,i,12,MUTE)
    b+=T(240,196,"position (index)",12,MUTE)+T(240,226,caption,13,BLUE,600)
    return wrap(b)
def table(t, headers, rows, hl_cols=(), hl_rows=(), caption=""):
    n=len(headers); w=min(110,440//n); x0=(480-n*w)/2; b=title(t)
    for j,h in enumerate(headers):
        b+=R(x0+j*w,50,w,30,NAVY if j not in hl_cols else GOLD,NAVY,0,1)+T(x0+j*w+w/2,70,h,12,"#fff",700)
    for i,row in enumerate(rows):
        for j,v in enumerate(row):
            fill="#ffffff"
            if i in hl_rows or j in hl_cols: fill="#fbf3dc"
            b+=R(x0+j*w,80+i*28,w,28,fill,"#c9d6e6",0,1)+T(x0+j*w+w/2,99+i*28,v,12,INK,500)
    if caption: b+=T(240,238,caption,13,BLUE,600)
    return wrap(b)
def flow(t, steps, caption=""):
    n=len(steps); w=100; gap=(480-n*w)/(n+1); b=title(t)
    for i,s in enumerate(steps):
        x=gap+i*(w+gap); b+=R(x,90,w,60,"#fff",BLUE)+T(x+w/2,126,s,13,NAVY,700)
        if i<n-1: b+=arrow(x+w+6,120,x+w+gap-8,120)
    if caption: b+=T(240,205,caption,13,MUTE)
    return wrap(b)
def fn(t, name, inp, out, caption=""):
    b=title(t)+R(30,90,110,60,"#fff",BLUE)+T(85,126,inp,14,INK,600)
    b+=arrow(146,120,184,120)+R(190,75,100,90,NAVY,NAVY)+T(240,114,name,15,"#fff",700)+T(240,140,"fonction",12,GOLD,600)
    b+=arrow(296,120,334,120)+R(340,90,110,60,"#fff",GOLD)+T(395,126,out,14,INK,600)
    if caption: b+=T(240,215,caption,13,MUTE)
    return wrap(b)
def bars(t, labels, values, caption="", hi=None):
    n=len(values); m=max(values); w=56; gap=(440-n*w)/(n+1); b=title(t)
    for i,(l,v) in enumerate(zip(labels,values)):
        h=140*v/m; x=20+gap+i*(w+gap)
        b+=f"<rect x='{x}' y='{190-h}' width='{w}' height='{h}' rx='5' fill='{GOLD if hi==i else BLUE}'/>"+T(x+w/2,208,l,12,INK)+T(x+w/2,184-h,v,12,NAVY,700)
    if caption: b+=T(240,238,caption,13,MUTE)
    return wrap(b)
def pie(t, labels, values, caption=""):
    import math
    cols=[NAVY,BLUE,GOLD,"#7fa6cc","#a88c4a"]; tot=sum(values); a=-math.pi/2; b=title(t); cx,cy,r=170,135,80
    for i,v in enumerate(values):
        a2=a+2*math.pi*v/tot; x1,y1=cx+r*math.cos(a),cy+r*math.sin(a); x2,y2=cx+r*math.cos(a2),cy+r*math.sin(a2)
        b+=f"<path d='M{cx},{cy} L{x1:.1f},{y1:.1f} A{r},{r} 0 {1 if v/tot>.5 else 0} 1 {x2:.1f},{y2:.1f} Z' fill='{cols[i%5]}' stroke='#fff' stroke-width='2'/>"
        b+=R(310,70+i*30,16,16,cols[i%5],cols[i%5],3,1)+T(334,83+i*30,f"{labels[i]}  {round(100*v/tot)}%",13,INK,600,'start'); a=a2
    if caption: b+=T(240,240,caption,13,MUTE)
    return wrap(b)
def line(t, labels, values, caption=""):
    n=len(values); m=max(values); lo=min(values); x0,x1=50,440; pts=[]; b=title(t)
    b+=f"<line x1='40' y1='200' x2='450' y2='200' stroke='#c9d6e6' stroke-width='2'/>"
    for i,v in enumerate(values):
        x=x0+i*(x1-x0)/(n-1); y=190-130*(v-lo)/(m-lo or 1); pts.append((x,y))
    b+=f"<polyline points='{' '.join(f'{x:.0f},{y:.0f}' for x,y in pts)}' fill='none' stroke='{BLUE}' stroke-width='4' stroke-linejoin='round'/>"
    for (x,y),l in zip(pts,labels): b+=f"<circle cx='{x:.0f}' cy='{y:.0f}' r='5' fill='{GOLD}'/>"+T(x,220,l,11,MUTE)
    if caption: b+=T(240,242,caption,13,MUTE)
    return wrap(b)
def decision(t, cond, yes, no):
    b=title(t)+f"<polygon points='240,50 330,110 240,170 150,110' fill='#fff' stroke='{BLUE}' stroke-width='2'/>"+T(240,115,cond,14,NAVY,700)
    b+=arrow(160,130,90,185)+arrow(320,130,390,185)+R(30,188,120,40,"#e6f4ee",GREEN)+T(90,214,yes,13,GREEN,700)+R(330,188,120,40,"#f9e8e6",RED)+T(390,214,no,13,RED,700)
    b+=T(110,150,"Oui",12,MUTE)+T(370,150,"Non",12,MUTE)
    return wrap(b)
def loop(t, items, caption=""):
    b=title(t)+f"<circle cx='240' cy='125' r='62' fill='none' stroke='{GOLD}' stroke-width='3' stroke-dasharray='8 6'/>"+T(240,121,"for",18,NAVY,700)+T(240,141,"chaque élément",11,MUTE)
    pos=[(240,48),(320,125),(240,202),(160,125)]
    for (x,y),v in zip(pos,items): b+=R(x-45,y-15,90,30,"#fff",BLUE)+T(x,y+5,v,13,NAVY,700)
    if caption: b+=T(240,244,caption,12,MUTE)
    return wrap(b)
def kv(t, pairs, caption=""):
    b=title(t)
    for i,(k,v) in enumerate(pairs):
        y=60+i*48; b+=R(100,y,110,36,NAVY,NAVY,6)+T(155,y+23,k,14,"#fff",700)+arrow(216,y+18,254,y+18)+R(260,y,120,36,"#fff",GOLD,6)+T(320,y+23,v,14,INK,700)
    if caption: b+=T(240,236,caption,13,MUTE)
    return wrap(b)
def join(t, left, right, key):
    b=title(t)
    b+=R(30,55,170,130,"#fff",BLUE)+T(115,78,left[0],13,NAVY,700)
    for i,r in enumerate(left[1:]): b+=T(115,106+i*26,r,12,INK)
    b+=R(280,55,170,130,"#fff",GOLD)+T(365,78,right[0],13,NAVY,700)
    for i,r in enumerate(right[1:]): b+=T(365,106+i*26,r,12,INK)
    b+=arrow(204,120,274,120)+T(240,108,key,12,BLUE,700)+T(240,222,"Une jointure relie deux tables par une clé commune",13,MUTE)
    return wrap(b)
def funnel(t, labels, caption=""):
    b=title(t)+f"<polygon points='110,60 370,60 290,140 290,190 190,190 190,140' fill='{SKY}' stroke='{BLUE}' stroke-width='2'/>"+T(240,110,labels[0],14,NAVY,700)+T(240,175,labels[1],13,BLUE,700)
    if caption: b+=T(240,232,caption,13,MUTE)
    return wrap(b)
def codeout(t, code, out, caption=""):
    b=title(t)+R(30,50,200,150,NAVY,NAVY,10)
    for i,l in enumerate(code[:6]): b+=T(44,78+i*22,l,12,"#e8eef7",500,'start')
    b+=arrow(238,125,262,125)+R(268,50,182,150,"#fff",GREEN,10)
    for i,l in enumerate(out[:6]): b+=T(282,78+i*22,l,12,GREEN,600,'start')
    if caption: b+=T(240,232,caption,13,MUTE)
    return wrap(b)

def hero(tool):
    pal={"python":("#0b2a4a","#1f5f99","#c2a15a"),"r":("#0b2a4a","#2c7fb8","#c2a15a"),"sql":("#0b2a4a","#1f5f99","#c2a15a"),"tableau":("#0b2a4a","#1f5f99","#c2a15a")}[tool]
    a,b_,c=pal; s=f"<svg viewBox='0 0 640 360' xmlns='http://www.w3.org/2000/svg' role='img'><defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='{a}'/><stop offset='1' stop-color='{b_}'/></linearGradient></defs><rect width='640' height='360' rx='20' fill='url(#g)'/>"
    s+="<g fill='none' stroke='#ffffff' stroke-opacity='.08'>"+"".join(f"<path d='M0 {y}H640'/>" for y in range(40,360,40))+"</g>"
    if tool in("python","r"):
        s+=f"<rect x='60' y='50' width='330' height='230' rx='12' fill='#0a2036' stroke='#ffffff' stroke-opacity='.2'/><circle cx='84' cy='72' r='5' fill='#d9776f'/><circle cx='102' cy='72' r='5' fill='{c}'/><circle cx='120' cy='72' r='5' fill='#5cb88c'/>"
        lines=(["import pandas as pd","df = pd.read_csv('ventes.csv')","df.groupby('produit').sum()","print(df.head())","# analyse en 4 lignes"] if tool=="python" else ["ventes <- read.csv('ventes.csv')","aggregate(q ~ produit, ventes, sum)","summary(ventes$q)","ggplot(ventes, aes(produit, q))","  + geom_col()"])
        for i,l in enumerate(lines): s+=f"<text x='80' y='{112+i*30}' font-size='15' fill='{'#e8eef7' if i<4 else c}' font-family='Consolas,monospace'>{l}</text>"
        s+=f"<rect x='360' y='150' width='230' height='150' rx='12' fill='#fff'/>"
        for i,(h,col) in enumerate([(50,b_),(90,a),(70,c),(110,b_),(130,a)]): s+=f"<rect x='{378+i*42}' y='{286-h}' width='28' height='{h}' rx='4' fill='{col}'/>"
    elif tool=="sql":
        for i in range(3): s+=f"<ellipse cx='150' cy='{110+i*50}' rx='70' ry='20' fill='#12395f' stroke='{c}' stroke-width='3'/><rect x='80' y='{110+i*50}' width='140' height='34' fill='#12395f'/><ellipse cx='150' cy='{144+i*50}' rx='70' ry='20' fill='#12395f' stroke='{c}' stroke-width='3'/>"
        s+=f"<ellipse cx='150' cy='110' rx='70' ry='20' fill='#1f5f99' stroke='{c}' stroke-width='3'/>"
        s+=f"<rect x='300' y='60' width='290' height='230' rx='12' fill='#fff'/>"+"".join(f"<rect x='300' y='{60+i*38}' width='290' height='38' fill='{'#0b2a4a' if i==0 else ('#fbf3dc' if i%2 else '#ffffff')}'/>" for i in range(6))
        for i,t in enumerate(["produit      quantité","Cacao            300","Anacarde         220","Café                110","Coton             95"]): s+=f"<text x='318' y='{85+i*38}' font-size='15' font-family='Consolas,monospace' fill='{'#fff' if i==0 else '#1f2933'}'>{t}</text>"
        s+=f"<path d='M232 150 H292' stroke='{c}' stroke-width='4'/><circle cx='294' cy='150' r='6' fill='{c}'/>"
    else:
        s+="<rect x='50' y='45' width='540' height='270' rx='14' fill='#fff'/>"
        s+=f"<rect x='70' y='65' width='240' height='110' rx='8' fill='#eef3f9'/>"+"".join(f"<rect x='{90+i*40}' y='{160-h}' width='26' height='{h}' rx='3' fill='{b_}'/>" for i,h in enumerate([40,70,55,85,60]))
        s+=f"<rect x='330' y='65' width='240' height='110' rx='8' fill='#eef3f9'/><polyline points='350,150 400,120 450,135 500,95 550,85' fill='none' stroke='{c}' stroke-width='5' stroke-linejoin='round'/>"
        s+=f"<rect x='70' y='190' width='240' height='105' rx='8' fill='#eef3f9'/><circle cx='150' cy='243' r='40' fill='{a}'/><path d='M150 243 L150 203 A40 40 0 0 1 188 232 Z' fill='{c}'/><path d='M150 243 L188 232 A40 40 0 0 1 160 283 Z' fill='{b_}'/>"
        s+=f"<rect x='330' y='190' width='240' height='105' rx='8' fill='#eef3f9'/>"+"".join(f"<rect x='350' y='{205+i*24}' width='{w}' height='14' rx='3' fill='{b_ if i%2 else a}'/>" for i,w in enumerate([180,140,100,60]))
    return s+"</svg>"
