import streamlit as st
import streamlit as st
import base64
from pathlib import Path


# El fondo ahora se carga desde fondo.jpeg; ya no se incrusta la imagen anterior.


def aplicar_estilos():
    # ESTILOS
    # -----------------------------
    st.markdown("""
    <style>

        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Forzar tema claro aunque Streamlit esté configurado en modo oscuro */
        :root {
            color-scheme: light;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp,
        [data-testid="stMain"], [data-testid="stHeader"] {
            background-color: #f5f8fc !important;
            color: #183451 !important;
        }

        [data-testid="stMarkdownContainer"],
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stWidgetLabel"] p,
        [data-testid="stCaptionContainer"] {
            color: #435873;
        }

        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        [data-testid="stSidebar"] label {
            color: #243b56 !important;
        }

        [data-testid="stRadio"] label,
        [data-testid="stRadio"] label p,
        [data-testid="stRadio"] div[role="radiogroup"] {
            color: #243b56 !important;
        }

        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input,
        [data-testid="stTimeInput"] input,
        [data-testid="stTextArea"] textarea,
        [data-testid="stSelectbox"] div[data-baseweb="select"] {
            background-color: #ffffff !important;
            color: #183451 !important;
            border-color: #d6e0ec !important;
        }

        [data-testid="stAppViewContainer"] .stMarkdown pre,
        [data-testid="stAppViewContainer"] pre,
        [data-testid="stAppViewContainer"] code {
            background-color: #eef3fa;
            color: #183451;
        }

        .stApp {
            background: #f5f8fc !important;
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid #e6ebf2;
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1rem;
        }

        .brand {
            padding: 10px 12px 24px 12px;
            border-bottom: 1px solid #edf1f6;
            margin-bottom: 18px;
        }

        .brand-row {
            display: flex;
            align-items: center;
            gap: 14px;
            min-width: 0;
        }
        .brand-row > div:last-child { min-width:0; flex:1; }
        .brand-row img { flex:0 0 auto; }

        .brand-icon {
            width: 44px;
            height: 44px;
            border-radius: 13px;
            background: linear-gradient(135deg, #1976f3, #4d8df7);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 23px;
            font-weight: 800;
            box-shadow: 0 8px 20px rgba(25,118,243,.20);	
	    margin: 0 auto;
        }

        .brand-name {
            font-size: 21px;
            font-weight: 800;
            color: #12335f;
            line-height: 1;
        }

        .brand-sub {
            font-size: 8px;
            letter-spacing: .9px;
            color: #7c8ba1;
            margin-top: 5px;
            font-weight: 600;
        }

        .section-label {
            color: #91a0b5;
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
            margin: 12px 10px 8px;
        }

        .hero {
            min-height: 280px;
            border-radius: 24px;
            padding: 30px 34px;
            background:
                radial-gradient(circle at 80% 25%, rgba(82,145,255,.22), transparent 28%),
                linear-gradient(135deg, #eef6ff 0%, #dcecff 100%);
            border: 1px solid #dbe9fb;
            position: relative;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(43,91,145,.06);
        }

        .hero h1 {
            color: #123b72;
            font-size: 34px;
            margin: 4px 0 8px;
            font-weight: 800;
        }

        .hero h2 {
            color: #1967d2;
            font-size: 14px;
            letter-spacing: .8px;
            margin: 0 0 15px;
            font-weight: 700;
        }

        .hero p {
            color: #51647c;
            max-width: 560px;
            line-height: 1.6;
            font-size: 14px;
        }

        .hero-art {
            position: absolute;
            right: 24px;
            top: 28px;
            width: 245px;
            height: 205px;
            border-radius: 35px;
            background: linear-gradient(145deg, rgba(255,255,255,.78), rgba(185,213,255,.55));
            transform: rotate(-2deg);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 20px 40px rgba(54,110,190,.13);
        }

        .cv-card {
            width: 130px;
            height: 158px;
            background: white;
            border-radius: 13px;
            transform: rotate(-7deg);
            box-shadow: 0 12px 25px rgba(40,75,120,.15);
            padding: 15px;
            position: relative;
        }

        .cv-avatar {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            background: #dcecff;
            margin-bottom: 12px;
        }

        .line {
            height: 7px;
            background: #dce8f8;
            border-radius: 5px;
            margin: 8px 0;
        }

        .line.short { width: 62%; }
        .line.mid { width: 78%; }
        .line.full { width: 94%; }

        .ai-badge {
            position: absolute;
            right: 18px;
            bottom: 18px;
            width: 58px;
            height: 58px;
            border-radius: 16px;
            background: #1976f3;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            box-shadow: 0 12px 25px rgba(25,118,243,.32);
        }

        .metric {
            background: white;
            border: 1px solid #e6ebf2;
            border-radius: 18px;
            padding: 18px 20px;
            min-height: 126px;
            box-shadow: 0 7px 22px rgba(31,63,100,.05);
        }

        .metric-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .metric-icon {
            width: 42px;
            height: 42px;
            border-radius: 13px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            background: #edf5ff;
        }

        .metric-label {
            color: #66778d;
            font-size: 12px;
            font-weight: 600;
        }

        .metric-value {
            color: #122a4a;
            font-size: 29px;
            font-weight: 800;
            margin-top: 9px;
        }

        .metric-foot {
            color: #8492a6;
            font-size: 11px;
            margin-top: 4px;
        }

        .panel {
            background: white;
            border: 1px solid #e6ebf2;
            border-radius: 18px;
            padding: 20px;
            box-shadow: 0 7px 22px rgba(31,63,100,.04);
        }

        .panel-title {
            color: #122a4a;
            font-size: 17px;
            font-weight: 800;
            margin-bottom: 4px;
        }

        .panel-sub {
            color: #8290a4;
            font-size: 12px;
            margin-bottom: 16px;
        }

        .candidate-row {
            padding: 13px 4px;
            border-bottom: 1px solid #eef2f6;
        }

        .candidate-name {
            font-weight: 700;
            color: #193453;
        }

        .candidate-small {
            color: #8491a4;
            font-size: 11px;
        }

        .pill {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 10px;
            font-weight: 700;
        }

        .pill-green { background:#e7f8ef; color:#168653; }
        .pill-blue { background:#e9f3ff; color:#1967d2; }
        .pill-orange { background:#fff2df; color:#c7780a; }
        .pill-purple { background:#f1eaff; color:#7444c4; }

        .quick {
            border-radius: 14px;
            padding: 14px 16px;
            margin-bottom: 10px;
            color: white;
            font-weight: 700;
        }

        .quick-blue { background: linear-gradient(135deg,#1976f3,#458df4); }
        .quick-green { background: linear-gradient(135deg,#16a978,#42c39b); }
        .quick-purple { background: linear-gradient(135deg,#6e55d9,#9278ee); }
        .quick-pink { background: linear-gradient(135deg,#9b55d8,#b981ee); }

        .empty {
            padding: 34px 20px;
            text-align: center;
            color: #8795a8;
            background: #fafcff;
            border: 1px dashed #dbe3ed;
            border-radius: 14px;
        }

        div[data-testid="stButton"] > button, div[data-testid="stLinkButton"] > a {
            border-radius: 11px;
            border: 1px solid #d7e2ef;
            font-weight: 600;
            color: #17395f !important;
            background: #ffffff;
        }

        div[data-testid="stButton"] > button:hover, div[data-testid="stLinkButton"] > a:hover {
            border-color: #1976f3;
            color: #145fc5 !important;
        }

        .stButton > button[kind="primary"] {
            background: #1976f3;
            border-color: #1976f3;
            color: white;
        }

        h1, h2, h3 {
            color: #122a4a;
        }

        .footer {
            text-align:center;
            color:#9aa7b8;
            font-size:10px;
            padding:25px 0 5px;
        }

        /* CurriculAI: paleta más viva, cálida y legible */
        html, body, [data-testid="stAppViewContainer"], .stApp, [data-testid="stMain"] {
            background: #f7f8ff !important;
            color: #243451 !important;
        }
        [data-testid="stSidebar"] { background: linear-gradient(180deg,#ffffff 0%,#fff9f4 100%) !important; border-right:1px solid #e8e8f5; }
        .brand { border-bottom:1px solid #eee8fa; }
        .brand-icon { background:linear-gradient(135deg,#4568f5 0%,#8b5cf6 55%,#ec6c9a 100%); box-shadow:0 9px 22px rgba(116,88,230,.27); }
        .brand-name { color:#26365d; }
        .brand-sub { color:#81749e; }
        .section-label { color:#8d7aa9; }
        .hero {
            background: radial-gradient(circle at 85% 18%,rgba(255,185,125,.42),transparent 25%),
                        radial-gradient(circle at 70% 90%,rgba(175,145,255,.35),transparent 30%),
                        linear-gradient(125deg,#fff3e8 0%,#f0eaff 48%,#e4f2ff 100%) !important;
            border:1px solid #e6dafa;
            box-shadow:0 14px 34px rgba(105,83,180,.10);
        }
        .metric { border-color:#ebe5f7; box-shadow:0 8px 24px rgba(95,74,150,.07); }
        .metric:nth-child(1) { border-top:3px solid #5b7cfa; }
        .panel { border-color:#e8e3f3; box-shadow:0 8px 24px rgba(95,74,150,.055); }
        .metric-icon { background:linear-gradient(135deg,#e7edff,#f5e8ff); }
        .quick-blue { background:linear-gradient(135deg,#4b6cf7,#8b5cf6) !important; }
        .quick-green { background:linear-gradient(135deg,#12a889,#50c9a7) !important; }
        .quick-purple { background:linear-gradient(135deg,#8b5cf6,#c084fc) !important; }
        .quick-pink { background:linear-gradient(135deg,#ef6a9b,#fb9b77) !important; }
        div[data-testid="stButton"] > button[kind="primary"] { background:linear-gradient(135deg,#4b6cf7,#8058e9) !important; border-color:#665fe9 !important; color:#fff !important; }
        div[data-testid="stButton"] > button:hover { border-color:#8b5cf6 !important; box-shadow:0 4px 12px rgba(107,86,220,.13); }
        [data-testid="stRadio"] [role="radiogroup"] label { background:transparent; border-radius:10px; padding:4px 8px; }
        [data-testid="stRadio"] [role="radiogroup"] label:hover { background:#f0eaff; }

        /* Fondo decorativo suave para que la interfaz no se sienta fría ni plana */
        [data-testid="stAppViewContainer"] {
            background-image:
                radial-gradient(ellipse at 8% 4%, rgba(255, 196, 151, .13), transparent 28%),
                radial-gradient(ellipse at 95% 16%, rgba(174, 143, 255, .13), transparent 30%),
                radial-gradient(ellipse at 76% 88%, rgba(99, 196, 229, .10), transparent 28%) !important;
        }
        .metric:nth-child(2) { border-top:3px solid #ffad5c; }
        .metric:nth-child(3) { border-top:3px solid #a46af5; }
        .metric:nth-child(4) { border-top:3px solid #2dc5a0; }
        .candidate-row:hover { background:linear-gradient(90deg,#f5f1ff,#fff8f2); border-radius:10px; }
        [data-testid="stSidebar"] [data-testid="stRadio"] label[data-checked="true"] { background:linear-gradient(90deg,#e8edff,#f5eaff); }
    </style>
    """, unsafe_allow_html=True)

    # Fondo tecnológico sutil en TODA la aplicación; las tarjetas mantienen fondo claro
    # para que los textos y controles sigan siendo legibles.
    st.markdown(f"""
    <style>
    [data-testid="stMainBlockContainer"] {{ position:relative; }}
    .brand {{ padding:12px 12px 24px 12px; }}
    .brand-row {{ gap:14px; min-width:0; }}
    .brand-row img, .brand-row .brand-icon {{ width:86px !important;height:86px !important;min-width:86px;flex:0 0 86px; }}
    .brand-row > div:last-child {{ min-width:0; flex:1; }}
    .brand-name {{ font-size:27px !important; line-height:1.15; white-space:normal; }}
    .brand-tagline {{ margin:12px 0 0 0;color:#1769c2;font-size:11px;font-weight:800;line-height:1.55;letter-spacing:.1px;max-width:100%; overflow-wrap:anywhere; }}
    [data-testid="stSidebar"] {{ background:linear-gradient(180deg,rgba(255,255,255,.97),rgba(255,249,246,.97)) !important; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ background:rgba(255,255,255,.93);border-color:#dfe7f7 !important;border-radius:16px; }}
    </style>
    """, unsafe_allow_html=True)

    # Fondo tecnológico adjunto por el usuario: visible de forma sutil detrás de los paneles.
    # Se usa un overlay claro para que el texto y los formularios sigan siendo legibles.
    st.markdown(f"""
    <style>
    [data-testid="stMain"] > div {{ background: transparent !important; }}
    [data-testid="stSidebar"] {{ background: linear-gradient(180deg,rgba(255,255,255,.96),rgba(255,249,246,.96)) !important; }}
    .brand-row {{ align-items:center; gap:15px; min-width:0; }}
    .brand-row > div:last-child {{ min-width:0; flex:1; }}
    .brand-name {{ font-size:27px !important; line-height:1.15; }}
    .brand-tagline {{ margin:12px 0 0 0 !important; max-width:100% !important; font-size:11px !important; line-height:1.55 !important; color:#236cc2 !important; overflow-wrap:anywhere; }}
    </style>
    """, unsafe_allow_html=True)
import base64
from pathlib import Path

def aplicar_fondo():
    """Aplica fondo.jpeg al área principal sin ocultar tarjetas ni formularios."""
    ruta = Path(__file__).resolve().parent.parent / "fondo.jpeg"
    if not ruta.is_file():
        st.error(f"No se encontró la imagen de fondo: {ruta}")
        return

    imagen = base64.b64encode(ruta.read_bytes()).decode("ascii")
    st.markdown(
        f"""
        <style>
        /* El contenedor visible de Streamlit es el que recibe la imagen. */
        .stApp,
        [data-testid="stAppViewContainer"] {{
            background-color: #f5f8fc !important;
            background-image: linear-gradient(
                rgba(255,255,255,0.12),
                rgba(255,255,255,0.12)
            ), url("data:image/jpeg;base64,{imagen}") !important;
            background-position: center center !important;
            background-size: cover !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}
        [data-testid="stMain"],
        [data-testid="stMain"] > div,
        [data-testid="stMainBlockContainer"],
        [data-testid="stHeader"] {{
            background: transparent !important;
            background-image: none !important;
        }}
        /* Panel lateral claro para conservar la legibilidad. */
        [data-testid="stSidebar"],
        [data-testid="stSidebar"] > div {{
            background: rgba(255,255,255,0.94) !important;
        }}




        /* Sidebar: compacta y fija en escritorio */
        [data-testid="stSidebar"] {{
            height: 100dvh !important;
            overflow: hidden !important;
        }}
        [data-testid="stSidebarContent"] {{
            height: 100dvh !important;
            max-height: 100dvh !important;
            overflow-y: hidden !important;
            overflow-x: hidden !important;
        }}
        [data-testid="stSidebarUserContent"] {{
            padding-top: 0.15rem !important;
            padding-bottom: 0.15rem !important;
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: 0.35rem !important;
        }}
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
            margin-top: 0 !important;
            margin-bottom: 0 !important;
        }}
        [data-testid="stSidebar"] .brand {{
            padding: 0 8px 6px !important;
            margin-bottom: 3px !important;
        }}
        [data-testid="stSidebar"] img {{
            max-height: 94px !important;
            object-fit: contain !important;
        }}
        [data-testid="stSidebar"] .brand-name {{
            font-size: 22px !important;
        }}
        [data-testid="stSidebar"] .brand-tagline {{
            margin: 4px 0 0 !important;
            font-size: 10px !important;
            line-height: 1.25 !important;
        }}
        [data-testid="stSidebar"] .section-label {{
            margin: 5px 8px 2px !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] {{
            gap: 0 !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            padding: 3px 7px !important;
            min-height: 32px !important;
            border-radius: 9px !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
            background: #e7f2ff !important;
        }}
        /* CurriculAI: identidad más clara y navegación moderna. */
        [data-testid="stSidebar"] .brand {{
            padding: 16px 18px 20px !important;
            margin: 0 auto 5px !important;
	    	
            border-bottom: 1px solid #e8edf7 !important;
        }}
        /* El logo se muestra mediante st.image en app.py. */
        [data-testid="stSidebar"] [data-testid="stImage"] img {{
            max-height: 116px !important;
            width: auto !important;
            object-fit: contain !important;
        }}
        [data-testid="stSidebar"] .brand-name {{
            font-size: 26px !important;
            font-weight: 800 !important;
            line-height: 1.16 !important;
            margin-top: 3px !important;
            letter-spacing: -.5px !important;
        }}
        [data-testid="stSidebar"] .brand-tagline {{
            display: block !important;
            font-size: 11px !important;
            font-weight: 650 !important;
            line-height: 1.42 !important;
            margin: 7px 0 5px !important;
            color: #2b65b0 !important;
            max-width: 270px !important;
            overflow-wrap: normal !important;
        }}
        [data-testid="stSidebar"] .section-label {{
            margin: 10px 8px 5px !important;
            font-size: 10px !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label {{
            min-height: 35px !important;
            padding: 5px 10px !important;
            margin: 1px 0 !important;
            border-radius: 11px !important;
            transition: background-color .12s ease !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{
            background: #e6f2ff !important;
            color: #145fc5 !important;
            font-weight: 700 !important;
        }}
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {{
            background: #f0f6ff !important;
        }}
        /* Ocultar círculos de st.radio; el área azul señala la selección. */
        [data-testid="stSidebar"] [role="radiogroup"] label [data-baseweb="radio"] > div:first-child {{
            display: none !important;
        }}
        /* Compensar la altura de las opciones sin perder el pie del menú. */
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
            gap: .25rem !important;
        }}
        /* Pantallas bajas: permitir acceso a las opciones sin recortarlas. */
        @media (max-height: 690px) {{
            [data-testid="stSidebarContent"] {{ overflow-y: auto !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
