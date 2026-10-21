import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --cai-blue:#173a62;
  --cai-blue-dark:#102d42;
  --cai-blue-soft:#eef4f8;
  --cai-accent:#245b8e;
  --cai-text:#18364a;
  --cai-muted:#6d8392;
  --cai-bg:#f4f7fa;
  --cai-border:#d7e1e8;
  --cai-white:#ffffff;
  --cai-good:#11795f;
  --cai-bad:#a83b3b;
  --cai-warn:#9c6b12;
}
html, body, .stApp, [class*="css"] {
  font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif !important;
  color: var(--cai-text) !important;
}
html,body,.stApp,[data-testid="stAppViewContainer"]{background:var(--cai-bg)!important;}
[data-testid="stMain"], [data-testid="stHeader"] {background:transparent!important;}
/* Conservar a stMain como contenedor desplazable para todas las paginas.
   overflow: visible anulaba el scroll interno de Streamlit. */
[data-testid="stMain"] {
  overflow-y: auto !important;
  overflow-x: hidden !important;
  min-height: 0 !important;
}
[data-testid="stSidebar"], [data-testid="collapsedControl"] {display:none!important;}
[data-testid="stMainBlockContainer"] {
  max-width: 1600px !important;
  padding: 0.75rem 1.35rem 2rem !important;
}
[data-testid="stVerticalBlock"] {gap:0.7rem;}
h1,h2,h3,h4{color:var(--cai-blue-dark)!important;letter-spacing:-.02em!important;}
h1{font-size:2rem!important; margin-bottom:.2rem!important;}
h2{font-size:1.25rem!important;}
p, li, label, [data-testid="stCaptionContainer"]{color:var(--cai-text)!important;}

/* Topbar fija */
[class*="st-key-cai_topbar"]{
  position:sticky!important; top:0!important; z-index:9999!important;
  width:calc(100vw - 24px)!important;
  margin-left:calc(50% - 50vw + 12px)!important;
  box-sizing:border-box!important;
  background:var(--cai-blue)!important; border-radius:0 0 14px 14px!important;
  padding:9px max(18px, calc((100vw - 1580px) / 2))!important;
  margin-bottom:10px!important;
  box-shadow:0 8px 20px rgba(16,45,66,.16)!important;
}
.cai-brand-wrap{display:flex;align-items:center;gap:12px;min-width:0;}
.cai-brand-title{font-size:1.12rem!important;font-weight:800!important;color:#fff!important;line-height:1.08;margin:0!important;white-space:nowrap;}
.cai-brand-sub{font-size:.58rem!important;font-weight:700!important;letter-spacing:.06em;color:#dcecf5!important;text-transform:uppercase;white-space:nowrap;}
[class*="st-key-cai_topbar"] [data-testid="stImage"] img{border-radius:10px; background:white; padding:4px;}
.cai-top-actions{display:flex;justify-content:flex-end;align-items:center;gap:8px;}
.cai-status{display:inline-flex;align-items:center;justify-content:center;padding:8px 11px;border-radius:999px;font-size:.74rem;font-weight:700;white-space:nowrap;}
.cai-status.ok{background:#244e79;color:#dff4eb;}
.cai-status.error{background:#6c3b46;color:#ffe7e7;}
.cai-top-divider{height:1px;background:#d8e2e9;margin:10px 0 14px 0;}

/* Navegación compacta: las siete secciones siempre visibles sin desplazamiento lateral.
   El texto completo se mantiene y el espacio se distribuye a todo lo ancho. */
[class*="st-key-cai_topbar"] [data-testid="stHorizontalBlock"] {gap:.42rem!important;align-items:center!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] {width:100%!important;min-width:0!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] {
    display:flex!important;
    flex-wrap:nowrap!important;
    align-items:center!important;
    justify-content:center!important;
    gap:3px!important;
    width:100%!important;
    overflow-x:visible!important;
    min-width:0!important;
}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label {
    border:1px solid transparent!important;
    border-radius:8px!important;
    padding:7px 8px!important;
    margin:0!important;
    min-height:36px!important;
    flex:0 0 auto!important;
    background:transparent!important;
    transition:background .15s ease;
}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label p {
    color:#fff!important;
    font-size:clamp(.65rem,.78vw,.85rem)!important;
    font-weight:700!important;
    white-space:nowrap!important;
}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label:hover {background:rgba(255,255,255,.13)!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {background:#edf3f7!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) p {color:var(--cai-blue)!important;}
/* Ocultamos sólo los círculos decorativos, no el área clicable. */
[class*="st-key-cai_topbar"] [data-testid="stRadio"] label [data-baseweb="radio"] > div:first-child {display:none!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] label [data-baseweb="radio"] {margin:0!important;}
[class*="st-key-cai_topbar"] [data-testid="stRadio"] label [data-testid="stMarkdownContainer"] {margin:0!important;}
[class*="st-key-cai_topbar"] .cai-status {font-size:.66rem!important;padding:6px 8px!important;}
[class*="st-key-cai_topbar"] .cai-brand-sub {font-size:.56rem!important;}

/* En pantallas intermedias, las opciones se distribuyen en dos filas
   si realmente no caben; nunca se ofrece una barra horizontal molesta. */
@media (max-width:1160px) {
  [class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] {
    flex-wrap:wrap!important;justify-content:center!important;row-gap:0!important;
  }
  [class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label {padding:4px 6px!important;min-height:30px!important;}
  [class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label p {font-size:.72rem!important;}
}

/* En móvil, cabeceras y navegación pueden ocupar dos renglones,
   pero todos los apartados siguen accesibles sin deslizar lateralmente. */
@media (max-width:740px) {
  [class*="st-key-cai_topbar"] {padding:8px 10px!important;}
  [class*="st-key-cai_topbar"] [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important;gap:6px!important;}
  [class*="st-key-cai_topbar"] [data-testid="stHorizontalBlock"] > div {flex:1 1 100%!important;width:100%!important;}
  [class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] {flex-wrap:wrap!important;}
  [class*="st-key-cai_topbar"] [data-testid="stRadio"] div[role="radiogroup"] label p {font-size:.74rem!important;}
}

/* widgets */
.stTextInput input,.stTextArea textarea,.stDateInput input,.stTimeInput input,[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div, .stFileUploader > section{
  border-radius:12px!important; border:1px solid var(--cai-border)!important; background:white!important; color:var(--cai-text)!important;
}
.stTextInput input:focus,.stTextArea textarea:focus{border-color:var(--cai-accent)!important; box-shadow:0 0 0 1px var(--cai-accent)!important;}
.stButton > button, .stFormSubmitButton > button, [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"]{
  border-radius:11px!important; padding:.58rem .95rem!important; font-weight:750!important;
  border:1px solid var(--cai-blue)!important; background:var(--cai-blue)!important;
  color:white!important; box-shadow:none!important;
}
.stButton > button p, .stButton > button span,
.stFormSubmitButton > button p, .stFormSubmitButton > button span,
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primary"] span{
  color:inherit!important; font-weight:750!important;
}
.stButton > button:hover,.stFormSubmitButton > button:hover{background:var(--cai-blue-dark)!important;border-color:var(--cai-blue-dark)!important;color:white!important;}
.stButton > button[kind="secondary"], [data-testid="stBaseButton-secondary"]{
  background:white!important;color:var(--cai-blue)!important;border-color:#aac2d4!important;
}
.stButton > button[kind="secondary"] p,[data-testid="stBaseButton-secondary"] p,
.stButton > button[kind="secondary"] span,[data-testid="stBaseButton-secondary"] span{color:var(--cai-blue)!important;}
.stButton > button[kind="secondary"]:hover,[data-testid="stBaseButton-secondary"]:hover{background:#e9f1f7!important;color:var(--cai-blue-dark)!important;}
.stButton > button:disabled,.stFormSubmitButton > button:disabled{background:#b0bdc9!important;border-color:#b0bdc9!important;color:#243d50!important;opacity:.8!important;}
.stButton > button:disabled p,.stFormSubmitButton > button:disabled p{color:#243d50!important;}

[data-testid="stExpander"] details, [data-testid="stVerticalBlockBorderWrapper"]{
  background:white!important; border:1px solid var(--cai-border)!important; border-radius:14px!important; box-shadow:0 3px 12px rgba(16,45,66,.03)!important;
}
[data-testid="stExpander"] details summary{padding:.4rem .8rem!important;}
[data-testid="stExpanderDetails"]{padding:.3rem .95rem .95rem .95rem!important;}

.stTabs [data-baseweb="tab-list"]{gap:8px;}
.stTabs [data-baseweb="tab"]{border-radius:10px 10px 0 0;background:#eef4f8;border:1px solid #d9e2e9;padding:.45rem .8rem;}
.stTabs [aria-selected="true"]{background:white;border-bottom-color:white;color:var(--cai-blue-dark);font-weight:700;}

/* Common sections */
.cai-kicker{color:var(--cai-blue);font-size:.75rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase;}
.cai-intro{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap;}
.cai-descripcion{color:var(--cai-muted)!important;font-size:1rem!important;line-height:1.5;margin-top:3px!important;}
.cai-section{font-size:1.15rem;font-weight:800;color:var(--cai-blue-dark);margin:.6rem 0 .25rem;}
.cai-subtle{color:var(--cai-muted);font-size:.85rem;}

.cai-dashboard-hero{width:75%;min-width:320px;background:white;border:1px solid var(--cai-border);border-radius:16px;padding:18px 22px;box-shadow:0 4px 14px rgba(16,45,66,.04);}
@media(max-width:1100px){.cai-dashboard-hero{width:100%;}}
.cai-hero-pill{display:inline-block;font-size:.72rem;color:var(--cai-blue);font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin-bottom:8px;}
.cai-hero-title{font-size:1.55rem;font-weight:800;color:var(--cai-blue-dark);line-height:1.1;margin:0 0 .55rem 0;}
.cai-hero-copy{font-size:.95rem;color:var(--cai-muted);line-height:1.6;}

.cai-kpi{background:white;border:1px solid var(--cai-border);border-radius:14px;padding:16px 18px;min-height:118px;box-shadow:0 3px 12px rgba(16,45,66,.03);}
.cai-kpi-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;}
.cai-kpi-label{font-size:.8rem;font-weight:700;color:var(--cai-muted)}
.cai-kpi-icon{width:36px;height:36px;border-radius:10px;background:var(--cai-blue-soft);display:grid;place-items:center;color:var(--cai-blue);}
.cai-kpi-number{font-size:2rem;font-weight:800;color:var(--cai-blue-dark);margin-top:.25rem;}
.cai-kpi-hint{font-size:.76rem;color:var(--cai-muted);}

.cai-item-card{background:white;border:1px solid var(--cai-border);border-radius:16px;overflow:hidden;box-shadow:0 4px 14px rgba(16,45,66,.04);margin-bottom:.7rem;}
.cai-item-banner{background:var(--cai-blue);padding:14px 17px;display:flex;justify-content:space-between;align-items:flex-start;gap:10px;min-height:76px;}
.cai-item-banner .cai-title{font-size:1.25rem;font-weight:800;color:white;line-height:1.15;}
.cai-item-banner .cai-pretitle{font-size:.7rem;color:#cfe0ec;font-weight:800;letter-spacing:.13em;text-transform:uppercase;margin-bottom:6px;}
.cai-item-banner .cai-icon{font-size:1.9rem;color:#cfe0ec;line-height:1;}
.cai-item-body{padding:14px 16px 16px 16px;}
.cai-item-meta{font-size:.8rem;color:var(--cai-muted);margin:.45rem 0 .55rem;line-height:1.5;}
.cai-item-copy{font-size:.92rem;color:var(--cai-text);line-height:1.55;}
.cai-tag{display:inline-flex;align-items:center;font-size:.72rem;font-weight:800;padding:6px 10px;border-radius:999px;background:#eef4f8;color:var(--cai-blue);margin-bottom:8px;}
.cai-tag.green{background:#e6f4ef;color:#16674f}.cai-tag.red{background:#fdeeed;color:#ab3f3f}.cai-tag.gold{background:#fff3d9;color:#9c6b12}
.cai-outline-box{background:white;border:1px solid var(--cai-border);border-left:4px solid var(--cai-blue);border-radius:14px;padding:14px 16px;margin-bottom:.85rem;}
.cai-actions-inline{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
.cai-actions-inline > div{flex:1 1 140px;}
.cai-mini-note{font-size:.74rem;color:var(--cai-muted);}
.cai-list-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;}
@media(max-width:920px){.cai-list-grid{grid-template-columns:1fr;} [class*="st-key-cai_topbar"]{padding:8px 12px!important;} }
@media(max-width:650px){[data-testid="stMainBlockContainer"]{padding:.5rem .75rem 2rem!important;} .cai-item-banner .cai-title{font-size:1rem;} .cai-brand-sub{display:none;} }

.stProgress > div > div > div > div{background:var(--cai-blue)!important;}
</style>
"""

def aplicar_estilos():
    st.markdown(CSS, unsafe_allow_html=True)

def aplicar_fondo():
    # Se conserva como punto de extensión, pero el fondo general ya está definido en CSS.
    return
