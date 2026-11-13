# -*- coding: utf-8 -*-
"""
CÓDIGO MENTAL - Bot v2.1 ELITE MASTER PREMIUM
Cambios v2.1 sobre v2.0:
  - Duración video 8-12 min (antes 7-11)
  - Palabras por punto 320-400 (antes 250-320)
  - Shorts 35-42 seg (antes 32-50)
  - Programación slots batch MISMO DÍA (fix bug de días cruzados)
  - Descripción SEO elite: keyword en primeras 2 líneas
  - Hashtags optimizados (3-5 relevantes, no 15 spam)
  - Tags mix estratégico: exactos + broad + long-tail + preguntas
  - CTA shorts con 4 variantes rotativas
  - Logs trazables con resumen final de shorts
"""
import asyncio
import bisect
import gc
import json
import os
import random
import re
import sys
import time
import traceback
import unicodedata
import ssl
import socket
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import edge_tts
import numpy as np
import requests
import urllib3
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from moviepy.editor import (
    AudioFileClip, CompositeAudioClip, VideoClip, VideoFileClip,
    concatenate_audioclips,
)
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

try:
    import json5
except ImportError:
    json5 = None

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =================================================================
# CONFIGURACIÓN
# =================================================================
TZ = ZoneInfo("America/Mexico_City")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL   = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
DEEPSEEK_URL     = "https://api.deepseek.com/v1/chat/completions"

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN  = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_MODEL      = "@cf/black-forest-labs/flux-1-schnell"

YOUTUBE_USER_TOKEN = json.loads(os.getenv("YOUTUBE_USER_TOKEN") or "{}")
PLAYLIST_ID        = os.getenv("YOUTUBE_PLAYLIST_ID", "")
CANAL_LINK         = "https://www.youtube.com/@codigomentalnovisible"

ESTADO_FILE  = "estado_shorts.json"
TITULOS_FILE = "titulos_publicados.json"
TEMAS_FILE   = "temas_shorts.json"

# ⚡ NUEVO v2.1: duración 8-12 min para mid-roll ads + watch time óptimo
DURACION_MINIMA_SEGUNDOS = 480   # 8 min (mínimo monetizable + mid-roll ads)
DURACION_MAXIMA_SEGUNDOS = 720   # 12 min (techo antes de perder retention)
NUM_PUNTOS               = 5
MAX_INTENTOS_EXPANSION   = 1

# ⚡ NUEVO v2.1: shorts en 35-42 seg (28-36 contenido + ~6 CTA)
SHORT_CONTENT_MIN = 28
SHORT_CONTENT_MAX = 36

SEG_MAX_PALABRAS = 45
SEG_ESCENA       = 14.0
W, H, FPS        = 1920, 1080, 24
VOL_FONDO        = 0.10
USAR_IMAGENES_IA = os.getenv("USAR_IMAGENES_IA", "true").lower() == "true"
GENERAR_SHORT    = os.getenv("GENERAR_SHORT", "true").lower() == "true"
PROGRAMAR_PICO   = os.getenv("PROGRAMAR_PICO", "true").lower() == "true"

HORA_LARGO              = int(os.getenv("HORA_LARGO", "8"))
VARIACION_MINUTOS_LARGO = int(os.getenv("VARIACION_MINUTOS_LARGO", "30"))
HORA_SHORT_1            = int(os.getenv("HORA_SHORT_1", "10"))
VARIACION_MINUTOS_SHORT_1 = int(os.getenv("VARIACION_MINUTOS_SHORT_1", "45"))
HORA_SHORT_2            = int(os.getenv("HORA_SHORT_2", "15"))
VARIACION_MINUTOS_SHORT_2 = int(os.getenv("VARIACION_MINUTOS_SHORT_2", "60"))
INTERVALO_MIN_HORAS     = float(os.getenv("INTERVALO_MIN_HORAS", "20"))
ACTIVAR_DISCLOSURE_IA   = True

DISCLOSURE_TEXT = (
    "\n\n⚠️ Este contenido es elaborado con asistencia de Inteligencia Artificial "
    "para garantizar la máxima claridad, precisión y calidad visual."
)

VOZ_CANAL = {"voz": "es-MX-DaliaNeural", "tono": "+0Hz"}
VOCES_RESPALDO = ["es-MX-DaliaNeural", "es-MX-JorgeNeural", "es-ES-ElviraNeural",
                  "es-US-PalomaNeural", "es-CO-SalomeNeural"]
RATE_ETAPA  = {"gancho": "+8%", "contexto": "+5%", "desarrollo": "+4%", "conclusion": "+2%"}
PAUSA_ETAPA = {"gancho": 0.4,   "contexto": 0.5,  "desarrollo": 0.45, "conclusion": 0.7}

FONDOS_DISPONIBLES = [
    "Celestial Drift.mp3", "Astral Alignment.mp3", "Deep Focus.mp3",
    "Silent Mind.mp3", "Inner Cosmos.mp3", "Zenith.mp3",
]
FUENTE_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/anton/Anton-Regular.ttf"

CTA_SHORTS = [
    "Esto es solo una parte. El video completo está en el canal. Suscríbete ahora.",
    "El análisis completo te espera en el canal. Suscríbete para verlo.",
    "Si esto te movió algo, el video completo está en el canal. Suscríbete.",
    "No te quedes con la duda. El video completo ya está en el canal.",
]

# =================================================================
# TEMAS — PSICOLOGÍA, ESTOICISMO, NEUROCIENCIA
# =================================================================
TEMAS = [
    {"tema": "detox_dopamina", "seed": "detox dopamina",
     "angulo": "Cómo resetear tu cerebro en 30 días y recuperar la motivación real.",
     "keywords": ["detox dopamina", "dopamina", "motivación", "adicción", "enfoque"],
     "contextos": ["vida moderna", "smartphone", "adicción digital", "productividad"],
     "hashtags": ["#Dopamina", "#Neurociencia"]},

    {"tema": "lenguaje_corporal", "seed": "lenguaje corporal",
     "angulo": "Las señales no verbales que revelan lo que la gente realmente piensa.",
     "keywords": ["lenguaje corporal", "señales", "comunicación no verbal", "psicología"],
     "contextos": ["oficina", "negociación", "reunión", "entrevista"],
     "hashtags": ["#LenguajeCorporal", "#Psicologia"]},

    {"tema": "psicologia_oscura", "seed": "psicología oscura",
     "angulo": "Las técnicas de manipulación que usan los manipuladores y cómo defenderte.",
     "keywords": ["psicología oscura", "manipulación", "narcisismo", "gaslighting"],
     "contextos": ["relaciones", "trabajo", "familia", "amistad"],
     "hashtags": ["#PsicologiaOscura", "#Manipulacion"]},

    {"tema": "estoicismo", "seed": "estoicismo",
     "angulo": "Cómo aplicar la sabiduría de Marco Aurelio al caos moderno.",
     "keywords": ["estoicismo", "marco aurelio", "seneca", "filosofia", "disciplina"],
     "contextos": ["vida moderna", "trabajo", "relaciones", "fracaso"],
     "hashtags": ["#Estoicismo", "#MarcoAurelio"]},

    {"tema": "habitos_atomicos", "seed": "hábitos atómicos",
     "angulo": "Cómo construir hábitos que duran y eliminar los que te destruyen.",
     "keywords": ["hábitos", "habitos atomicos", "productividad", "rutinas"],
     "contextos": ["mañana", "trabajo", "ejercicio", "estudio"],
     "hashtags": ["#Habitos", "#Productividad"]},

    {"tema": "ansiedad", "seed": "ansiedad",
     "angulo": "Cómo calmar tu mente ansiosa con técnicas basadas en neurociencia.",
     "keywords": ["ansiedad", "estrés", "respiración", "mindfulness"],
     "contextos": ["vida diaria", "trabajo", "relaciones", "insomnio"],
     "hashtags": ["#Ansiedad", "#SaludMental"]},

    {"tema": "concentracion", "seed": "concentración profunda",
     "angulo": "Cómo recuperar la capacidad de concentrarte en un mundo de distracciones.",
     "keywords": ["concentración", "foco", "deep work", "productividad"],
     "contextos": ["trabajo", "estudio", "oficina", "home office"],
     "hashtags": ["#Concentracion", "#DeepWork"]},

    {"tema": "inteligencia_emocional", "seed": "inteligencia emocional",
     "angulo": "Cómo dominar tus emociones en lugar de que ellas te dominen a ti.",
     "keywords": ["inteligencia emocional", "emociones", "autocontrol", "empatia"],
     "contextos": ["relaciones", "trabajo", "familia", "conflicto"],
     "hashtags": ["#InteligenciaEmocional", "#Emociones"]},

    {"tema": "sesgos_cognitivos", "seed": "sesgos cognitivos",
     "angulo": "Los sesgos que tu cerebro usa para engañarte todos los días.",
     "keywords": ["sesgos cognitivos", "pensamiento", "psicología", "decisión"],
     "contextos": ["decisiones", "compras", "relaciones", "política"],
     "hashtags": ["#SesgosCognitivos", "#Psicologia"]},

    {"tema": "memoria", "seed": "técnicas de memoria",
     "angulo": "Cómo aprender más rápido usando el método de los campeones de memoria.",
     "keywords": ["memoria", "aprendizaje", "estudio", "técnicas"],
     "contextos": ["estudio", "examen", "trabajo", "idiomas"],
     "hashtags": ["#Memoria", "#Aprendizaje"]},

    {"tema": "sueno", "seed": "sueño y rendimiento",
     "angulo": "Cómo dormir mejor para rendir al máximo al día siguiente.",
     "keywords": ["sueño", "dormir bien", "descanso", "rendimiento"],
     "contextos": ["recámara", "rutina nocturna", "insomnio", "energía"],
     "hashtags": ["#Sueño", "#Descanso"]},

    {"tema": "disciplina", "seed": "disciplina y fuerza de voluntad",
     "angulo": "Cómo construir una disciplina que no depende de la motivación.",
     "keywords": ["disciplina", "fuerza de voluntad", "autocontrol", "consistencia"],
     "contextos": ["vida diaria", "ejercicio", "trabajo", "hábitos"],
     "hashtags": ["#Disciplina", "#Autocontrol"]},

    {"tema": "banderas_rojas", "seed": "banderas rojas en relaciones",
     "angulo": "Las señales de alarma que debes detectar antes de que sea tarde.",
     "keywords": ["banderas rojas", "relaciones toxicas", "narcisismo", "manipulacion"],
     "contextos": ["pareja", "amistad", "trabajo", "familia"],
     "hashtags": ["#BanderasRojas", "#Relaciones"]},

    {"tema": "procrastinacion", "seed": "procrastinación",
     "angulo": "Por qué procrastinas y cómo hackear tu cerebro para dejar de hacerlo.",
     "keywords": ["procrastinación", "productividad", "postergar", "motivacion"],
     "contextos": ["trabajo", "estudio", "tareas", "metas"],
     "hashtags": ["#Procrastinacion", "#Productividad"]},

    {"tema": "soledad", "seed": "soledad y crecimiento",
     "angulo": "Cómo transformar la soledad en tu mayor ventaja competitiva.",
     "keywords": ["soledad", "autoconocimiento", "crecimiento", "independencia"],
     "contextos": ["vida moderna", "trabajo remoto", "transiciones", "silencio"],
     "hashtags": ["#Soledad", "#Crecimiento"]},

    {"tema": "carisma", "seed": "carisma y presencia",
     "angulo": "Los hábitos que hacen que las personas magnéticas te escuchen.",
     "keywords": ["carisma", "presencia", "influencia", "confianza"],
     "contextos": ["reuniones", "presentaciones", "entrevistas", "networking"],
     "hashtags": ["#Carisma", "#Influencia"]},

    {"tema": "dinero_mentalidad", "seed": "mentalidad de dinero",
     "angulo": "Los patrones psicológicos que separan a ricos de pobres.",
     "keywords": ["mentalidad de dinero", "riqueza", "psicología financiera", "abundancia"],
     "contextos": ["finanzas", "inversión", "trabajo", "hábitos"],
     "hashtags": ["#Mentalidad", "#Dinero"]},

    {"tema": "estoicismo_amor", "seed": "estoicismo y amor",
     "angulo": "Cómo amar sin perderte usando la sabiduría estoica.",
     "keywords": ["estoicismo", "amor", "relaciones", "desapego"],
     "contextos": ["pareja", "ruptura", "autoconocimiento", "relaciones"],
     "hashtags": ["#Estoicismo", "#Amor"]},

    {"tema": "mentalidad_crecimiento", "seed": "mentalidad de crecimiento",
     "angulo": "Cómo cambiar tu mentalidad fija por una de crecimiento (Carol Dweck).",
     "keywords": ["mentalidad de crecimiento", "fixed mindset", "aprendizaje", "fracaso"],
     "contextos": ["estudio", "trabajo", "metas", "fracaso"],
     "hashtags": ["#MentalidadDeCrecimiento", "#Psicologia"]},

    {"tema": "miedo_al_rechazo", "seed": "miedo al rechazo",
     "angulo": "Cómo superar el miedo a lo que los demás piensan de ti.",
     "keywords": ["miedo al rechazo", "autoestima", "aprobación", "confianza"],
     "contextos": ["relaciones", "trabajo", "vida social", "entrevistas"],
     "hashtags": ["#MiedoAlRechazo", "#Autoestima"]},
]

# =================================================================
# FORMATOS Y PERFILES
# =================================================================
FORMATOS_NARRACION = [
    {"nombre": "lista_educativa",
     "instruccion": ("Formato LISTA EDUCATIVA. El narrador presenta los puntos de forma "
                     "numerada y progresiva, con un ejemplo cotidiano por punto. "
                     "Cada punto debe sentirse autoconclusivo pero enlazado al tema global.")},
    {"nombre": "caso_de_estudio",
     "instruccion": ("Formato CASO DE ESTUDIO. Presenta a una persona concreta (nombre, "
                     "edad, contexto) y analiza su situación desde la psicología. "
                     "El espectador debe identificarse con el caso.")},
    {"nombre": "explicacion_cientifica",
     "instruccion": ("Formato EXPLICACIÓN CIENTÍFICA. Cita estudios, autores y mecanismos "
                     "cerebrales. Explica POR QUÉ funciona algo, no solo QUÉ funciona. "
                     "Tono accesible pero con autoridad.")},
    {"nombre": "historia_personal",
     "instruccion": ("Formato HISTORIA PERSONAL. Narra en primera persona un cambio real "
                     "del narrador (ficticio pero creíble). Conecta la vivencia con la ciencia.")},
    {"nombre": "analogia_poderosa",
     "instruccion": ("Formato ANALOGÍA PODEROSA. Explora el tema a través de una metáfora "
                     "central (jardín, máquina, ciudad, etc.) que hace tangible lo abstracto.")},
]

PERFILES_NARRADOR = [
    "psicólogo clínico con consulta privada",
    "coach de alto rendimiento",
    "profesor de filosofía aplicada",
    "neurocientífico divulgador",
    "terapeuta cognitivo-conductual",
    "escritor de desarrollo personal",
    "emprendedor serial con background en psicología",
    "ex-monje que estudió estoicismo",
]

# =================================================================
# UTILIDADES
# =================================================================
def cargar_json(ruta, default):
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def guardar_json(ruta, data):
    tmp = ruta + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, ruta)

def cargar_estado():
    estado = cargar_json(ESTADO_FILE, {})
    estado.setdefault("ultimos_fondos", [])
    estado.setdefault("videos", [])
    estado.setdefault("temas_recientes", [])
    return estado

def parsear_json(texto):
    if not texto:
        raise ValueError("respuesta vacía")
    t = re.sub(r"```(?:json)?", " ", texto, flags=re.I)
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        raise ValueError("sin JSON")
    t = t[i:j + 1]
    t = re.sub(r",\s*([}\]])", r"\1", t)
    if json5:
        try:
            return json5.loads(t)
        except Exception:
            pass
    return json.loads(t, strict=False)

def llm(prompt, temperature=0.8, max_tokens=1500, json_mode=False, system=None, intentos=3):
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    payload = {"model": DEEPSEEK_MODEL, "messages": msgs,
               "temperature": temperature, "max_tokens": max_tokens}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    for i in range(intentos):
        try:
            r = requests.post(DEEPSEEK_URL, headers=headers, json=payload, timeout=150)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"⚠️ LLM intento {i+1}/{intentos}: {e}")
            time.sleep(5 * (i + 1))
    return None

def fmt_ts(seg):
    seg = int(seg)
    h, m, s = seg // 3600, seg % 3600 // 60, seg % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

# =================================================================
# HISTORIAL
# =================================================================
def titulo_ya_publicado(titulo):
    data = cargar_json(TITULOS_FILE, {"titulos": []})
    n = titulo.lower().strip()
    p1 = set(re.findall(r"\w+", n))
    for t in data["titulos"]:
        tn = t.lower().strip()
        if n == tn:
            return True
        p2 = set(re.findall(r"\w+", tn))
        if len(p1) > 3 and len(p2) > 3 and len(p1 & p2) / min(len(p1), len(p2)) > 0.7:
            return True
    return False

def guardar_titulo(titulo):
    data = cargar_json(TITULOS_FILE, {"titulos": []})
    if titulo not in data["titulos"]:
        data["titulos"].append(titulo)
    data["titulos"] = data["titulos"][-100:]
    guardar_json(TITULOS_FILE, data)

def tema_ya_usado(tema, umbral=0.5):
    data = cargar_json(TEMAS_FILE, {"temas": []})
    nuevas = set(re.findall(r"\w+", str(tema).lower()))
    for antiguo in data["temas"][-20:]:
        if not isinstance(antiguo, str) or len(antiguo) > 80:
            continue
        viejas = set(re.findall(r"\w+", antiguo.lower()))
        union = nuevas | viejas
        if union and len(nuevas & viejas) / len(union) > umbral:
            return True
    return False

def guardar_tema(tema):
    data = cargar_json(TEMAS_FILE, {"temas": []})
    data["temas"] = [t for t in data["temas"] if isinstance(t, str) and len(t) < 80]
    if isinstance(tema, str) and len(tema) < 80 and tema not in data["temas"]:
        data["temas"].append(tema)
    data["temas"] = data["temas"][-20:]
    guardar_json(TEMAS_FILE, data)

# =================================================================
# YOUTUBE
# =================================================================
def crear_cliente_youtube():
    try:
        creds = Credentials.from_authorized_user_info(YOUTUBE_USER_TOKEN)
        return build("youtube", "v3", credentials=creds)
    except Exception as e:
        print(f"⚠️ YouTube cliente: {e}")
        return None

def sugerencias_youtube(seed):
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search", timeout=10,
                         params={"client": "firefox", "ds": "yt", "hl": "es", "gl": "mx", "q": seed})
        return [s for s in r.json()[1] if isinstance(s, str)][:8]
    except Exception:
        return []

def puntuar_demanda(youtube, consulta):
    if youtube is None:
        return None
    try:
        desde = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        q = f"psicología {consulta}"
        r = youtube.search().list(part="id", q=q, type="video", order="viewCount",
                                  publishedAfter=desde, relevanceLanguage="es",
                                  regionCode="MX", maxResults=8).execute()
        ids = [i["id"]["videoId"] for i in r.get("items", [])]
        if not ids:
            return 0
        s = youtube.videos().list(part="statistics", id=", ".join(ids)).execute()
        vistas = [int(i["statistics"].get("viewCount", 0)) for i in s.get("items", [])]
        return sum(vistas) / len(vistas) if vistas else 0
    except Exception:
        return None

def actualizar_rendimiento(youtube, estado):
    ids = [v["id"] for v in estado["videos"][-30:] if v.get("id")]
    if not ids or youtube is None:
        return
    try:
        r = youtube.videos().list(part="statistics", id=", ".join(ids)).execute()
        vistas = {i["id"]: int(i["statistics"].get("viewCount", 0)) for i in r.get("items", [])}
        for v in estado["videos"]:
            if v.get("id") in vistas:
                v["vistas"] = vistas[v["id"]]
    except Exception:
        pass

def elegir_tema(estado, youtube):
    recientes = estado["temas_recientes"][-6:]
    pool = [t for t in TEMAS if t["tema"] not in recientes] or TEMAS[:]
    candidatos = random.sample(pool, min(5, len(pool)))
    acum = {}
    for v in estado["videos"]:
        if "vistas" in v:
            acum.setdefault(v["tema"], []).append(v["vistas"])
    rend = {k: sum(x) / len(x) for k, x in acum.items()}
    max_r = max(rend.values()) if rend else 1
    demandas = {t["tema"]: puntuar_demanda(youtube, t["seed"]) for t in candidatos}
    max_d = max([d for d in demandas.values() if d] or [1])

    def score(t):
        d = demandas[t["tema"]]
        sd = d / max_d if d else 0.4
        sr = rend[t["tema"]] / max_r if t["tema"] in rend and max_r else 0.6
        return 0.5 * sd + 0.5 * sr + random.uniform(0, 0.2)

    elegido = max(candidatos, key=score)
    print(f"🎯 Tema elegido: {elegido['tema']}")
    return elegido

# =================================================================
# TÍTULOS
# =================================================================
GANCHOS = [
    "nunca", "nadie", "jamás", "nadie te", "prohibido", "secreto",
    "verdad", "nadie quiere", "no te dijeron", "ocultan",
    "cambia", "rompe", "destruye", "mejor", "peor", "por qué",
    "cómo", "si ", "cuando", "5 ", "7 ", "3 ", "10 ", "?", "!",
    "nadie", "evita", "deja de", "empieza a",
]
PROHIBIDAS = ["testimonio real", "caso real", "100% real", "verídico", "comprobado",
              "garantizado", "secreto revelado", "hack", "truco", "trucos"]
GENERICAS = ["psicologia", "filosofia", "relato", "historia de"]

def limpiar_titulo(t):
    t = t.strip().strip('"').strip("'")
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"\s*[-|–]\s*psicología.*$", "", t, flags=re.I)
    t = t.rstrip(".")
    palabras = t.split()
    caps = [w for w in palabras if len(re.sub(r"\W", " ", w)) >= 3 and w.isupper()]
    if len(caps) > 3:
        keep = set(caps[:2])
        palabras = [w if (not w.isupper() or w in keep or len(w) < 3) else w.capitalize()
                    for w in palabras]
    return " ".join(palabras)

def puntuar_titulo(t, dato_contraintuitivo=""):
    s, n, tl = 0, len(t), t.lower()
    if 45 <= n <= 68:
        s += 4
    elif 30 <= n < 45 or 68 < n <= 80:
        s += 2
    elif n > 95 or n < 25:
        s -= 6
    if re.search(r"\d", t):
        s += 2
    s += min(3, sum(1 for g in GANCHOS if g in tl))

    if re.search(r'\bsi\b.{1,60}(nunca|no\s)', tl, re.I | re.S):
        s += 6
    if re.search(r'\b\d{1,2}\s+(señales|habitos|hábitos|claves|trucos|reglas|formas|maneras|razones)', tl):
        s += 4

    if dato_contraintuitivo:
        dc_words = set(re.findall(r"\w+", dato_contraintuitivo.lower())) - {
            "de", "la", "el", "que", "y", "en", "un", "una", "por", "para", "con", "los", "las"}
        tit_words = set(re.findall(r"\w+", tl))
        if len(dc_words & tit_words) >= 2:
            s += 5

    if re.search(r'\b(menos|peor|nunca|deja de|evita|no hagas|no debes)\b', tl):
        s += 3

    caps = re.findall(r"\b[A-ZÁÉÍÓÚÑ]{4,}\b", t)
    s += 2 if 1 <= len(caps) <= 2 else (-3 if len(caps) > 3 else 0)
    if any(p in tl for p in PROHIBIDAS):
        s -= 8
    if any(tl.startswith(g) for g in GENERICAS):
        s -= 6
    if "!" in t:
        s -= 1
    return s

def elegir_titulo(candidatos, dato_contraintuitivo=""):
    puntuados = []
    for c in candidatos:
        if not isinstance(c, str):
            continue
        base = limpiar_titulo(c)
        if len(base) < 25 or titulo_ya_publicado(base):
            continue
        puntuados.append((puntuar_titulo(base, dato_contraintuitivo), base))
    if not puntuados:
        return None
    puntuados.sort(reverse=True)
    for sc, t in puntuados[:4]:
        print(f"   📝 [{sc:>2}] {t}")
    return puntuados[0][1][:100]

def elegir_texto_portada(opciones, titulo):
    pt = set(re.findall(r"\w+", titulo.lower()))
    mejor = None
    for o in opciones or []:
        if not isinstance(o, str):
            continue
        o = re.sub(r"[^\w¿?¡! ]", "", o).strip().upper()
        w = o.split()
        if not 1 <= len(w) <= 4:
            continue
        solape = len({x.lower() for x in w} & pt) / len(w)
        sc = (3 if len(w) in (2, 3) else 1) - 2 * solape + (1 if "?" in o else 0)
        if mejor is None or sc > mejor[0]:
            mejor = (sc, o)
    return mejor[1] if mejor else "MENTALIDAD"

# =================================================================
# GENERACIÓN DE CONTENIDO
# =================================================================
ESQUEMA_PLAN = """{
 "titulos": ["6 títulos de 45-68 caracteres con ESTRUCTURA DISTINTA. NUNCA termines con '| Psicología'. AL MENOS 3 deben incluir el dato_contraintuitivo o una contradicción ('menos', 'nunca', 'deja de'). Combina: 'Si [situación], NUNCA [acción]'"],
 "tema_central": "descripción breve del tema",
 "anio_estudio": 2023,
 "protagonista": "nombre de pila del narrador (ej: Daniel, Andrea)",
 "dato_contraintuitivo": "CRÍTICO: el dato más sorprendente que rompe expectativas. Ej: 'sonreír más te hace menos creíble', 'estudiar más horas reduce el aprendizaje', 'la multitarea baja el CI 10 puntos'. Debe aparecer en AL MENOS 3 de los 6 títulos",
 "gancho": "1-2 frases (máx 35 palabras) que abren el video con el dato_contraintuitivo en primera persona",
 "resumen": "sinopsis de 2-3 oraciones sin spoilers",
 "palabras_clave": ["5 keywords SEO en español, la primera es el keyword principal del video"],
 "palabras_portada": ["3 opciones de 2-3 palabras EN MAYÚSCULAS, impacto visual"],
 "miniatura_escena": "4-6 palabras en inglés para buscar/imagen (ej: brain scan, nervous person meeting, two people arguing)",
 "descripcion_gancho": "2 líneas: la primera con el keyword principal y una promesa concreta; la segunda invita a suscribirse",
 "titulo_short": "gancho de máx 55 caracteres para YouTube Short",
 "pregunta_comentario": "pregunta corta que invite a comentar",
 "tags": ["10 tags ULTRA-ESPECÍFICOS: 2-3 del tema central, 2-3 de la mecánica, 1-2 preguntas de audiencia, 1-2 'psicologia + elemento', 1-2 'estoicismo + elemento'"],
 "puntos": [{"titulo": "2-4 palabras con intriga", "resumen": "qué se explica y qué idea clave se deja"}]
}"""

def generar_plan(tema, contexto, sugerencias, titulos_previos, formato, perfil):
    prev = "\n".join(f"- {t}" for t in titulos_previos) or "Ninguno"
    sug  = "\n".join(f"- {s}" for s in sugerencias) or "Ninguna"

    prompt = f"""Eres showrunner de un canal de psicología aplicada en español (México/Latam) con millones de vistas.
Diseña el PLAN de un video educativo de ~9-11 minutos, con {NUM_PUNTOS} puntos principales.

TEMA: {tema['tema']} | ÁNGULO: {tema['angulo']}
CONTEXTO: {contexto}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO OBLIGATORIO: {formato['nombre'].upper()}
{formato['instruccion']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PERFIL DEL NARRADOR: {perfil}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BÚSQUEDAS REALES YOUTUBE: {sug}
TÍTULOS YA PUBLICADOS (no repetir): {prev}

━━━ REGLA CRÍTICA: DATO CONTRAINTUITIVO ━━━
El campo 'dato_contraintuitivo' es el corazón del CTR. Debe ser un dato que ROMPE
la intuición del espectador. Ejemplos que funcionan:
  • "sonreír más te hace menos creíble"
  • "estudiar más horas reduce el aprendizaje"
  • "la multitarea baja el CI 10 puntos"
  • "dormir menos de 6h equivale a estar ebrio"
  • "los introvertidos son mejores líderes"

REGLAS DE TÍTULO:
1. NUNCA termines con "| Psicología" ni fórmulas genéricas.
2. AL MENOS 3 de los 6 títulos deben incluir el dato_contraintuitivo o una contradicción.
3. Cada título con estructura DISTINTA:
   - Advertencia: "Nunca [verbo] cuando [contexto]"
   - Contradicción: "Mientras más [X], menos [Y]"
   - Confesión: "Lo que descubrí sobre [tema] cambió todo"
   - Pregunta: "¿Por qué [comportamiento] te está [consecuencia]?"
   - Número específico: "5 señales de que [X]"
   - Paradoja: "[acción obvia] te hace [resultado opuesto]"
4. Combina "Si [situación], NUNCA [acción]" cuando encaje.
5. Mayúsculas solo para 1-2 palabras de impacto.

REGLAS DE CONTENIDO:
1. Cada punto debe aportar VALOR concreto (no relleno).
2. Incluye al menos 1 estudio o autor por video.
3. El gancho debe INCLUIR el dato_contraintuitivo.
4. Cada punto termina con una idea que el espectador pueda aplicar hoy.

Responde SOLO con este JSON:
{ESQUEMA_PLAN}"""
    txt = llm(prompt, temperature=0.9, max_tokens=2400, json_mode=True)
    plan = parsear_json(txt)
    if not (isinstance(plan.get("titulos"), list) and len(plan["titulos"]) >= 3
            and isinstance(plan.get("puntos"), list) and len(plan["puntos"]) >= NUM_PUNTOS
            and plan.get("gancho") and plan.get("palabras_portada")
            and plan.get("dato_contraintuitivo")):
        raise ValueError("plan incompleto")
    return plan

def limpiar_texto_narracion(t):
    t = re.sub(r"[\U00010000-\U0010ffff]", " ", t)
    t = re.sub(r"(?im)^\s*(punto|cap[ií]tulo|parte)\s*\d+.\s*$", " ", t)
    t = re.sub(r"\[[^\]]*\]", " ", t)
    t = re.sub(r"[*_#>`~]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def generar_puntos(plan, tema, contexto):
    puntos = plan["puntos"][:NUM_PUNTOS]
    indice = "\n".join(f"{i+1}. {p.get('titulo','')}: {p.get('resumen','')}"
                       for i, p in enumerate(puntos))
    textos = []
    formato    = plan.get("_formato_instruccion", "Explicación directa.")
    perfil     = plan.get("_perfil_narrador", "psicólogo")
    nombre_fmt = plan.get("_nombre_formato", "lista_educativa")
    dato_c     = plan.get("dato_contraintuitivo", "un dato sorprendente")

    for i, punto in enumerate(puntos):
        previo = textos[-1][-600:] if textos else ""
        if i == 0:
            extra = (f"Empieza EXACTAMENTE con: \"{plan['gancho']}\" y enseguida "
                     f"INTEGRA el dato contraintuitivo '{dato_c}' como el detonante.")
        elif i == len(puntos) - 1:
            extra = ("Cierra con un cierre que sintetice y deje al espectador con "
                     "una acción concreta para hoy. Vuelve a mencionar el dato "
                     "contraintuitivo para reforzarlo.")
        else:
            extra = (f"Conecta con el punto anterior y asegúrate de que el dato "
                     f"contraintuitivo '{dato_c}' se mencione si encaja.")

        prompt = f"""Escribe el PUNTO {i+1} de {len(puntos)} de un video educativo de psicología.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FORMATO: {nombre_fmt.upper()}
{formato}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NARRADOR: {plan.get('protagonista', 'Daniel')} — {perfil}
TEMA: {tema['angulo']}
DATO CONTRAINTUITIVO: "{dato_c}"
SINOPSIS: {plan.get('resumen', '')}
ÍNDICE COMPLETO: {indice}
ESTE PUNTO: {punto.get('titulo', '')} → {punto.get('resumen', '')}
{extra}
{('CIERRE DEL PUNTO ANTERIOR: ' + previo) if previo else ''}

REGLAS:
- 320-400 palabras exactas
- Español neutro-mexicano, tono de autoridad pero accesible
- Cada punto aporta VALOR: ejemplo cotidiano + explicación + aplicación práctica
- Incluye 1 estudio, autor o dato científico (real o plausible)
- SHOWING not telling: describe escenas concretas
- El dato contraintuitivo debe sonar natural, no forzado
- Sin listas, emojis, ni acotaciones
Devuelve SOLO el texto del punto."""
        texto = None
        for intento in range(3):
            t = llm(prompt, temperature=0.85, max_tokens=1000)
            t = limpiar_texto_narracion(t) if t else ""
            if len(t.split()) >= 280:
                texto = t
                break
            print(f"⚠️ Punto {i+1} corto ({len(t.split())} pal.)")
        if not texto:
            raise RuntimeError(f"No se pudo generar el punto {i+1}")
        textos.append(texto)
        print(f"   ✅ Punto {i+1}/{len(puntos)}: {len(texto.split())} palabras")
    return textos

def expandir_texto(titulo, texto_actual):
    prompt = (f'Video: "{titulo}". Final:\n"""\n{texto_actual[-500:]}\n"""\n'
              f"Añade 200-300 palabras profundizando el cierre. Devuelve SOLO el texto.")
    for _ in range(2):
        t = llm(prompt, temperature=0.8, max_tokens=900)
        t = limpiar_texto_narracion(t) if t else ""
        if len(t.split()) > 150:
            return t
    return ""

OUTROS = [
    "Y hasta aquí llega el video de hoy. Si te aportó, suscríbete y activa la campanita. "
    "Cuéntame en los comentarios: ¿cuál de estos puntos vas a aplicar primero?",
    "Eso fue todo por hoy. Si llegaste hasta el final, déjame un like y suscríbete para "
    "no perderte el siguiente. ¿Tú qué opinas? Te leo abajo.",
]

# =================================================================
# SEGMENTOS
# =================================================================
def dividir_en_segmentos(texto, max_palabras=SEG_MAX_PALABRAS):
    oraciones = [o.strip() for o in re.split(r"(?<=[.!?…])\s+", texto) if o.strip()]
    if not oraciones:
        return [texto]
    segs, actual, cuenta = [], [], 0
    for o in oraciones:
        n = len(o.split())
        if cuenta + n > max_palabras and actual:
            segs.append(" ".join(actual))
            actual, cuenta = [o], n
        else:
            actual.append(o)
            cuenta += n
    if actual:
        segs.append(" ".join(actual))
    if len(segs) > 1 and len(segs[-1].split()) < 12:
        segs[-2] += " " + segs.pop()
    return segs

def crear_segmentos(puntos_txt):
    segs = []
    for pi, txt in enumerate(puntos_txt):
        for k, p in enumerate(dividir_en_segmentos(txt)):
            segs.append({"punto": pi, "texto": p, "punto_ini": k == 0})
    n = len(segs)
    for i, s in enumerate(segs):
        p = i / max(n - 1, 1)
        s["etapa"] = ("gancho" if p < 0.12 else
                      "contexto" if p < 0.30 else
                      "desarrollo" if p < 0.85 else "conclusion")
    return segs

# =================================================================
# VOZ
# =================================================================
def duracion_audio(ruta):
    a = AudioFileClip(ruta)
    d = a.duration
    a.close()
    return d

def generar_audio(texto, nombre, etapa):
    limpio = re.sub(r'[{}[\]"]', " ", texto)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    if len(limpio) < 10:
        return None
    ruta = f"temp_audio_{nombre}.mp3"
    rate = RATE_ETAPA.get(etapa, "+4%")
    pitch = VOZ_CANAL["tono"]
    voces = [VOZ_CANAL["voz"]] + [v for v in VOCES_RESPALDO if v != VOZ_CANAL["voz"]]
    for voz in voces:
        for intento in range(2):
            async def _go():
                communicate = edge_tts.Communicate(limpio, voz, rate=rate, pitch=pitch)
                await communicate.save(ruta)
            try:
                asyncio.run(_go())
                if os.path.exists(ruta) and os.path.getsize(ruta) > 500:
                    return ruta
            except Exception as e:
                print(f"❌ TTS {voz}: {e}")
                time.sleep(2 * (intento + 1))
    return None

def sintetizar(segs):
    ok = []
    for i, s in enumerate(segs):
        ruta = generar_audio(s["texto"], s.get("id", i), s["etapa"])
        if not ruta:
            print(f"⚠️ Segmento {i} sin audio")
            continue
        s["audio"]     = ruta
        s["dur_audio"] = duracion_audio(ruta)
        ok.append(s)
        time.sleep(0.2)
    if len(ok) < len(segs) * 0.9:
        raise RuntimeError("Demasiados segmentos sin audio")
    return ok

def construir_timeline(segs):
    t = 0.0
    for s in segs:
        s["inicio"] = t
        s["dur"]    = s["dur_audio"] + PAUSA_ETAPA.get(s["etapa"], 0.5)
        t += s["dur"]
    return t

# =================================================================
# CLOUDFLARE FLUX
# =================================================================
ANTI_DEFORM = (", cinematic wide shot, professional lighting, highly detailed, "
               "photorealistic, 8k, no text, no deformed faces, no mutated hands, "
               "no extra limbs, sharp focus, professional composition")

def generar_imagen_cloudflare(prompt_en, idx, intentos=3):
    if not USAR_IMAGENES_IA:
        return None
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        print("⚠️ Sin credenciales Cloudflare")
        return None
    prompt_completo = prompt_en.strip() + ANTI_DEFORM
    url = (f"https://api.cloudflare.com/client/v4/accounts/"
           f"{CLOUDFLARE_ACCOUNT_ID}/ai/run/{CLOUDFLARE_MODEL}")
    headers = {"Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}"}
    payload = {"prompt": prompt_completo}
    for i in range(intentos):
        print(f"   🎨 Cloudflare intento {i+1}/{intentos}")
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            if r.status_code == 200:
                ruta = f"temp_img_{idx}.jpg"
                if r.headers.get("Content-Type", "").startswith("image"):
                    with open(ruta, "wb") as f:
                        f.write(r.content)
                else:
                    import base64
                    data = r.json()
                    if "result" in data and "image" in data["result"]:
                        with open(ruta, "wb") as f:
                            f.write(base64.b64decode(data["result"]["image"]))
                    else:
                        print(f"⚠️ Formato inesperado: {str(data)[:100]}")
                        continue
                if os.path.exists(ruta) and os.path.getsize(ruta) > 1000:
                    print(f"   ✅ Imagen Cloudflare generada")
                    return ruta
            else:
                print(f"   ⚠️ Cloudflare {r.status_code}: {r.text[:150]}")
        except Exception as e:
            print(f"   ❌ Error Cloudflare: {e}")
        time.sleep(3 * (i + 1))
    return None

def imagen_fallback(idx):
    img = Image.new("RGB", (W, H), (10, 15, 25))
    draw = ImageDraw.Draw(img)
    for y in range(H):
        color = (int(10 + 30 * y / H), int(15 + 20 * y / H), int(25 + 40 * y / H))
        draw.line([(0, y), (W, y)], fill=color)
    ruta = f"temp_img_{idx}.jpg"
    img.save(ruta, "JPEG", quality=85)
    return ruta

# =================================================================
# PLANIFICACIÓN VISUAL POR IA
# =================================================================
def planificar_visuales(segs, tema):
    out = [None] * len(segs)
    for ini in range(0, len(segs), 15):
        lote = segs[ini:ini + 15]
        listado = "\n".join(f"{j+1}. {s['texto'][:230]}" for j, s in enumerate(lote))
        prompt = f"""Eres director de fotografía de un canal de PSICOLOGÍA de élite (estilo
documental educativo, autoridad intelectual).

Para CADA fragmento numerado devuelve UNA consulta corta (4-6 palabras, EN INGLÉS)
para generar una imagen con Flux que ilustre visualmente ese fragmento.

REGLAS:
- Estilo: cinematográfico, profesional, oscuro-elegante, editorial
- Prefiere: siluetas, manos, entornos, objetos simbólicos, escenarios
- EVITA primeros planos de rostros (Flux los hace pero mejor evitarlos)
- Ejemplos: "cinematic brain scan blue light", "person walking alone silhouette", "hands writing journal dark", "two people arguing office"
- NUNCA incluyas: "text", "words", "letters", "caption"

Tema: {tema['tema']}
Fragmentos:\n{listado}

Responde SOLO JSON: {{"consultas": ["..."]}} con exactamente {len(lote)} elementos."""
        lista = []
        try:
            lista = parsear_json(llm(prompt, 0.4, 800, json_mode=True)).get("consultas", [])
        except Exception as e:
            print(f"⚠️ Planificación visual: {e}")
        for j, s in enumerate(lote):
            q = lista[j] if j < len(lista) and isinstance(lista[j], str) else ""
            q = " ".join(re.sub(r"[^a-zA-Z ]", " ", q).split()[:7])
            if len(q) < 10:
                q = "cinematic dark moody professional educational scene"
            out[ini + j] = q
    return out

# =================================================================
# RENDER
# =================================================================
_VIG = {}

def vignette(size, base=1.0, fuerza=0.55):
    k = (size, base)
    if k not in _VIG:
        w, h = size
        y, x = np.ogrid[-1:1:h * 1j, -1:1:w * 1j]
        d = np.clip(np.sqrt(x ** 2 + y ** 2) / 1.414, 0, 1)
        _VIG[k] = ((1 - fuerza * d ** 2.2) * base).astype(np.float32)[..., None]
    return _VIG[k]

def grade(img, etapa):
    img = ImageEnhance.Color(img).enhance(0.85)
    img = ImageEnhance.Contrast(img).enhance({"gancho": 1.20, "conclusion": 1.10}.get(etapa, 1.15))
    img = ImageEnhance.Brightness(img).enhance({"gancho": 0.90, "conclusion": 0.95}.get(etapa, 0.92))
    return Image.blend(img, Image.new("RGB", img.size, (12, 18, 32)), 0.08)

class RenderEscenas:
    def __init__(self, escenas, size, total):
        self.esc, self.size, self.total = escenas, size, total
        self.starts = [e["inicio"] for e in escenas]
        self._ikey = self._img = None
        self.vig_img = vignette(size, 1.0)

    def cerrar(self):
        pass

    def _base(self, e):
        key = (e["path"], e["etapa"])
        if self._ikey != key:
            sz = (int(self.size[0] * 1.2), int(self.size[1] * 1.2))
            im = ImageOps.fit(Image.open(e["path"]).convert("RGB"), sz, Image.LANCZOS)
            arr = np.asarray(grade(im, e["etapa"]), dtype=np.float32) * vignette(sz, 1.0)
            self._img, self._ikey = Image.fromarray(arr.astype(np.uint8)), key
        return self._img

    def _frame_img(self, e, lt):
        base = self._base(e)
        bw, bh = base.size
        p = min(max(lt / e["dur"], 0), 1) if e["dur"] > 0 else 0
        if not e["zin"]:
            p = 1 - p
        cw = bw / (1 + 0.08 * p)
        ch = cw * bh / bw
        mx, my = bw - cw, bh - ch
        x0 = min(max(mx / 2 + e["ax"] * mx / 2 * 0.8, 0), mx)
        y0 = min(max(my / 2 + e["ay"] * my / 2 * 0.8, 0), my)
        return np.asarray(base.resize(self.size, Image.BILINEAR,
                                      box=(x0, y0, x0 + cw, y0 + ch)))

    def frame(self, t):
        i = max(0, bisect.bisect_right(self.starts, t) - 1)
        e = self.esc[i]
        lt = t - e["inicio"]
        fr = self._frame_img(e, lt)
        f = 1.0
        if e.get("fade") and lt < 0.6:
            f = lt / 0.6
        if t > self.total - 1.5:
            f = min(f, max(0.0, (self.total - t) / 1.5))
        if f < 1.0:
            fr = (fr.astype(np.float32) * f).astype(np.uint8)
        return fr

def construir_escenas(segs):
    esc = []
    for s in segs:
        n_imgs = max(1, round(s["dur_audio"] / SEG_ESCENA))
        dur_por_img = s["dur"] / n_imgs
        for k in range(n_imgs):
            esc.append({
                "path": s["medios"][k % len(s["medios"])],
                "inicio": s["inicio"] + k * dur_por_img,
                "dur": dur_por_img,
                "etapa": s["etapa"],
                "fade": bool(k == 0 and s.get("punto_ini")),
                "zin": random.random() < 0.65,
                "ax": random.uniform(-1, 1),
                "ay": random.uniform(-1, 1),
            })
    return esc

def mezclar_audio(segs, total, fondo, extras=()):
    clips = [AudioFileClip(s["audio"]).set_start(s["inicio"]) for s in segs]
    clips += list(extras)
    narr = CompositeAudioClip(clips)
    capas = [narr]
    if fondo and os.path.exists(fondo):
        try:
            bg = AudioFileClip(fondo)
            if bg.duration < total:
                bg = concatenate_audioclips([bg] * (int(total / bg.duration) + 1))
            capas.append(bg.subclip(0, total).volumex(VOL_FONDO).audio_fadein(2).audio_fadeout(3))
        except Exception as e:
            print(f"⚠️ Fondo: {e}")
    return CompositeAudioClip(capas).set_duration(total), clips

def renderizar(escenas, total, audio, size, salida, sufijo=""):
    render = RenderEscenas(escenas, size, total)
    video = VideoClip(render.frame, duration=total).set_audio(audio)
    temp_audio = f"temp_audio_final{sufijo}.m4a"
    video.write_videofile(salida, fps=FPS, codec="libx264", audio_codec="aac",
                          audio_bitrate="192k", threads=4, preset="veryfast",
                          temp_audiofile=temp_audio,
                          ffmpeg_params=["-crf", "23", "-pix_fmt", "yuv420p",
                                         "-movflags", "+faststart"],
                          logger=None)
    render.cerrar()
    video.close()
    try:
        if os.path.exists(temp_audio):
            os.remove(temp_audio)
    except Exception:
        pass
    return salida

# =================================================================
# MINIATURA
# =================================================================
def obtener_fuente(size):
    os.makedirs("fonts", exist_ok=True)
    ruta = "fonts/Anton-Regular.ttf"
    if not os.path.exists(ruta):
        try:
            r = requests.get(FUENTE_URL, timeout=20)
            if r.status_code == 200 and len(r.content) > 20000:
                with open(ruta, "wb") as f:
                    f.write(r.content)
        except Exception:
            pass
    for p in [ruta, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def dividir_lineas(palabras):
    if len(palabras) <= 2:
        return palabras[:]
    mejor = None
    for i in range(1, len(palabras)):
        a, b = " ".join(palabras[:i]), " ".join(palabras[i:])
        m = max(len(a), len(b))
        if mejor is None or m < mejor[0]:
            mejor = (m, [a, b])
    return mejor[1]

def crear_miniatura(img_path, texto, salida):
    TW, TH = 1280, 720
    try:
        img = Image.open(img_path).convert("RGB") if img_path else Image.new("RGB", (TW, TH), (10, 10, 20))
        img = ImageOps.fit(img, (TW, TH), Image.LANCZOS)
        img = ImageEnhance.Contrast(img).enhance(1.45)
        img = ImageEnhance.Color(img).enhance(1.35)
        img = ImageEnhance.Sharpness(img).enhance(2.0)
        img = ImageEnhance.Brightness(img).enhance(0.90)

        grad = Image.new("L", (TW, TH), 0)
        gd = ImageDraw.Draw(grad)
        for x in range(TW):
            gd.line([(x, 0), (x, TH)], fill=int(240 * max(0, 1 - x / (TW * 0.65)) ** 1.6))
        img = Image.composite(Image.new("RGB", (TW, TH), (0, 0, 0)), img, grad)
        arr = np.asarray(img, dtype=np.float32) * vignette((TW, TH), 1.0, 0.55)
        img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")

        lineas = dividir_lineas(texto.upper().split()[:4])
        max_w, max_h = int(TW * 0.58), int(TH * 0.78)

        for size in range(150, 60, -6):
            font = obtener_fuente(size)
            cajas = [font.getbbox(l) for l in lineas]
            alto = sum(b[3] - b[1] for b in cajas) + 18 * (len(lineas) - 1)
            if max(b[2] - b[0] for b in cajas) <= max_w and alto <= max_h:
                break

        acento = random.choice([(255, 220, 0), (255, 50, 50), (255, 140, 0), (255, 255, 255)])
        y = (TH - alto) // 2 + 10
        pos = []
        for l, b in zip(lineas, cajas):
            pos.append((l, 60, y - b[1]))
            y += (b[3] - b[1]) + 18

        glow = Image.new("RGBA", (TW, TH), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        for l, x, yy in pos:
            gdraw.text((x, yy), l, font=font, fill=acento + (255,),
                       stroke_width=10, stroke_fill=acento + (255,))
        img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(24)))

        draw = ImageDraw.Draw(img)
        borde = max(7, size // 20)
        for i, (l, x, yy) in enumerate(pos):
            color = acento if (i == len(pos) - 1) else (255, 255, 255)
            draw.text((x, yy), l, font=font, fill=color + (255,),
                      stroke_width=borde, stroke_fill=(0, 0, 0, 255))

        rgb = img.convert("RGB")
        for q in (92, 87, 82, 76, 70):
            rgb.save(salida, "JPEG", quality=q, optimize=True)
            if os.path.getsize(salida) < 1_900_000:
                break
        print(f"✅ Miniatura: '{' / '.join(lineas)}' ({size}px)")
        return True
    except Exception as e:
        print(f"❌ Error miniatura: {e}")
        return False

# =================================================================
# SEO ELITE
# =================================================================
def _ascii_tag_yt(t):
    nfd = unicodedata.normalize('NFD', str(t))
    sin_acentos = ''.join(c for c in nfd if unicodedata.category(c) != 'Mn')
    limpio = re.sub(r'[^a-z0-9 ]', '', sin_acentos.lower())
    return re.sub(r'\s+', ' ', limpio).strip()

def construir_tags(plan, tema, sugerencias):
    """Mix elite vidIQ: exactos + broad + long-tail + preguntas."""
    nombre_tema = _ascii_tag_yt(tema["tema"].replace("_", " "))

    tags_ia = plan.get("tags", [])
    if isinstance(tags_ia, str):
        tags_ia = [x.strip() for x in tags_ia.split(",")]

    # Estructura por capas (SEO estratégico)
    exactos = list(tags_ia)[:5]                          # 5 específicos IA
    broad = ["psicologia", "estoicismo", "desarrollo personal",
             "inteligencia emocional", "mentalidad"]      # 5 broad del canal
    long_tail = [
        f"psicologia {nombre_tema}",
        f"estoicismo {nombre_tema}",
        f"como {nombre_tema}",
        f"que es {nombre_tema}",
    ]
    preguntas = list(sugerencias)[:3]
    especificos_tema = list(tema["keywords"])[:3]

    todos, vistos = [], set()
    for raw in exactos + broad + long_tail + preguntas + especificos_tema:
        tag = _ascii_tag_yt(raw)
        if not tag or len(tag) < 2 or len(tag) > 40 or tag in vistos:
            continue
        if any(x in tag for x in ("100 real", "veridico", "caso real")):
            continue
        vistos.add(tag)
        todos.append(tag)

    resultado, total_chars = [], 0
    for tag in todos:
        costo = len(tag) + 1
        if total_chars + costo > 460 or len(resultado) >= 20:
            break
        resultado.append(tag)
        total_chars += costo
    print(f"🏷️  Tags ({len(resultado)}): {', '.join(resultado[:6])}...")
    return resultado

def construir_hashtags(tema, plan):
    """SEO elite: 4-5 hashtags relevantes (no spam). Los 3 primeros son críticos."""
    base = ["#Psicologia", "#DesarrolloPersonal"]
    tema_hs = tema.get("hashtags", [])[:2]
    extra = "#Estoicismo"
    if "estoic" in tema["tema"].lower() or "estoic" in " ".join(plan.get("palabras_clave", [])).lower():
        extra = "#MarcoAurelio"
    hs = base + tema_hs + [extra]
    vistos = []
    for h in hs:
        if h not in vistos:
            vistos.append(h)
    return " ".join(vistos[:5])

def construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags):
    """
    Descripción SEO elite:
    - Línea 1: keyword principal + promesa (aparece en búsqueda, crítico)
    - Línea 2: hook secundario
    - Capítulos, sinopsis, CTA, redes, hashtags
    """
    kws = plan.get("palabras_clave", [])
    keyword_principal = kws[0] if kws else tema["tema"].replace("_", " ")
    dato_c = plan.get("dato_contraintuitivo", "")
    resumen = plan.get("resumen", "")

    # ⚡ Línea 1 SEO: keyword + promesa (primeros 150 chars críticos)
    linea1 = f"{keyword_principal.title()}: {dato_c}." if dato_c else f"{keyword_principal.title()}: {resumen[:120]}"
    # ⚡ Línea 2: promesa específica
    linea2 = f"En este video te explico {plan.get('gancho', '')[:180]}"

    capitulos = "\n".join(f"{ts} {t}" for ts, t in caps_ts)
    rel = ", ".join(sugerencias[:5])

    partes = [
        f"🎯 {linea1}",
        linea2,
        f"",
        f"🔔 SUSCRÍBETE para un video nuevo cada día: {CANAL_LINK}?sub_confirmation=1",
        f"",
        f"⏰ CAPÍTULOS\n{capitulos}",
        f"",
        f"📖 SOBRE ESTE VIDEO\n{resumen}",
        f"",
        (f"🔎 BÚSQUEDAS RELACIONADAS: {rel}" if rel else ""),
        f"",
        f"📱 Sígueme en Facebook: https://www.facebook.com/profile.php?id=61593237382982",
        f"",
        f"📚 Otros videos que te pueden interesar:",
        f"• Cómo recuperar tu dopamina → {CANAL_LINK}/videos",
        f"• Estoicismo aplicado → {CANAL_LINK}/videos",
    ]

    if ACTIVAR_DISCLOSURE_IA:
        partes.append(DISCLOSURE_TEXT.strip())

    partes.append("")
    partes.append(hashtags)

    desc = "\n".join(p for p in partes if p is not None)
    return desc[:4900]

def generar_srt(segs, ruta):
    def ts(x):
        h, m, s = int(x // 3600), int(x % 3600 // 60), x % 60
        return f"{h:02d}:{m:02d}:{int(s):02d},{int((s - int(s)) * 1000):03d}"
    lineas, n = [], 1
    for s in segs:
        pal = s["texto"].split()
        if not pal:
            continue
        t = s["inicio"]
        for i in range(0, len(pal), 9):
            tr = pal[i:i + 9]
            d = s["dur_audio"] * len(tr) / len(pal)
            lineas.append(f"{n}\n{ts(t)} --> {ts(t + d)}\n{' '.join(tr)}\n")
            n, t = n + 1, t + d
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))
    return ruta

# =================================================================
# PUBLICACIÓN
# =================================================================
def deberia_publicar(estado):
    ult = estado.get("ultima_publicacion")
    if not ult:
        return True
    try:
        dt = datetime.fromisoformat(ult)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        horas = (datetime.now(TZ) - dt).total_seconds() / 3600
        if horas < INTERVALO_MIN_HORAS:
            print(f"⏸️ Han pasado {horas:.1f}h (mínimo {INTERVALO_MIN_HORAS}h).")
            return False
    except ValueError:
        pass
    return True

def proximo_slot_batch():
    """
    ⚡ v2.1: Garantiza que los 3 slots caigan el MISMO DÍA.
    Antes cada slot se calculaba independiente → bug de días cruzados.
    """
    ahora = datetime.now(TZ)
    slot_mas_temprano_hoy = (
        ahora.replace(hour=HORA_LARGO, minute=0, second=0, microsecond=0)
        - timedelta(minutes=VARIACION_MINUTOS_LARGO)
    )
    if slot_mas_temprano_hoy - ahora < timedelta(minutes=10):
        dia_base = (ahora + timedelta(days=1)).date()
    else:
        dia_base = ahora.date()

    dia_dt = datetime.combine(dia_base, datetime.min.time()).replace(tzinfo=TZ)

    def slot(hora, variacion, offset=0):
        s = dia_dt.replace(hour=hora, minute=0)
        s += timedelta(minutes=random.randint(-variacion, variacion) + offset)
        return s

    slot_largo  = slot(HORA_LARGO, VARIACION_MINUTOS_LARGO)
    slot_short1 = slot(HORA_SHORT_1, VARIACION_MINUTOS_SHORT_1, offset=15)
    slot_short2 = slot(HORA_SHORT_2, VARIACION_MINUTOS_SHORT_2, offset=15)
    return slot_largo, slot_short1, slot_short2

def utc_iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

def subir_video(youtube, ruta, titulo, descripcion, tags, publish_at=None):
    status = {"privacyStatus": "public", "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": True}
    if publish_at:
        status.update({"privacyStatus": "private", "publishAt": publish_at})
    body = {"snippet": {"title": titulo[:100], "description": descripcion[:5000],
                        "tags": tags, "categoryId": "27", "defaultLanguage": "es",
                        "defaultAudioLanguage": "es"},
            "status": status}
    media = MediaFileUpload(ruta, chunksize=8 * 1024 * 1024, resumable=True,
                            mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp, reintentos = None, 0
    while resp is None:
        try:
            st, resp = req.next_chunk()
            if st:
                print(f"   ⬆️ {int(st.progress() * 100)}%")
        except (HttpError, ssl.SSLEOFError, ConnectionError, socket.timeout, OSError) as e:
            es_reintento = (isinstance(e, HttpError) and e.resp.status in (429, 500, 502, 503, 504))
            es_reintento = es_reintento or isinstance(e, (ssl.SSLEOFError, ConnectionError, socket.timeout, OSError))
            if es_reintento and reintentos < 8:
                reintentos += 1
                espera = 2 ** reintentos
                print(f"⚠️ Reintento {reintentos}/8 en {espera}s...")
                time.sleep(espera)
                continue
            print(f"❌ Error fatal subida: {type(e).__name__}: {e}")
            raise
    print(f"✅ Video subido: https://youtu.be/{resp['id']}" +
          (f" (programado {publish_at})" if publish_at else ""))
    return resp["id"]

def extras_post_subida(youtube, vid, miniatura, srt, comentario):
    if miniatura and os.path.exists(miniatura):
        try:
            youtube.thumbnails().set(
                videoId=vid,
                media_body=MediaFileUpload(miniatura, mimetype="image/jpeg")
            ).execute()
            print("✅ Miniatura subida")
        except Exception as e:
            print(f"⚠️ Miniatura: {e}")
    if srt and os.path.exists(srt):
        try:
            youtube.captions().insert(
                part="snippet",
                body={"snippet": {"videoId": vid, "language": "es",
                                  "name": "Español", "isDraft": False}},
                media_body=MediaFileUpload(srt, mimetype="application/octet-stream")
            ).execute()
            print("✅ Subtítulos subidos")
        except Exception as e:
            print(f"⚠️ Subtítulos: {e}")
    if PLAYLIST_ID:
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={"snippet": {"playlistId": PLAYLIST_ID,
                                  "resourceId": {"kind": "youtube#video", "videoId": vid}}}
            ).execute()
            print("✅ Añadido a playlist")
        except Exception as e:
            print(f"⚠️ Playlist: {e}")
    if comentario:
        try:
            youtube.commentThreads().insert(
                part="snippet",
                body={"snippet": {"videoId": vid,
                                  "topLevelComment": {"snippet": {"textOriginal": comentario}}}}
            ).execute()
            print("✅ Comentario publicado")
        except Exception as e:
            print(f"⚠️ Comentario: {e}\n   Para fijar: {comentario}")

# =================================================================
# SHORTS
# =================================================================
def crear_short(segs_orig, fondo, indice, salida="short_final.mp4", modo="gancho"):
    """
    ⚡ v2.1: contenido 28-36s + CTA = 35-42s total (sweet spot vidIQ).
    """
    segs = [{**s} for s in segs_orig]
    if modo == "gancho":
        candidatos = segs[:8]
    else:
        total_segs = len(segs)
        inicio = max(0, total_segs // 2 - 4)
        candidatos = segs[inicio:inicio + 8]

    sel, t = [], 0.0
    for s in candidatos:
        if sel and t + s["dur"] > SHORT_CONTENT_MAX:
            break
        sel.append(s)
        t += s["dur"]
        if t >= SHORT_CONTENT_MIN:
            break
    if not sel:
        return None
    print(f"   📱 Short {indice} contenido: {t:.1f}s (+ CTA ≈ {t+6:.1f}s total)")

    t0 = 0.0
    for s in sel:
        s["inicio"] = t0
        t0 += s["dur"]
    t = t0

    cta_texto = random.choice(CTA_SHORTS)
    cta = generar_audio(cta_texto, f"cta_{indice}", "conclusion")
    escenas = construir_escenas(sel)
    extras, total = [], t
    if cta:
        d = duracion_audio(cta)
        extras.append(AudioFileClip(cta).set_start(t))
        ult = escenas[-1]
        escenas.append({**ult, "inicio": t, "dur": d + 0.6, "fade": False})
        total = t + d + 0.6
    audio, _ = mezclar_audio(sel, total, fondo, extras)
    renderizar(escenas, total, audio, (1080, 1920), salida, sufijo=f"_s{indice}")
    return salida

# =================================================================
# MÚSICA
# =================================================================
def buscar_archivo(nombre):
    for root, _, files in os.walk("."):
        if "/." in root or "\\." in root:
            continue
        if nombre in files:
            return os.path.join(root, nombre)
    return None

def seleccionar_fondo(estado):
    ultimos = estado["ultimos_fondos"]
    disp = [f for f in FONDOS_DISPONIBLES if f not in ultimos[-3:]] or FONDOS_DISPONIBLES[:]
    random.shuffle(disp)
    for f in disp + FONDOS_DISPONIBLES:
        ruta = buscar_archivo(f)
        if ruta:
            estado["ultimos_fondos"] = (ultimos + [f])[-10:]
            print(f"🎵 Fondo: {ruta}")
            return ruta
    print("⚠️ Sin música de fondo")
    return None

# =================================================================
# VALIDACIONES
# =================================================================
def limpiar_temporales():
    for f in os.listdir("."):
        if f.startswith("temp_") or f in ("video_final.mp4", "short_1.mp4",
                                          "short_2.mp4", "short_final.mp4",
                                          "miniatura.jpg", "subtitulos.srt"):
            try:
                os.remove(f)
            except OSError:
                pass

def verificar_envs():
    faltan = [v for v in ("DEEPSEEK_API_KEY", "CLOUDFLARE_ACCOUNT_ID",
                          "CLOUDFLARE_API_TOKEN", "YOUTUBE_USER_TOKEN")
              if not os.getenv(v)]
    if faltan:
        print(f"❌ Faltan variables: {', '.join(faltan)}")
        sys.exit(1)
    yt = crear_cliente_youtube()
    if yt is None:
        print("❌ YOUTUBE_USER_TOKEN inválido/expirado")
        sys.exit(1)
    try:
        yt.channels().list(part="id", mine=True).execute()
        print("✅ Credenciales válidas.")
    except HttpError as e:
        err_str = str(e)
        if "insufficientPermissions" in err_str:
            print("⚠️ Token sin permiso de lectura. El bot publica igual.")
        elif "401" in err_str or "invalid_grant" in err_str:
            print(f"❌ YouTube token expirado: {e}")
            sys.exit(1)
        else:
            print(f"❌ Error YouTube: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ YouTube token inválido: {e}")
        sys.exit(1)
    return yt

# =================================================================
# MAIN
# =================================================================
def main():
    youtube = verificar_envs()
    limpiar_temporales()
    estado = cargar_estado()

    if os.getenv("FORCE_PUBLISH") == "true":
        print("⚡ FORCE_PUBLISH activo")
    elif not deberia_publicar(estado):
        sys.exit(0)

    print("=" * 70)
    print("🧠 CÓDIGO MENTAL - BOT v2.1 ELITE MASTER PREMIUM")
    print(f"📅 {datetime.now(TZ):%Y-%m-%d %H:%M} | 🎤 {VOZ_CANAL['voz']}")
    print(f"📤 1 Video Largo (8-12 min) + 2 Shorts (35-42s) | 🎨 Flux SEG_ESCENA={SEG_ESCENA}s")
    print("=" * 70)

    actualizar_rendimiento(youtube, estado)
    tema = elegir_tema(estado, youtube)
    contexto = random.choice(tema["contextos"])
    formato = random.choice(FORMATOS_NARRACION)
    perfil = random.choice(PERFILES_NARRADOR)
    print(f"🎭 Formato: {formato['nombre']} | Narrador: {perfil}")

    sugerencias = list(dict.fromkeys(
        sugerencias_youtube(tema["seed"]) +
        sugerencias_youtube("psicología " + tema["keywords"][0])
    ))[:10]

    fondo = seleccionar_fondo(estado)
    titulos_previos = cargar_json(TITULOS_FILE, {"titulos": []})["titulos"][-20:]

    plan = titulo = None
    for intento in range(4):
        try:
            plan = generar_plan(tema, contexto, sugerencias, titulos_previos, formato, perfil)
            if plan.get("palabras_clave") and tema_ya_usado(" ".join(map(str, plan["palabras_clave"]))):
                raise ValueError("tema repetido")
            titulo = elegir_titulo(plan["titulos"], plan.get("dato_contraintuitivo", ""))
            if not titulo:
                raise ValueError("sin título válido")
            plan["_formato_instruccion"] = formato["instruccion"]
            plan["_perfil_narrador"]     = perfil
            plan["_nombre_formato"]      = formato["nombre"]
            break
        except Exception as e:
            print(f"⚠️ Plan intento {intento+1}/4: {e}")
            plan = None
            time.sleep(5)
    if not plan:
        print("❌ No se pudo generar plan válido.")
        sys.exit(1)

    print(f"📌 Título: {titulo}")
    print(f"🎯 Dato contraintuitivo: {plan.get('dato_contraintuitivo', 'N/A')}")

    puntos_txt = generar_puntos(plan, tema, contexto)
    n_puntos = len(puntos_txt)
    segs = crear_segmentos(puntos_txt)
    print(f"🧩 {len(segs)} segmentos, {sum(len(p.split()) for p in puntos_txt)} palabras")

    segs = sintetizar(segs)
    total = construir_timeline(segs)

    intentos = 0
    while total < DURACION_MINIMA_SEGUNDOS and intentos < MAX_INTENTOS_EXPANSION:
        print(f"⚠️ {total/60:.1f} min < mínimo. Expandiendo ({intentos+1})...")
        extra = expandir_texto(titulo, " ".join(s["texto"] for s in segs))
        intentos += 1
        if not extra:
            break
        nuevos = [{"punto": n_puntos - 1, "texto": p, "punto_ini": False,
                   "etapa": "conclusion", "id": f"x{intentos}_{k}", "expansion": True}
                  for k, p in enumerate(dividir_en_segmentos(extra))]
        segs += sintetizar(nuevos)
        total = construir_timeline(segs)

    if total > DURACION_MAXIMA_SEGUNDOS:
        print(f"⚠️ {total/60:.1f} min > máximo. Recortando...")
        while total > DURACION_MAXIMA_SEGUNDOS:
            idx = next((i for i in range(len(segs) - 1, -1, -1) if segs[i].get("expansion")), None)
            if idx is None:
                break
            segs.pop(idx)
            total = construir_timeline(segs)

    if total < DURACION_MINIMA_SEGUNDOS:
        print("❌ Duración insuficiente. Abortando.")
        sys.exit(1)

    outro = [{"punto": n_puntos - 1, "texto": random.choice(OUTROS), "punto_ini": False,
              "etapa": "conclusion", "id": "outro", "outro": True}]
    segs += sintetizar(outro)
    total = construir_timeline(segs)
    print(f"⏱️ Duración final: {total/60:.1f} min")

    print("🎨 Planificando visuales con IA...")
    prompts_visuales = planificar_visuales(segs, tema)

    for i, s in enumerate(segs):
        n_imgs = max(1, round(s["dur_audio"] / SEG_ESCENA))
        prompt_visual = prompts_visuales[i] if i < len(prompts_visuales) else "cinematic dark moody professional scene"
        print(f"🖼️ {i+1}/{len(segs)} [{s['etapa']}] '{prompt_visual}' x{n_imgs}")
        medios = []
        for k in range(n_imgs):
            ruta = generar_imagen_cloudflare(prompt_visual, f"{i}_{k}")
            if not ruta:
                ruta = imagen_fallback(f"{i}_{k}")
            medios.append(ruta)
        s["medios"] = medios

    caps_ts = []
    for p in range(n_puntos):
        primero = next((s for s in segs if s["punto"] == p), None)
        nombre = (str(plan["puntos"][p].get("titulo", f"Punto {p+1}"))[:50]
                  if p < len(plan["puntos"]) else f"Punto {p+1}")
        if primero:
            caps_ts.append((fmt_ts(primero["inicio"]), nombre))
    if caps_ts:
        caps_ts[0] = ("00:00", caps_ts[0][1])

    hashtags = construir_hashtags(tema, plan)
    descripcion = construir_descripcion(plan, tema, caps_ts, sugerencias, hashtags)
    tags = construir_tags(plan, tema, sugerencias)
    srt = generar_srt(segs, "subtitulos.srt")

    print(f"📝 Descripción (primeras 2 líneas):")
    print("   " + "\n   ".join(descripcion.split("\n")[:2]))

    portada = elegir_texto_portada(plan.get("palabras_portada"), titulo)
    escena_mini = str(plan.get("miniatura_escena", "professional psychology cinematic dark"))
    base_mini = generar_imagen_cloudflare(escena_mini + " for thumbnail", "thumb")
    if not base_mini:
        base_mini = imagen_fallback("thumb")
    miniatura = "miniatura.jpg" if crear_miniatura(base_mini, portada, "miniatura.jpg") else None

    escenas = construir_escenas(segs)
    audio, _ = mezclar_audio(segs, total, fondo)
    print("🎬 Renderizando video largo...")
    renderizar(escenas, total, audio, (W, H), "video_final.mp4", sufijo="_largo")

    if PROGRAMAR_PICO:
        slot_largo, slot_short1, slot_short2 = proximo_slot_batch()
        print(f"🕖 Video Largo: {slot_largo:%Y-%m-%d %H:%M} CDMX")
        print(f"📱 Short 1:    {slot_short1:%Y-%m-%d %H:%M} CDMX")
        print(f"📱 Short 2:    {slot_short2:%Y-%m-%d %H:%M} CDMX")
        dias = {slot_largo.date(), slot_short1.date(), slot_short2.date()}
        if len(dias) != 1:
            print(f"⚠️ ADVERTENCIA: slots en días distintos: {dias}")
        else:
            print(f"✅ Los 3 slots están el mismo día: {slot_largo.date()}")
    else:
        slot_largo = slot_short1 = slot_short2 = None
        print("📤 Publicación inmediata")

    vid = subir_video(youtube, "video_final.mp4", titulo, descripcion, tags,
                      utc_iso(slot_largo) if slot_largo else None)
    comentario = str(plan.get("pregunta_comentario") or "¿Qué opinas? Te leo 👇")
    extras_post_subida(youtube, vid, miniatura, srt, comentario)

    # ============ SHORTS ============
    if GENERAR_SHORT:
        shorts_creados = []

        try:
            print("🎞️ Creando Short Versión 1 (Gancho)...")
            s1 = crear_short(segs, fondo, 1, "short_1.mp4", modo="gancho")
            if not s1 or not os.path.exists(s1):
                raise RuntimeError("crear_short devolvió None o archivo inexistente")
            print(f"   ✅ Short 1 renderizado: {os.path.getsize(s1) // 1024} KB")

            titulo_base = str(plan.get("titulo_short") or titulo)[:88]
            t_short1 = titulo_base + " #Shorts"
            kws = plan.get("palabras_clave", [])
            kw_tag = "#" + _ascii_tag_yt(kws[0]).replace(" ", "") if kws else "#Psicologia"
            d_short1 = (f"{kws[0].title() if kws else 'Psicología'}: {titulo_base[:60]}\n\n"
                        f"📺 Video completo 👉 https://youtu.be/{vid}\n\n"
                        f"🔔 Suscríbete: {CANAL_LINK}?sub_confirmation=1\n\n"
                        f"#Shorts {kw_tag} {hashtags}" +
                        (DISCLOSURE_TEXT if ACTIVAR_DISCLOSURE_IA else ""))
            vid_s1 = subir_video(youtube, "short_1.mp4", t_short1, d_short1,
                                 tags[:15] + ["shorts"],
                                 utc_iso(slot_short1) if slot_short1 else None)
            if not vid_s1:
                raise RuntimeError("subir_video no devolvió ID")
            print(f"✅ Short 1 subido: https://youtu.be/{vid_s1}")
            shorts_creados.append(("Short 1", vid_s1))
        except Exception as e:
            print(f"❌ Short 1 FALLÓ: {type(e).__name__}: {e}")
            traceback.print_exc()

        gc.collect()
        time.sleep(3)

        try:
            print("🎞️ Creando Short Versión 2 (Clímax)...")
            s2 = crear_short(segs, fondo, 2, "short_2.mp4", modo="climax")
            if not s2 or not os.path.exists(s2):
                raise RuntimeError("crear_short devolvió None o archivo inexistente")
            print(f"   ✅ Short 2 renderizado: {os.path.getsize(s2) // 1024} KB")

            t_short2 = str(plan.get("titulo_short") or titulo)[:80] + " 🤯 #Shorts"
            d_short2 = (f"{kws[0].title() if kws else 'Psicología'}: {str(plan.get('titulo_short') or titulo)[:60]}\n\n"
                        f"📺 Video completo 👉 https://youtu.be/{vid}\n\n"
                        f"🔔 Suscríbete: {CANAL_LINK}?sub_confirmation=1\n\n"
                        f"#Shorts {kw_tag} {hashtags}" +
                        (DISCLOSURE_TEXT if ACTIVAR_DISCLOSURE_IA else ""))
            vid_s2 = subir_video(youtube, "short_2.mp4", t_short2, d_short2,
                                 tags[:15] + ["shorts"],
                                 utc_iso(slot_short2) if slot_short2 else None)
            if not vid_s2:
                raise RuntimeError("subir_video no devolvió ID")
            print(f"✅ Short 2 subido: https://youtu.be/{vid_s2}")
            shorts_creados.append(("Short 2", vid_s2))
        except Exception as e:
            print(f"❌ Short 2 FALLÓ: {type(e).__name__}: {e}")
            traceback.print_exc()

        print("=" * 70)
        print(f"📊 RESUMEN SHORTS: {len(shorts_creados)}/2 creados")
        for nombre, sid in shorts_creados:
            print(f"   ✅ {nombre}: https://youtu.be/{sid}")
        if len(shorts_creados) < 2:
            print(f"   ⚠️ Faltan {2 - len(shorts_creados)} short(s). Revisa el log arriba.")
        print("=" * 70)

    ahora = datetime.now(TZ).isoformat()
    guardar_titulo(titulo)
    guardar_tema(tema["tema"])
    estado["videos"].append({
        "id": vid, "titulo": titulo, "tema": tema["tema"],
        "formato": formato["nombre"], "perfil": perfil,
        "dato_contraintuitivo": plan.get("dato_contraintuitivo"),
        "duracion_min": round(total / 60, 1),
        "fecha": ahora,
    })
    estado["videos"] = estado["videos"][-60:]
    estado["temas_recientes"] = (estado["temas_recientes"] + [tema["tema"]])[-6:]
    estado["ultima_publicacion"] = ahora
    guardar_json(ESTADO_FILE, estado)

    limpiar_temporales()
    print("🎉 Proceso completado: 1 video largo + 2 shorts programados.")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        traceback.print_exc()
        sys.exit(1)
