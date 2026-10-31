"""Modelli grafici dei post (1080x1350). Stesse regole del sistema visivo approvato:
Lora per i titoli, Instrument Sans per il testo, blu notte / verde petrolio / acqua / menta,
con la «colonna vertebrale» a sinistra (una vertebra piena = slide corrente)."""
from html import escape as e

W, H = 1080, 1350
NAVY, TEAL, AQUA, MINT, FOG, MUTED, BAND = "#12203f", "#1d7774", "#7fd6cf", "#e2f1f0", "#f3f6f8", "#4a5870", "#b9c6da"

CSS = """
@font-face{font-family:'Lora';font-weight:400;font-style:normal;src:url(FONTS/lora-regular.woff)}
@font-face{font-family:'Lora';font-weight:700;font-style:normal;src:url(FONTS/lora-bold.woff)}
@font-face{font-family:'Lora';font-weight:400;font-style:italic;src:url(FONTS/lora-italic.woff)}
@font-face{font-family:'Instrument Sans';font-weight:400;font-style:normal;src:url(FONTS/instrument-sans-regular.woff)}
@font-face{font-family:'Instrument Sans';font-weight:700;font-style:normal;src:url(FONTS/instrument-sans-bold.woff)}
html,body{margin:0}
.p{position:relative;overflow:hidden;box-sizing:border-box;width:1080px;height:1350px;font-family:'Instrument Sans',system-ui,sans-serif}
.h{font-family:'Lora',Georgia,serif;letter-spacing:-0.015em;line-height:1.06;text-wrap:balance;margin:0;font-weight:400}
.sp{position:absolute;left:72px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:16px;align-items:center}
.sp b{display:block;height:22px;border-radius:99px;border:4px solid currentColor;box-sizing:border-box}
.sp b.on{background:currentColor}
.mk{display:flex;flex-direction:column;gap:9px;align-items:flex-start}
.mk b{display:block;height:15px;border-radius:99px;border:3px solid currentColor;box-sizing:border-box}
.mk b.on{background:currentColor}
.kick{position:absolute;left:190px;right:90px;top:110px;font-size:36px;line-height:1.3}
.foot{position:absolute;left:190px;right:90px;bottom:110px;font-size:34px;line-height:1.35}
"""

def _spine(i, n, color):
    ws = [34, 40, 46, 52, 46, 40]
    n = max(3, min(n, 10))
    pills = "".join(f'<b class="{"on" if k == i else ""}" style="width:{ws[k % 6]}px"></b>' for k in range(n))
    return f'<div class="sp" style="color:{color}">{pills}</div>'

def _mark(color, pos):
    return (f'<div class="mk" style="color:{color};position:absolute;{pos}">'
            '<b style="width:44px"></b><b class="on" style="width:56px"></b><b style="width:44px"></b></div>')

ARROW = ('<svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
         'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>')

def cover(p, i, n):
    return f'''<div class="p" style="background:{NAVY};color:#fff">{_spine(i, n, AQUA)}
<div class="kick" style="color:{BAND}">{e(p.get("kicker", "Riccardo Di Lazzaro · Fisioterapista e osteopata"))}</div>
<div style="position:absolute;left:190px;right:90px;top:50%;transform:translateY(-50%)"><h1 class="h" style="font-size:{p.get("size", 108)}px">{e(p["title"])}</h1></div>
<div class="foot" style="display:flex;align-items:center;gap:18px;font-size:38px;color:{AQUA}">{e(p.get("cta", "Scorri per leggere"))} {ARROW}</div></div>'''

def slide(p, i, n):
    note = p.get("note", "Informazione generale. Non sostituisce una visita.")
    return f'''<div class="p" style="background:{FOG};color:{NAVY}">{_spine(i, n, TEAL)}
<div class="kick" style="color:{MUTED}">{e(p.get("kicker", ""))}</div>
<div style="position:absolute;left:190px;right:90px;top:50%;transform:translateY(-50%);display:flex;flex-direction:column;gap:44px">
<h2 class="h" style="font-size:{p.get("size", 88)}px">{e(p["title"])}</h2>
<div style="font-size:42px;line-height:1.4">{e(p["body"])}</div></div>
<div class="foot" style="color:{MUTED}">{e(note)}</div></div>'''

def mito(p, i, n):
    return f'''<div class="p" style="background:{NAVY};color:#fff;display:grid;grid-template-rows:1fr 1fr">
<div style="background:{MINT};color:{NAVY};padding:110px 90px 70px 120px;display:flex;flex-direction:column;justify-content:flex-end;gap:22px;position:relative">
{_mark(TEAL, "left:120px;top:110px")}
<div style="font-family:'Lora',Georgia,serif;font-style:italic;font-size:52px;color:{MUTED}">Mito</div>
<h2 class="h" style="font-size:{p.get("size", 84)}px;color:{MUTED};text-decoration:line-through;text-decoration-thickness:4px">{e(p["mito"])}</h2></div>
<div style="padding:70px 90px 70px 120px;display:flex;flex-direction:column;justify-content:center;gap:22px">
<div style="font-family:'Lora',Georgia,serif;font-style:italic;font-size:52px;color:{AQUA}">Realtà</div>
<div style="font-size:44px;line-height:1.35">{e(p["realta"])}</div></div></div>'''

def chiusura(p, i, n):
    return f'''<div class="p" style="background:{TEAL};color:#fff">{_spine(i, n, "#ffffff")}
<div class="kick" style="color:{MINT}">{e(p.get("kicker", "Ultima slide"))}</div>
<div style="position:absolute;left:190px;right:90px;top:42%;transform:translateY(-50%);display:flex;flex-direction:column;gap:40px">
<h2 class="h" style="font-size:104px">{e(p.get("title", "Hai un dolore che ti limita?"))}</h2>
<div style="font-size:42px;line-height:1.4">{e(p.get("body", "Ogni percorso parte da una valutazione: si ascolta, si esamina, si decide insieme."))}</div></div>
<div style="position:absolute;left:190px;right:90px;bottom:110px;display:flex;flex-direction:column;gap:6px;padding:34px 40px;border-radius:28px;background:#fff;color:{NAVY}">
<b style="font-size:40px">{e(p.get("place", "Eur Centro Medico, Roma"))}</b>
<span style="font-size:36px;color:{MUTED}">{e(p.get("address", "Via di Fiume Bianco 56"))}</span>
<span style="font-size:36px;color:{TEAL};font-weight:700;padding-top:10px">{e(p.get("cta", "Prenota dal link in bio"))}</span></div></div>'''

def quote(p, i, n):
    return f'''<div class="p" style="background:{NAVY};color:#fff">{_mark(AQUA, "left:120px;top:110px")}
<div style="position:absolute;left:120px;right:110px;top:50%;transform:translateY(-50%)"><div class="h" style="font-style:italic;font-size:{p.get("size", 96)}px;line-height:1.14">{e(p["text"])}</div></div>
<div style="position:absolute;left:120px;right:110px;bottom:110px;font-size:38px;line-height:1.3;color:{BAND}">{e(p.get("cite", "Riccardo Di Lazzaro, fisioterapista e osteopata"))}</div></div>'''

def foto(p, i, n):
    """Foto a tutta pagina con scheda bianca in basso (ritratto, studio, terapia)."""
    card = ""
    if p.get("name"):
        sub = f'<div style="font-size:38px;line-height:1.3;color:{MUTED}">{e(p["sub"])}</div>' if p.get("sub") else ""
        card = f'''<div data-card style="position:absolute;left:72px;right:72px;bottom:72px;display:flex;flex-direction:column;gap:10px;padding:44px 50px;border-radius:32px;background:#fff;color:{NAVY}">
<div class="h" style="font-size:72px">{e(p["name"])}</div>{sub}</div>'''
    return f'''<div class="p" style="background:{NAVY}"><img src="PHOTO" alt="" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;object-position:{p.get("pos", "50% 16%")}">{card}</div>'''

def passi(p, i, n):
    """Esercizio in 3 passaggi: foto in alto, titolo, passi numerati."""
    steps = "".join(
        f'''<div style="display:flex;align-items:flex-start"><div style="width:118px;flex:none;font-family:'Lora',Georgia,serif;font-size:60px;line-height:1;color:{TEAL};padding-top:4px">{k}</div>
<div style="font-size:40px;line-height:1.3">{e(t)}</div></div>''' for k, t in enumerate(p["passi"], 1))
    return f'''<div class="p" style="background:{FOG};color:{NAVY}">
<img src="PHOTO" alt="" style="position:absolute;left:0;right:0;top:0;width:100%;height:470px;object-fit:cover;object-position:{p.get("pos", "50% 50%")}">
<div style="position:absolute;left:72px;right:90px;top:520px;bottom:80px;display:flex;flex-direction:column;justify-content:space-between">
<h2 class="h" style="font-size:76px;padding-left:118px">{e(p["title"])}</h2>
<div style="display:flex;flex-direction:column;gap:22px">{steps}</div>
<div style="font-size:34px;line-height:1.35;color:{MUTED};padding-left:118px">{e(p.get("note", "Fermati se senti dolore. Non sostituisce una visita."))}</div></div></div>'''

TEMPLATES = {"cover": cover, "slide": slide, "mito": mito, "chiusura": chiusura,
             "quote": quote, "foto": foto, "passi": passi}
NEEDS_PHOTO = {"foto", "passi"}

def page(slide_props, i, n, fonts_url, photo_url=None):
    body = TEMPLATES[slide_props["template"]](slide_props, i, n)
    if photo_url:
        body = body.replace('src="PHOTO"', f'src="{photo_url}"')
    css = CSS.replace("FONTS", fonts_url)
    return f'<!doctype html><html lang="it"><head><meta charset="utf-8"><style>{css}</style></head><body>{body}</body></html>'
