import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageOps
import base64
import io
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
import time
from datetime import datetime, timedelta
import urllib.parse
import os
import tempfile
import numpy as np
import shutil 
import re 
import uuid 

# ==========================================
# 🚗 CONFIGURACIÓN DE LANZAMIENTO AUTOMOTOR
# ==========================================
MODO_LANZAMIENTO = True 
CREDITOS_INVITADO = 4 
NOMBRE_APP = "AutoProp IA 🚗"
NOMBRE_SHEET_DB = "Usuarios_AutoApp" # ¡Asegúrate de crear esta hoja en Drive!

# --- IMPORTACIÓN CONDICIONAL DE MOVIEPY ---
try:
    from moviepy.editor import ImageClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title=NOMBRE_APP, 
    page_icon="🚗",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- TU NÚMERO DE ADMINISTRADOR ---
ADMIN_WHATSAPP = "595961871700" 

# --- SISTEMA DE PERSISTENCIA ANTI-REFRESH (INVITADOS) ---
@st.cache_resource
def get_guest_db():
    return {}

guest_db = get_guest_db()

query_params = st.query_params
if "gid" not in query_params:
    guest_id = str(uuid.uuid4())[:8]
    st.query_params["gid"] = guest_id
else:
    guest_id = query_params["gid"]

if guest_id not in guest_db:
    guest_db[guest_id] = CREDITOS_INVITADO

# Sincronizar session_state con la DB global al inicio
if 'guest_credits' not in st.session_state:
    st.session_state['guest_credits'] = guest_db[guest_id]

def consumir_credito_invitado():
    """Descuenta 1 crédito y actualiza la sesión inmediatamente"""
    if guest_db[guest_id] > 0:
        guest_db[guest_id] -= 1
        st.session_state['guest_credits'] = guest_db[guest_id] 
        return True
    return False

# --- ESTILOS CSS (MODO EXPERIENCIA PERFECTA) ---
st.markdown("""
    <style>
    .main { background-color: #F1F5F9; } 
    h1 { color: #1E293B; font-family: 'Helvetica Neue', sans-serif; font-weight: 800; }
    
    .stButton>button {
        border-radius: 8px; border: none; padding: 12px; font-weight: bold; width: 100%; transition: all 0.2s;
    }
    .stButton>button:hover { transform: scale(1.02); }
    
    .stButton>button:disabled {
        background-color: #CBD5E1; color: #64748B; cursor: not-allowed;
    }

    /* --- STATUS FLOTANTE --- */
    div[data-testid="stStatusWidget"] {
        position: fixed !important; top: 50% !important; left: 50% !important; transform: translate(-50%, -50%) !important; z-index: 999999 !important; background-color: white !important; padding: 25px !important; border-radius: 15px !important; box-shadow: 0 0 0 100vmax rgba(0,0,0,0.6) !important; border: 2px solid #EF4444 !important; width: 85% !important; max-width: 350px !important; text-align: center !important;
    }

    /* --- ELIMINAR EFECTOS DE CARGA --- */
    .stApp, [data-testid="stAppViewContainer"] { opacity: 1 !important; filter: none !important; transition: none !important; will-change: auto !important; }
    [data-testid="InputInstructions"] { display: none !important; }

    /* UPLOADER */
    [data-testid='stFileUploaderDropzoneInstructions'] > div:first-child { display: none; }
    [data-testid='stFileUploaderDropzoneInstructions']::before { content: "📸 Sube fotos del vehículo"; visibility: visible; display: block; text-align: center; font-weight: bold; font-size: 1.2em; color: #EF4444; }
    [data-testid='stFileUploaderDropzoneInstructions']::after { content: "Máx 10 fotos"; visibility: visible; display: block; text-align: center; font-size: 0.8em; }
    [data-testid='stFileUploader'] button { color: transparent !important; position: relative; }
    [data-testid='stFileUploader'] button::after { content: "📂 Galería"; color: #333; position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-weight: bold; font-size: 14px; }

    /* BOTÓN FLOTANTE */
    [data-testid="stSidebarCollapsedControl"] { background-color: #EF4444 !important; color: white !important; border-radius: 8px !important; padding: 5px !important; }
    [data-testid="stSidebarCollapsedControl"] svg { fill: white !important; color: white !important; }

    /* OCULTAR FLECHAS NUMEROS */
    input::-webkit-outer-spin-button, input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }

    .output-box { background-color: white; padding: 25px; border-radius: 10px; border: 1px solid #cbd5e1; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    
    /* --- BOTONES SOCIALES ELEGANTES --- */
    .social-btn {
        display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 10px; margin: 5px 0; border-radius: 8px; text-align: center; text-decoration: none; font-weight: bold; font-size: 0.85em; transition: all 0.2s; background-color: white; border: 2px solid #ddd;
    }
    .social-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .social-btn:active { transform: scale(0.98); }
    
    .btn-wp { border-color: #25D366; color: #25D366 !important; }
    .btn-wp svg { fill: #25D366; width: 18px; height: 18px; }
    .btn-ig { border-color: #E1306C; color: #E1306C !important; }
    .btn-ig svg { fill: #E1306C; width: 18px; height: 18px; }
    .btn-fb { border-color: #1877F2; color: #1877F2 !important; }
    .btn-fb svg { fill: #1877F2; width: 18px; height: 18px; }
    .btn-tk { border-color: #000000; color: #000000 !important; }
    .btn-tk svg { fill: #000000; width: 18px; height: 18px; }
    
    .reel-wrapper { max-width: 350px; margin: 0 auto; border-radius: 20px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3); background-color: #000; }

    /* TARJETAS PLANES DETALLADAS */
    .plan-basic, .plan-standard, .plan-agency { text-align: left !important; padding: 20px; border-radius: 12px; margin-bottom: 10px; height: 100%; }
    .plan-basic { background-color: #F8FAFC; border: 2px solid #475569; color: #334155; }
    .plan-standard { background-color: white; border: 2px solid #EF4444; color: #0F172A; box-shadow: 0 4px 6px rgba(239, 68, 68, 0.1); }
    .plan-agency { background: linear-gradient(135deg, #FFFBEB 0%, #FFFFFF 100%); border: 2px solid #F59E0B; color: #0F172A; box-shadow: 0 10px 25px rgba(245, 158, 11, 0.25); transform: scale(1.03); position: relative; z-index: 10; }
    
    .feature-list { list-style-type: none; padding: 0; margin: 15px 0; }
    .feature-list li { margin-bottom: 8px; font-size: 0.85em; display: flex; align-items: center; gap: 8px; line-height: 1.3; }
    .check-icon { color: #16a34a; font-weight: bold; min-width: 20px; font-size: 1.1em; } 
    .cross-icon { color: #dc2626; opacity: 0.6; min-width: 20px; font-size: 1.1em; }
    .feature-locked { opacity: 0.5; text-decoration: line-through; color: #64748B; }
    .plan-title-center { text-align: center; margin-bottom: 5px; font-weight: 800; font-size: 1.3em; }
    .price-tag { font-size: 1.4em; font-weight: 800; margin: 10px 0; text-align: center; }
    .pro-badge { background-color: #EF4444; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7em; font-weight: bold; }
    .free-badge { background-color: #64748B; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.7em; font-weight: bold; }
    .launch-badge { background: linear-gradient(90deg, #EF4444, #F59E0B); color: white; padding: 5px 10px; border-radius: 12px; font-size: 0.8em; font-weight: bold; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }

    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE APOYO ---
def encode_image(image):
    buffered = io.BytesIO()
    if image.mode in ("RGBA", "P"): image = image.convert("RGB")
    image.thumbnail((800, 800))
    image.save(buffered, format="JPEG", quality=70)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def format_price_display(value):
    if not value: return ""
    try:
        return "{:,}".format(int(value)).replace(",", ".")
    except:
        return value

def limpiar_formulario():
    """RESETEA COMPLETAMENTE LOS CAMPOS DEL FORMULARIO AUTOMOTOR"""
    # Establecer valores por defecto
    st.session_state['v_oper'] = "Venta"
    st.session_state['v_marca'] = "Toyota" 
    st.session_state['v_modelo'] = ""
    st.session_state['v_ano'] = 2020
    st.session_state['v_color'] = ""
    st.session_state['v_origen'] = "Importado (Iquique)"
    st.session_state['v_estado'] = "Usado"
    st.session_state['v_tipo'] = "Automóvil (Sedán/Hatch)"
    st.session_state['v_transmision'] = "Automática"
    st.session_state['v_combustible'] = "Nafta"
    st.session_state['v_precio'] = 0
    st.session_state['v_moneda'] = "Gs."
    st.session_state['v_uso_alquiler'] = "Particular"
    st.session_state['v_frecuencia_pago'] = "Diario"
    
    st.session_state['u_whatsapp'] = None 
    
    # Borrar resultados generados
    keys_borrar = ['generated_result', 'video_path', 'video_frases']
    for k in keys_borrar:
        if k in st.session_state:
            del st.session_state[k]
            
    # Reiniciar uploader
    st.session_state['uploader_key'] += 1
    
    # RECARGA FORZOSA
    st.rerun()

def cerrar_sesion():
    st.session_state['usuario_activo'] = None
    st.session_state['plan_seleccionado'] = None
    st.session_state['ver_planes'] = False
    st.session_state['pedido_registrado'] = False
    st.rerun()

# --- CALLBACKS ---
def ir_a_planes():
    st.session_state.ver_planes = True
    st.session_state.plan_seleccionado = None
    st.session_state.pedido_registrado = False

def seleccionar_plan(nombre_plan):
    st.session_state.plan_seleccionado = nombre_plan
    st.session_state.ver_planes = True
    st.session_state.pedido_registrado = False

def volver_a_app():
    st.session_state.ver_planes = False
    st.session_state.plan_seleccionado = None
    st.session_state.pedido_registrado = False

def cancelar_seleccion():
    st.session_state.plan_seleccionado = None
    st.session_state.ver_planes = True
    st.session_state.pedido_registrado = False

# --- FUNCIÓN DE VALIDACIÓN DE IMÁGENES (EL PORTERO IA) ---
def validar_imagenes_vehiculos(files):
    """Verifica si las imágenes son de vehículos antes de procesar."""
    try:
        content = [{"type": "text", "text": "Eres un clasificador de imágenes. Analiza estas imágenes. Tu ÚNICA tarea es determinar si la MAYORÍA de las imágenes muestran vehículos de cuatro ruedas (autos, camionetas, SUVs, furgonetas) aptos para la venta en un concesionario. Si muestran motocicletas, bicicletas, personas, paisajes sin vehículos, o cualquier otra cosa que no sea un vehículo de 4 ruedas principal, responde 'INVALID'. Si son vehículos de 4 ruedas válidos, responde 'VALID'. Tu respuesta debe ser SOLO una palabra: VALID o INVALID."}]
        
        # Solo analizamos las primeras 3 fotos para que sea rápido y barato
        for f in files[:3]:
            f.seek(0)
            content.append({
                "type": "image_url", 
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image(Image.open(f))}",
                    "detail": "low"
                }
            })
        
        res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": content}], temperature=0.0, max_tokens=10) 
        validation_result = res.choices[0].message.content.strip().upper()
        return validation_result == "VALID"
        
    except Exception as e:
        print(f"Error en validación: {e}")
        return True 

# --- FUNCIÓN GENERADORA DE VIDEO REEL ---
def crear_reel_vertical(imagenes_uploaded, textos_clave, status_container=None):
    if not MOVIEPY_AVAILABLE or not imagenes_uploaded: return None
    
    num_fotos = len(imagenes_uploaded)
    duracion_por_foto = 20.0 / num_fotos
    if duracion_por_foto < 2.0: duracion_por_foto = 2.0 

    clips = []
    W, H = 720, 1280 
    font = ImageFont.load_default()
    temp_dir = tempfile.mkdtemp()

    for i, img_file in enumerate(imagenes_uploaded):
        try:
            if status_container: status_container.update(label=f"🎞️ Procesando foto {i+1}/{num_fotos}...")
            
            img_file.seek(0)
            img = Image.open(img_file).convert("RGB")
            img.thumbnail((1200, 1200)) 
            img = ImageOps.fit(img, (W, H), method=Image.Resampling.LANCZOS)
            overlay = Image.new('RGBA', (W, H), (0, 0, 0, 80))
            img.paste(overlay, (0, 0), overlay)
            draw = ImageDraw.Draw(img)
            
            texto_actual = textos_clave[i % len(textos_clave)] if textos_clave else NOMBRE_APP
            draw.text((W/2, H*0.8), texto_actual, font=font, fill="white", anchor="mm", align="center")
            draw.text((W/2, H*0.95), f"Generado con {NOMBRE_APP} 🚀", fill="#cccccc", anchor="mm", font=font)
            
            temp_img_path = os.path.join(temp_dir, f"temp_frame_{i}.jpg")
            img.save(temp_img_path, quality=70, optimize=True)
            clip = ImageClip(temp_img_path).set_duration(duracion_por_foto)
            clips.append(clip)

        except Exception as e:
            print(f"Error procesando imagen {i}: {e}")
            continue

    if not clips:
        try: shutil.rmtree(temp_dir)
        except: pass
        return None

    if status_container: status_container.update(label="🎞️ Renderizando video final...")
    
    final_clip = concatenate_videoclips(clips, method="compose")
    if final_clip.duration > 20.0: final_clip = final_clip.subclip(0, 20.0)

    tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
    output_path = tfile.name
    tfile.close()

    final_clip.write_videofile(
        output_path, codec="libx264", audio=False, fps=15, preset='ultrafast',
        ffmpeg_params=['-pix_fmt', 'yuv420p'], threads=1, logger=None
    )
    
    try: shutil.rmtree(temp_dir)
    except: pass
        
    return output_path

# --- INICIALIZACIÓN ---
if 'uploader_key' not in st.session_state: st.session_state['uploader_key'] = 0
if 'usuario_activo' not in st.session_state: st.session_state['usuario_activo'] = None
if 'ver_planes' not in st.session_state: st.session_state['ver_planes'] = False
if 'plan_seleccionado' not in st.session_state: st.session_state['plan_seleccionado'] = None
if 'pedido_registrado' not in st.session_state: st.session_state['pedido_registrado'] = False

# --- API KEY ---
api_key = st.secrets.get("OPENAI_API_KEY")
if not api_key:
    st.error("⚠️ Error: Falta API Key de OpenAI en Secrets.")
    st.stop()
client = OpenAI(api_key=api_key)

# =======================================================
# === 🔐 CONEXIÓN GOOGLE SHEETS (AUTOMOTOR) ===
# =======================================================
def get_gspread_client():
    creds_info = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_info:
        creds_info["private_key"] = creds_info["private_key"].replace("\\n", "\n")
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
    client_gs = gspread.authorize(creds)
    return client_gs

def obtener_usuarios_sheet():
    try:
        client_gs = get_gspread_client()
        archivo = client_gs.open(NOMBRE_SHEET_DB)
        sheet = archivo.get_worksheet(0)
        return sheet.get_all_records()
    except Exception:
        return []

def descontar_credito(codigo_usuario):
    try:
        client_gs = get_gspread_client()
        sheet = client_gs.open(NOMBRE_SHEET_DB).get_worksheet(0)
        cell = sheet.find(str(codigo_usuario))
        if cell:
            headers = sheet.row_values(1)
            col_limite = headers.index('limite') + 1 
            valor_actual = sheet.cell(cell.row, col_limite).value
            if valor_actual and int(valor_actual) > 0:
                nuevo_saldo = int(valor_actual) - 1
                sheet.update_cell(cell.row, col_limite, nuevo_saldo)
                return True
    except Exception:
        return False
    return False

def registrar_pedido(nombre, apellido, email, telefono, nuevo_plan):
    try:
        client_gs = get_gspread_client()
        sheet = client_gs.open(NOMBRE_SHEET_DB).get_worksheet(0)
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        nombre_completo = f"{nombre} {apellido}"
        nueva_fila = ["PENDIENTE", nombre_completo, nuevo_plan, 0, telefono, email, "NUEVO PEDIDO", fecha]
        sheet.append_row(nueva_fila)
        return "CREATED"
    except Exception as e:
        return "ERROR"

# =======================================================
# === 🏗️ BARRA LATERAL (AUTOMOTOR) ===
# =======================================================
with st.sidebar:
    st.header("🔐 Área de Agentes")
    
    if not st.session_state['usuario_activo']:
        if MODO_LANZAMIENTO:
            creditos_actuales = st.session_state.get('guest_credits', CREDITOS_INVITADO)
            st.markdown(f"""<div style="background-color:#FEF3C7; padding:10px; border-radius:8px; margin-bottom:15px; border:1px solid #F59E0B;"><small>Estado actual:</small><br><b>🚀 INVITADO VIP (Motor)</b><br><span style="color:#B45309; font-size:0.9em;">Créditos disponibles: <b>{creditos_actuales}</b></span></div>""", unsafe_allow_html=True)
        else:
            st.markdown("""<div style="background-color:#F1F5F9; padding:10px; border-radius:8px; margin-bottom:15px;"><small>Estado actual:</small><br><b>👤 Invitado (Freemium)</b><br><span style="color:#64748B; font-size:0.8em;">1 Generación / 24hs</span></div>""", unsafe_allow_html=True)
            
        with st.form("login_form"):
            codigo_input = st.text_input("¿Tienes Código de Agente?", type="password", placeholder="Ej: AUTO123")
            submit_login = st.form_submit_button("🔓 Entrar como Agente")
        if submit_login and codigo_input:
            usuarios_db = obtener_usuarios_sheet()
            usuario_encontrado = next((u for u in usuarios_db if str(u.get('codigo', '')).strip().upper() == codigo_input.strip().upper()), None)
            if usuario_encontrado:
                st.session_state['usuario_activo'] = usuario_encontrado
                st.session_state['ver_planes'] = False
                st.rerun()
            else:
                st.error("❌ Código incorrecto.")
        st.markdown("---")
        st.info("💡 **Los Invitados tienen funciones limitadas.**")
        st.button("🚀 VER PLANES PRO", on_click=ir_a_planes)
    else:
        user = st.session_state['usuario_activo']
        creditos_disponibles = int(user.get('limite', 0) if user.get('limite') != "" else 0)
        st.success(f"✅ ¡Hola {user.get('cliente', 'Agente')}!")
        color_cred = "blue" if creditos_disponibles > 0 else "red"
        st.markdown(f":{color_cred}[**🪙 Créditos: {creditos_disponibles}**]")
        
    st.markdown("---")
    st.markdown("### 🛠️ Gestión")
    if st.button("🚘 Nuevo Vehículo (Limpiar)", type="primary"):
        limpiar_formulario()
            
    if st.session_state['usuario_activo']:
        if st.button("🔒 Cerrar Sesión"):
            cerrar_sesion()
    st.caption(f"© 2026 {NOMBRE_APP}")

# =======================================================
# === 💎 ZONA DE VENTAS (ADAPTADA A MOTOR) ===
# =======================================================
if st.session_state.ver_planes:
    st.title("💎 Acelera tus Ventas")
    
    if st.session_state.plan_seleccionado is None:
        st.write("Planes diseñados para playas y agentes independientes.")
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("""<div class="plan-basic"><h3 class="plan-title-center">🥉 Básico</h3><div class="price-tag">20.000 Gs</div><ul class="feature-list"><li><span class="check-icon">✅</span> 10 Vehículos/mes</li><li><span class="check-icon">✅</span> Ficha Técnica Completa</li><li><span class="check-icon">✅</span> Datos de Precio</li><li><span class="check-icon">✅</span> Max 3 Fotos (Visión IA)</li><li class="feature-locked"><span class="cross-icon">❌</span> Estrategia de Venta</li><li class="feature-locked"><span class="cross-icon">❌</span> Tono de Voz</li><li class="feature-locked"><span class="cross-icon">❌</span> Link WhatsApp</li><li class="feature-locked"><span class="cross-icon">❌</span> Generador de Video</li></ul></div>""", unsafe_allow_html=True)
            st.button("Elegir Básico", key="btn_basico", on_click=seleccionar_plan, args=("Básico",))

        with c2:
            st.markdown("""<div class="plan-standard"><h3 class="plan-title-center">🥈 Playa</h3><div class="price-tag" style="color:#EF4444;">35.000 Gs</div><ul class="feature-list"><li><span class="check-icon">✅</span> <b>20 Vehículos/mes</b></li><li><span class="check-icon">✅</span> Ficha Técnica Completa</li><li><span class="check-icon">✅</span> <b>Estrategia de Venta</b></li><li><span class="check-icon">✅</span> <b>Tono de Voz (Vendedor)</b></li><li><span class="check-icon">✅</span> Datos de Precio</li><li><span class="check-icon">✅</span> <b>Link WhatsApp Directo</b></li><li><span class="check-icon">✅</span> <b>Max 6 Fotos</b> (Visión IA)</li><li class="feature-locked"><span class="cross-icon">❌</span> Generador de Video</li></ul></div>""", unsafe_allow_html=True)
            st.button("Elegir Playa", key="btn_estandar", type="primary", on_click=seleccionar_plan, args=("Playa",))

        with c3:
            st.markdown("""<div class="plan-agency"><h3 class="plan-title-center" style="color:#B45309;">🥇 Concesionaria</h3><div class="price-tag" style="color:#D97706;">80.000 Gs</div><ul class="feature-list"><li><span class="check-icon">✅</span> <b>80 Vehículos/mes</b></li><li><span class="check-icon">✅</span> Ficha Técnica Completa</li><li><span class="check-icon">✅</span> <b>Estrategia de Venta</b></li><li><span class="check-icon">✅</span> <b>Tono de Voz (Vendedor)</b></li><li><span class="check-icon">✅</span> Datos de Precio</li><li><span class="check-icon">✅</span> <b>Link WhatsApp Directo</b></li><li><span class="check-icon">✅</span> <b>Max 10 Fotos</b> (Visión IA)</li><li><span class="check-icon">✅</span> 🎬 <b>Video Reel (Opcional)</b></li></ul></div>""", unsafe_allow_html=True)
            st.button("👑 ELEGIR CONCESIONARIA", key="btn_agencia", type="primary", on_click=seleccionar_plan, args=("Concesionaria",))
        
        st.divider()
        st.button("⬅️ Volver a la App", on_click=volver_a_app)

    else:
        # PANTALLA DE REGISTRO Y PAGO
        st.info(f"🚀 Excelente elección: **Plan {st.session_state.plan_seleccionado}**")
        
        if not st.session_state.pedido_registrado:
            st.write("### 📝 Paso 1: Datos del Agente/Playa")
            
            def_nombre = ""
            def_email = ""
            def_tel = ""
            if st.session_state['usuario_activo']:
                u = st.session_state['usuario_activo']
                try: def_nombre = u.get('cliente', '').split(' ')[0]
                except: pass
                def_email = u.get('correo', '')
                def_tel = str(u.get('telefono', ''))

            with st.form("form_registro_pedido"):
                c_nom, c_ape = st.columns(2)
                nombre = c_nom.text_input("Nombre", value=def_nombre)
                apellido = c_ape.text_input("Apellido")
                email = st.text_input("Correo Electrónico (Para tu código de acceso)", value=def_email)
                telefono = st.text_input("Número de WhatsApp", value=def_tel)
                
                submitted = st.form_submit_button("✅ Confirmar y Ver Datos de Pago", type="primary")
                
                if submitted:
                    if nombre and apellido and email and telefono:
                        with st.spinner("Registrando pedido..."):
                            status = registrar_pedido(nombre, apellido, email, telefono, st.session_state.plan_seleccionado)
                            if status == "ERROR":
                                st.error("Error de conexión con la base de datos. Intente de nuevo.")
                            else:
                                st.session_state.pedido_registrado = True
                                st.session_state['temp_nombre'] = f"{nombre} {apellido}"
                                st.rerun()
                    else:
                        st.warning("⚠️ Completa todos los campos.")
            st.button("🔙 Volver atrás", on_click=cancelar_seleccion)

        else:
            st.success("✅ **¡Datos recibidos!** Realiza el pago para activar tu cuenta.")

            st.write("### 💳 Paso 2: Realiza el Pago")
            col_bank, col_wa = st.columns(2)
            with col_bank:
                st.markdown("""
                <div style="background-color:white; padding:15px; border-radius:10px; border:1px solid #ddd; color: #333;">
                <b>Banco:</b> ITAÚ <br>
                <b>Titular:</b> Ricardo Blanco <br>
                <b>Cuenta:</b> 320595209 <br>
                <b>Alias:</b> RUC 1911221-1 <br>
                <b>C.I.:</b> 1911221 <br>
                <b>RUC:</b> 1911221-1
                </div>
                """, unsafe_allow_html=True)
            with col_wa:
                nombre_cliente = st.session_state.get('temp_nombre', 'Nuevo Agente')
                mensaje_wp = f"Hola, soy *{nombre_cliente}*. Adjunto comprobante para *Plan {st.session_state.plan_seleccionado}* de AutoProp IA."
                mensaje_wp_url = mensaje_wp.replace(" ", "%20").replace("\n", "%0A")
                link_wp = f"https://wa.me/{ADMIN_WHATSAPP}?text={mensaje_wp_url}"
                
                st.markdown(f'<a href="{link_wp}" target="_blank" style="text-decoration:none;"><button style="background-color:#25D366; color:white; border:none; padding:15px; border-radius:8px; width:100%; font-weight:bold; cursor:pointer; font-size:1.1em; margin-top:10px; box-shadow: 0 4px 6px rgba(37, 211, 102, 0.3);">📲 Enviar Comprobante por WhatsApp</button></a>', unsafe_allow_html=True)
            st.divider()
            if st.button("🏁 Finalizar y Volver al Inicio"):
                volver_a_app()
    st.stop()

# =======================================================
# === APP PRINCIPAL (AUTOMOTOR) ===
# =======================================================
c_title, c_badge = st.columns([2, 1])
st.markdown(f"<h1 style='text-align: center; margin-bottom: 0;'>{NOMBRE_APP}</h1>", unsafe_allow_html=True)
st.markdown("<h3 style='text-align: center; color: #1E293B; font-weight: 600; margin-top: 0; font-size: 1.2rem;'>Inteligencia Artificial para Venta de Vehículos</h3>", unsafe_allow_html=True)

# --- GUÍA PASO A PASO AUTOMOTOR ---
with st.expander("ℹ️ ¿Cómo funciona AutoProp IA? (Guía Rápida)"):
    st.markdown("""
    ### 🚗 Tu Vendedor Digital Experto
    
    **1. 📸 Sube Fotos:** Carga fotos del vehículo (exterior, interior, motor). La IA las analizará.
    **2. 📝 Completa la Ficha:** Rellena los datos clave (Marca, Modelo, Año, Estado).
    **3. ✨ Genera Estrategia:** Pulsa el botón y obtendrás redacción persuasiva para redes y hashtags optimizados para el mercado motor.
    """)

es_pro = False
plan_actual = "INVITADO"
cupo_fotos = 0
puede_video = False

if st.session_state['usuario_activo']:
    es_pro = True
    user = st.session_state['usuario_activo']
    plan_str = str(user.get('plan', '')).lower()
    
    if 'concesionaria' in plan_str or 'agencia' in plan_str:
        cupo_fotos = 10
        plan_actual = "CONCESIONARIA"
        puede_video = True
    elif 'playa' in plan_str or 'estándar' in plan_str:
        cupo_fotos = 6
        plan_actual = "PLAYA"
    else:
        cupo_fotos = 3
        plan_actual = "BÁSICO"

    creditos_disponibles = int(user.get('limite', 0) if user.get('limite') != "" else 0)
    st.markdown(f'<div style="text-align:center; margin-top: 10px;"><span class="pro-badge">PLAN {plan_actual}</span></div>', unsafe_allow_html=True)
else:
    es_pro = False
    creditos_disponibles = st.session_state.get('guest_credits', 0)
    if MODO_LANZAMIENTO:
        plan_actual = "INVITADO VIP"
        cupo_fotos = 10
        puede_video = True 
        st.markdown('<div style="text-align:center; margin-top: 10px;"><span class="launch-badge">🚀 MODO LANZAMIENTO: ACCESO TOTAL</span></div>', unsafe_allow_html=True)
    else:
        plan_actual = "INVITADO"
        cupo_fotos = 0
        puede_video = False
        st.markdown('<div style="text-align:center; margin-top: 10px;"><span class="free-badge">MODO FREEMIUM</span></div>', unsafe_allow_html=True)

if not es_pro and not MODO_LANZAMIENTO:
    st.info("👈 **¿Sos Agente o tenés Playa?** Toca el botón rojo **'MENÚ'** para iniciar sesión.")

# =======================================================
# === 1. GALERÍA ===
# =======================================================
st.write("#### 1. 📸 Fotos del Vehículo")
uploaded_files = []

if es_pro or MODO_LANZAMIENTO:
    if creditos_disponibles <= 0:
        st.error("⛔ **Sin créditos.** Recarga tu plan para seguir vendiendo.")
        st.stop()
    
    uploaded_files = st.file_uploader("Subir fotos", type=["jpg", "png", "jpeg", "webp"], accept_multiple_files=True, key=f"uploader_{st.session_state['uploader_key']}")
    
    if uploaded_files:
        if len(uploaded_files) > cupo_fotos:
            st.error(f"⛔ **¡Demasiadas fotos!** Tu plan {plan_actual} solo permite {cupo_fotos} imágenes.")
            st.stop()
        
        st.success(f"✅ {len(uploaded_files)} fotos cargadas.")
        
        with st.expander("👁️ Ver fotos cargadas", expanded=False):
            cols = st.columns(4)
            for i, f in enumerate(uploaded_files):
                with cols[i%4]: st.image(Image.open(f), use_container_width=True)
else:
    st.info("🔒 **La carga de fotos y Visión IA es exclusiva para Miembros.**")

st.divider()

# =======================================================
# === 2. FICHA TÉCNICA (FORMULARIO AUTOMOTOR) ===
# =======================================================
st.write("#### 2. 📝 Ficha Técnica")

oper = st.radio("Operación", ["Venta", "Alquiler"], horizontal=True, key="v_oper")

with st.form("formulario_vehiculo"):
    c1, c2 = st.columns(2)

    with c1:
        # Selectores principales
        tipo_vehiculo = st.selectbox("Tipo de Vehículo", ["Automóvil (Sedán/Hatch)", "Camioneta/Pickup", "SUV", "Furgoneta/Van", "Camión Ligero", "Deportivo"], key="v_tipo")
        estado = st.radio("Estado", ["Usado", "0KM"], horizontal=True, key="v_estado")

        # Inputs de texto
        marca = st.text_input("Marca (Ej: Toyota, Kia)", key="v_marca")
        modelo = st.text_input("Modelo (Ej: Hilux, Picanto)", key="v_modelo")
        
        # Selectores de detalles
        col_ano, col_color = st.columns(2)
        with col_ano:
            year_val = st.number_input("Año", min_value=1990, max_value=2026, value=2020, step=1, format="%d", key="v_ano")
        with col_color:
             color_val = st.text_input("Color", key="v_color")

        origen = st.selectbox("Procedencia/Origen", ["Importado (Iquique/Vía Chile)", "Del Representante (Nacional)", "Importación Directa (USA/Europa)"], key="v_origen")

        # --- OPCIONES DE ALQUILER ---
        uso_alquiler = ""
        if oper == "Alquiler":
             st.markdown("ℹ️ **Opciones de Alquiler:**")
             uso_alquiler = st.selectbox("Uso permitido", ["Particular", "Plataforma (Uber/Bolt/MUV)"], key="v_uso_alquiler")

    with c2:
        st.write("**Detalles Mecánicos & Precio:**")
        transmision = st.selectbox("Transmisión", ["Automática", "Manual/Mecánica"], key="v_transmision")
        combustible = st.selectbox("Combustible", ["Nafta", "Diesel", "Híbrido", "Eléctrico", "Flex"], key="v_combustible")
        
        st.write("💰 **Precio:**")
        
        # Logica de precio diferenciada para alquiler
        frecuencia_pago = ""
        if oper == "Alquiler":
             col_mon, col_prec, col_frec = st.columns([1, 2, 2])
             with col_mon:
                  moneda = st.selectbox("Divisa", ["Gs.", "$us"], label_visibility="collapsed", key="v_moneda")
             with col_prec:
                  precio_val = st.number_input("Monto", min_value=0, step=50000, format="%d", label_visibility="collapsed", placeholder="Monto", key="v_precio")
             with col_frec:
                  frecuencia_pago = st.selectbox("Frecuencia", ["Diario", "Semanal", "Mensual"], label_visibility="collapsed", key="v_frecuencia_pago")
        else:
             col_mon, col_prec = st.columns([1, 2])
             with col_mon:
                  moneda = st.selectbox("Divisa", ["Gs.", "$us"], label_visibility="collapsed", key="v_moneda")
             with col_prec:
                  precio_val = st.number_input("Monto", min_value=0, step=1000000, format="%d", label_visibility="collapsed", placeholder="Monto", key="v_precio")

        if es_pro or MODO_LANZAMIENTO:
            st.write("📱 **WhatsApp para contacto:**")
            whatsapp_num = st.number_input("N° Celular (Sin 0 inicial, Ej: 961...)", min_value=0, step=1, format="%d", value=None,placeholder="Ej: 961123456", key="u_whatsapp")
        else:
             st.text_input("WhatsApp", placeholder="🔒 Solo Miembros PRO", disabled=True)

    deshabilitar_boton = False
    if (es_pro or MODO_LANZAMIENTO) and not uploaded_files:
        deshabilitar_boton = True
        st.warning("⚠️ **Sube las fotos del vehículo para activar la IA.**")
    
    submitted = st.form_submit_button("✨ Generar Descripción de Venta/Alquiler", type="primary", disabled=deshabilitar_boton)

# =======================================================
# === GENERACIÓN (LÓGICA AUTOMOTOR) ===
# =======================================================
if submitted:
    # Validaciones
    if not marca or not modelo or precio_val == 0:
        st.warning("⚠️ Completa Marca, Modelo y Precio (mayor a 0).")
        st.stop()
        
    permitido = False
    if es_pro and creditos_disponibles > 0: permitido = True
    elif not es_pro and st.session_state['guest_credits'] > 0: permitido = True
    else:
        st.error("⛔ Sin créditos suficientes.")
        st.stop()

    if permitido:
        estado_ia = st.status("🕵️ Iniciando análisis del vehículo...", expanded=True)
        
        # PASO 1: VALIDACIÓN (PORTERO)
        estado_ia.write("👁️ **Verificando que las fotos sean de vehículos...**")
        es_vehiculo_valido = validar_imagenes_vehiculos(uploaded_files)
        
        if not es_vehiculo_valido:
            estado_ia.update(label="❌ Error de validación", state="error", expanded=True)
            st.error("Lo siento, no puedo generar la descripción ya que tus fotos no parecen estar dentro de la categoría de vehículos (autos, camionetas, etc.).")
            st.stop()

        # PASO 2: GENERACIÓN
        try:
            estado_ia.write("✅ Fotos validadas.")
            estado_ia.write("🧠 **Analizando detalles (estado, equipamiento visible)...**")
            time.sleep(0.5)
            estado_ia.write("✍️ **Redactando estrategia de venta automotriz...**")

            precio_fmt = format_price_display(precio_val)
            texto_precio_final = f"{precio_fmt} {moneda}"
            
            detalles_alquiler_prompt = ""
            if oper == "Alquiler":
                 if frecuencia_pago: texto_precio_final += f" ({frecuencia_pago})"
                 detalles_alquiler_prompt = f". Uso permitido: {uso_alquiler}. Frecuencia de pago: {frecuencia_pago}."

            tono_venta = "centrado en la confiabilidad y estado."
            if estado == "0KM": tono_venta = "centrado en la exclusividad y garantía."
            if oper == "Alquiler" and "Plataforma" in uso_alquiler: tono_venta = "centrado en la economía y rentabilidad para trabajar."

            base_prompt = f"""Eres un Vendedor de Autos Experto y Copywriter Automotriz.
            DATOS TÉCNICOS:
            - Operación: {oper}{detalles_alquiler_prompt}
            - Vehículo: {marca} {modelo} {year_val}.
            - Tipo: {tipo_vehiculo}. Color: {color_val}.
            - Estado: {estado}. Origen: {origen}.
            - Mecánica: Transmisión {transmision}, Motor {combustible}.
            - Precio: {texto_precio_final}.
            """
            
            prompt_avanzado = f"""
            TUS INSTRUCCIONES MAESTRAS (OBLIGATORIO):
            
            1. 👁️ ANÁLISIS VISUAL DETALLADO:
               - Mira las fotos y DETECTA: llantas, cuero, pantalla, estado general. Menciona lo que ves.

            2. 🎯 ESTRATEGIA DE VENTA AUTOMOTRIZ:
               - Tono: Persuasivo, directo y {tono_venta}.
               - Destaca la procedencia ({origen}).
            
            OUTPUT (Genera 3 opciones):
            Opción 1: Venta Emocional.
            Opción 2: Venta Racional (Datos duros).
            Opción 3: Formato Corto para Redes.
            
            REGLAS:
            - Usa Markdown (**negritas**).
            - Link WhatsApp: https://wa.me/595{str(whatsapp_num)}
            - Incluye 10 hashtags relevantes a Paraguay.
            - PRECIO: Muestra siempre "{texto_precio_final}".
            
            {base_prompt}
            """

            content = [{"type": "text", "text": prompt_avanzado}]
            if (es_pro or MODO_LANZAMIENTO) and uploaded_files:
                for f in uploaded_files:
                    f.seek(0)
                    content.append({
                        "type": "image_url", 
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image(Image.open(f))}",
                            "detail": "low"
                        }
                    })

            res = client.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "user", "content": content}], temperature=0.7) 
            generated_text = res.choices[0].message.content

            cleaned_text = generated_text.replace("###", "🚗").replace("##", "✨").replace("# ", "🔥 ")
            
            # --- VIDEO REEL ---
            frases_video = []
            if puede_video:
                try:
                    lines = cleaned_text.split('\n')
                    for l in lines:
                        l = l.strip().replace("*", "").replace("🚗", "").replace("✨", "").replace("🔥", "")
                        if 10 < len(l) < 35 and not l.startswith("http"): phrases_video.append(l)
                    if len(frases_video) < 3:
                        frases_video = [f"{marca} {modelo} {year_val}", f"Estado: {estado}", "¡Contactanos hoy!"]
                    st.session_state['video_frases'] = frases_video[:5]
                except:
                    st.session_state['video_frases'] = [f"{marca} {modelo}", "Disponible", "Ver Precio"]

            # --- CONSUMO CRÉDITOS ---
            if es_pro:
                exito = descontar_credito(user['codigo'])
                if exito: st.session_state['usuario_activo']['limite'] = creditos_disponibles - 1
            else:
                if consumir_credito_invitado():
                    st.toast(f"🪙 Crédito de cortesía usado.", icon="✅")

            st.session_state['generated_result'] = cleaned_text
            estado_ia.update(label="✅ ¡Descripción lista!", state="complete", expanded=False)
            time.sleep(0.5) 
            estado_ia.empty() 
            st.rerun() 
            
        except Exception as e:
            st.error(f"Error en el proceso: {e}")
            estado_ia.update(label="❌ Error", state="error")

# =======================================================
# === MOSTRAR RESULTADOS ===
# =======================================================
if 'generated_result' in st.session_state:
    st.markdown('<div class="output-box">', unsafe_allow_html=True)
    st.subheader("🎉 Estrategia de Venta Generada:")
    st.markdown(st.session_state['generated_result'])
    
    # BOTONES SOCIALES
    c_wa, c_ig, c_fb, c_tk = st.columns(4)
    msg_url = urllib.parse.quote(st.session_state['generated_result'])
    
    svg_wa = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M380.9 97.1C339 55.1 283.2 32 223.9 32c-122.4 0-222 99.6-222 222 0 60.2 23.5 118.5 61.9 163.9L0 512l95.4-25.2c43.4 23.6 92.6 36.1 143.3 36.1 122.4 0 222-99.6 222-222 0-59.3-23.5-115.1-65.4-157zM223.9 471.1c-44.9 0-88.7-11.8-127.7-34.2L90.2 434l-47.6 12.6 12.7-46.4-6-10.5C25.1 346.6 12 296.4 12 244.1c0-116.9 95.1-212 211.9-212 56.6 0 109.8 22 149.9 62.1 40 40.1 62.1 93.3 62.1 149.9 0 116.9-95.1 212-212 212zm112.2-157.8c-6.1-3-36.4-18-42-20.1-5.6-2.1-9.7-3-13.7 3-4 6.1-15.6 19.5-19.1 23.5-3.5 4-7 4.5-13.1 1.5-6.1-3-25.7-9.5-48.9-30.2-18.1-16.1-30.3-36-33.8-42-3.5-6.1-.3-9.4 2.7-12.4 2.8-2.8 6.1-7.3 9.1-11 3-3.6 4-6.1 6.1-10.3 2.1-4.2 1-7.9-.5-11-1.5-3-13.7-33.1-18.8-45.3-5-12.1-10.1-10.4-13.7-10.6-3.5-.2-7.5-.2-11.5-.2-4 0-10.5 1.5-15.9 7.3-5.4 5.8-20.8 20.3-20.8 49.5 0 29.2 21 57.5 23.9 61.5 3 4 41.3 63.1 100.1 88.5 14 6 24.9 9.6 33.4 12.3 14.1 4.5 26.9 3.8 37.1 2.3 11.3-1.7 36.4-14.9 41.5-29.3 5.1-14.4 5.1-26.8 3.6-29.3-1.5-2.6-5.6-4-11.6-7z"/></svg>'
    svg_ig = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M224.1 141c-63.6 0-114.9 51.3-114.9 114.9s51.3 114.9 114.9 114.9S339 319.5 339 255.9 287.7 141 224.1 141zm0 189.6c-41.1 0-74.7-33.5-74.7-74.7s33.5-74.7 74.7-74.7 74.7 33.5 74.7 74.7-33.6 74.7-74.7 74.7zm146.4-194.3c0 14.9-12 26.8-26.8 26.8-14.9 0-26.8-12-26.8-26.8s12-26.8 26.8-26.8 26.8 12 26.8 26.8zm76.1 27.2c-1.7-35.9-9.9-67.7-36.2-93.9-26.2-26.2-58-34.4-93.9-36.2-37-2.1-147.9-2.1-184.9 0-35.8 1.7-67.6 9.9-93.9 36.1s-34.4 58-36.2 93.9c-2.1 37-2.1 147.9 0 184.9 1.7 35.9 9.9 67.7 36.2 93.9s58 34.4 93.9 36.2c37 2.1 147.9 2.1 184.9 0 35.9-1.7 67.7-9.9 93.9-36.2 26.2-26.2 34.4-58 36.2-93.9 2.1-37 2.1-147.9 0-184.9zm-49.6 259.7c-12.2 12.2-28.4 18.4-59.5 20-32.3 1.6-128.9 1.6-161.2 0-31-1.6-47.3-7.8-59.5-20-12.2-12.2-18.4-28.4-20-59.5-1.6-32.3-1.6-128.9 0-161.2 1.6-31 7.8-47.3 20-59.5 12.2-12.2 28.4-18.4 59.5-20 32.3-1.6 128.9-1.6 161.2 0 31 1.6 47.3 7.8 59.5z"/></svg>'
    svg_fb = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 512"><path d="M80 299.3V512H196V299.3h86.5l18-97.8H196V166.9c0-28.3 7.9-47.5 48.4-47.5h51.7V35.7c-9-1.2-39.6-3.9-75.3-3.9-74.5 0-125.5 45.5-125.5 128.9v72.8H80z"/></svg>'
    svg_tk = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512"><path d="M448,209.91a210.06,210.06,0,0,1-122.77-39.25V349.38A162.55,162.55,0,1,1,185,188.31V278.2a90.92,90.92,0,1,0,90.93,90.93V0H210.16V209.91A210.26,210.26,0,1,0,448,209.91Z"/></svg>'

    with c_wa: st.markdown(f'''<a href="https://wa.me/?text={msg_url}" target="_blank" class="social-btn btn-wp">{svg_wa} WhatsApp</a>''', unsafe_allow_html=True)
    with c_ig: st.markdown(f'''<a href="https://instagram.com" target="_blank" class="social-btn btn-ig">{svg_ig} Instagram</a>''', unsafe_allow_html=True)
    with c_fb: st.markdown(f'''<a href="https://facebook.com" target="_blank" class="social-btn btn-fb">{svg_fb} Facebook</a>''', unsafe_allow_html=True)
    with c_tk: st.markdown(f'''<a href="https://tiktok.com" target="_blank" class="social-btn btn-tk">{svg_tk} TikTok</a>''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # VIDEO
    if puede_video and uploaded_files:
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("🎬 **Video Reel Automotriz**")
        c_v1, c_v2, c_v3 = st.columns([1, 2, 1]) 
        
        if 'video_path' not in st.session_state:
            if st.button("🎥 GENERAR VIDEO AHORA"):
                if not MOVIEPY_AVAILABLE:
                    st.error("⚠️ Librería de video no disponible.")
                else:
                    st_video = st.status("🎞️ Renderizando video...", expanded=True)
                    try:
                        frases = st.session_state.get('video_frases', [NOMBRE_APP])
                        path_video = crear_reel_vertical(uploaded_files, frases, st_video)
                        if path_video:
                            st.session_state['video_path'] = path_video
                            st_video.update(label="✅ Video Listo", state="complete", expanded=False)
                            time.sleep(0.5)
                            st_video.empty()
                            st.rerun()
                        else:
                            st.warning("⚠️ Error al generar video.")
                    except Exception as e:
                        st.error(f"Error video: {e}")
        
        if 'video_path' in st.session_state:
            with c_v2:
                st.markdown('<div class="reel-wrapper">', unsafe_allow_html=True)
                st.video(st.session_state['video_path'])
                st.markdown('</div>', unsafe_allow_html=True)
                with open(st.session_state['video_path'], "rb") as file:
                    st.download_button("⬇️ Descargar Video", file, "reel_vehiculo.mp4", "video/mp4", type="primary")

    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚘 Nuevo Vehículo (Limpiar)", key="clean_bottom", type="secondary"):
        limpiar_formulario()

# =======================================================
# === AVISO LEGAL ===
# =======================================================
st.markdown("<br><br>", unsafe_allow_html=True)
with st.expander("⚖️ Aviso Legal y Privacidad"):
    st.markdown("""
    <div class="legal-text">
    AppyProp IA (Versión Automotor) es una herramienta de procesamiento en tiempo real.
    <ul>
        <li><b>Privacidad:</b> Las fotos y datos se eliminan al cerrar la sesión.</li>
        <li><b>Responsabilidad:</b> Verifique siempre los textos generados antes de publicar.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
