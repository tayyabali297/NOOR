# ============================================================
#  N.O.O.R  v1.0 — Personal AI Assistant
#  Tayyab | Dublin | Windows 11 | Python 3.11
# ============================================================

import os, json, asyncio, tempfile, subprocess, webbrowser
import time, threading, math, base64, io, re, smtplib
import calendar as cal_lib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import sounddevice as sd
import numpy as np
import requests
import edge_tts
import pygame
import feedparser
import pyperclip
import pyautogui
from PIL import Image
import speech_recognition as sr
import psutil

# Google API (Calendar + Gmail) — optional, graceful fallback if not configured
try:
    from googleapiclient.discovery import build as _gbuild
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request as GRequest
    from google.oauth2.credentials import Credentials as GCredentials
    _GOOGLE_LIBS = True
except ImportError:
    _GOOGLE_LIBS = False

import config

# ── Theme ────────────────────────────────────────────────────────
BG     = "#080c14"
CARD   = "#0d1520"
CARD2  = "#101c2c"
BORDER = "#1a3050"
TEXT   = "#c0d0e0"
DIM    = "#2a4060"
WHITE  = "#e8f0f8"
CYAN   = "#1a9aaa"
GREEN  = "#1a8a55"
AMBER  = "#a07820"
ACCENT = "#0d8aaa"
FONT   = "Consolas"

STA_COL = {
    "STANDBY":    "#2a4060",
    "LISTENING":  "#1a8a55",
    "PROCESSING": "#a07820",
    "SPEAKING":   "#1a9aaa",
}

# ── API / Audio ──────────────────────────────────────────────────
CLAUDE_URL   = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
VOICE        = "en-GB-SoniaNeural"
VOICE_RATE   = "+4%"
VOICE_PITCH  = "-4Hz"
SPOTIFY_EXE  = r"C:\Users\tayya\AppData\Local\Microsoft\WindowsApps\Spotify.exe"
COMMAND_SECS = 7
SAMPLE_RATE  = 16000

# ── Wake / exit words ────────────────────────────────────────────
WAKE_WORDS = [
    # NOOR — primary + STT mis-transcription variants
    "hey noor", "noor", "okay noor", "wake up noor",
    "hey nor", "nor ", " nor", "hey no ", "hey new",
    "hey nu", "a noor", "a nor",
    # Fallback trigger phrases
    "let's get to work", "lets get to work", "get to work",
    "let's go", "lets go",
]
EXIT_WORDS = {
    "thanks", "bye", "stop", "that's all", "goodbye",
    "nevermind", "that will be all", "dismiss",
}
MAX_TURNS = 5

# ── Paths ────────────────────────────────────────────────────────
BASE      = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE, "data")
NOTES_F    = os.path.join(DATA_DIR, "notes.txt")
HEALTH_F   = os.path.join(DATA_DIR, "health.json")
TASKS_F    = os.path.join(DATA_DIR, "tasks.json")
WORKOUT_F  = os.path.join(DATA_DIR, "workout.json")
CALORIES_F = os.path.join(DATA_DIR, "calories.json")
KNOW_F    = os.path.join(BASE, "noor_knowledge.md")
GCREDS_F  = os.path.join(BASE, "google_credentials.json")
GTOKEN_F  = os.path.join(BASE, "google_token.json")
os.makedirs(DATA_DIR, exist_ok=True)

DAYS     = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DAY_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

GSCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# ── Knowledge / system prompt ────────────────────────────────────
_knowledge = ""
if os.path.exists(KNOW_F):
    with open(KNOW_F, encoding="utf-8") as f:
        _knowledge = f.read()

SYSTEM_PROMPT = f"""You are N.O.O.R, Tayyab's personal AI assistant.
CRITICAL RULE: Reply in 1 sentence maximum. No lists, no markdown, no elaboration.
Occasionally say "sir". Never suggest alcohol.

You have the following capabilities built in — use them when relevant:
- Weather for any city
- News from Ireland, world, tech, business, science (summarised)
- Morning briefing (date, weather, news, today's calendar events, email brief)
- Google Calendar: read today's/upcoming events, add new events
- Gmail: read email brief for today/yesterday, send emails
- Spotify: play, pause, skip, search, now playing
- GitHub: repos, open issues
- Tasks: add, complete, delete (shown in GUI)
- Notes: save and read back
- Health: log meals with macro estimation, log workouts, daily summary
- Word documents: create and open
- Screen reading: take screenshot and analyse with AI — great for coding help
- Computer control: type text, press keyboard shortcuts, open files and apps
- System: set volume, lock screen, set reminders, CPU/RAM/disk stats
- Maps and directions
- Web search: search the web and give a verbal answer, or open browser
- Look up any topic: uses live web data + own knowledge to answer
- Answer any question, help with thinking, planning, analysis

Personal context:
{_knowledge}

CRITICAL: You are the conversational fallback ONLY. All tools (email, calendar, screen reading,
file operations, apps, Spotify, system control) are handled by the router BEFORE you are called.
If the user asks you to do something you cannot do as a language model (open apps, send emails,
take screenshots, control the computer), do NOT pretend to do it or describe doing it.
Instead say: "Try saying: [the correct voice command]" and give them the right phrasing."""

# ── STT ──────────────────────────────────────────────────────────
stt = sr.Recognizer()
stt.energy_threshold         = 200
stt.dynamic_energy_threshold = True
stt.pause_threshold          = 1.4   # wait 1.4s of silence before cutting off

# ── Global state ─────────────────────────────────────────────────
history      = []
_app         = None
_busy        = False
is_speaking  = False
_mic_stream  = None
_pending_act      = None   # (fn, description) pending confirmation
_current_vol      = 50     # track volume for up/down commands
_interrupt_speech = False  # set True to stop TTS mid-sentence
_force_stop       = False  # set True to kill current _handle session

# ── WebSocket server (NOOR UI bridge) ────────────────────────────
try:
    import websockets as _websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False

_ws_clients: set = set()
_ws_loop = None
_ws_state = {
    "state": "STANDBY", "said": "", "response": "",
    "tasks": [], "stats": {}, "events": {}, "nutrition": {},
}

def ws_broadcast(msg: dict):
    """Thread-safe broadcast to all connected NOOR UI clients."""
    if not _WS_OK or not _ws_loop:
        return
    data = json.dumps(msg, ensure_ascii=False)
    async def _push():
        for client in list(_ws_clients):
            try:
                await client.send(data)
            except Exception:
                _ws_clients.discard(client)
    try:
        asyncio.run_coroutine_threadsafe(_push(), _ws_loop)
    except Exception:
        pass

def _ws_push_tasks():
    tasks = load_tasks() if os.path.exists(TASKS_F) else []
    _ws_state["tasks"] = tasks
    ws_broadcast({"type": "tasks", "tasks": tasks})

def _ws_push_nutrition():
    try:
        data  = _load_calories()
        today = datetime.now().date().isoformat()
        kcal  = data.get(today, 0)
    except Exception:
        kcal = 0
    n = {"calories": kcal, "protein": 0, "carbs": 0, "fat": 0}
    _ws_state["nutrition"] = n
    ws_broadcast({"type": "nutrition", **n})

def _ws_push_stats():
    try:
        cpu  = psutil.cpu_percent(interval=None)
        ram  = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.expanduser("~"))
        procs = len(psutil.pids())
        boot  = datetime.fromtimestamp(psutil.boot_time()).strftime("%d %b %H:%M")
        s = {"cpu": cpu, "ram_pct": ram.percent, "disk_pct": disk.percent, "procs": procs, "boot": boot}
        _ws_state["stats"] = s
        ws_broadcast({"type": "stats", **s})
    except Exception:
        pass

def _ws_push_workout():
    try:
        data = _load_workout_routine()
        ws_broadcast({"type": "workout", "data": data})
    except Exception:
        pass


async def _ws_handler(websocket, path=""):
    _ws_clients.add(websocket)
    try:
        # Send full current state on connect
        full = dict(_ws_state)
        full["type"] = "full_state"
        full["tasks"]    = load_tasks()
        full["workout"]  = _load_workout_routine() if os.path.exists(WORKOUT_F) else {}
        try:
            cal_data  = _load_calories()
            today_k   = datetime.now().date().isoformat()
            full["nutrition"] = {"calories": cal_data.get(today_k, 0),
                                 "protein": 0, "carbs": 0, "fat": 0}
        except Exception:
            pass
        await websocket.send(json.dumps(full))
        async for raw in websocket:
            try:
                _ws_on_cmd(json.loads(raw))
            except Exception:
                pass
    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)

def _ws_on_cmd(msg: dict):
    """Handle commands from the browser UI."""
    t = msg.get("type", "")
    if t == "action":
        action = msg.get("action", "")
        cmd_map = {
            "WEATHER":    "what is the weather",
            "NEWS":       "tell me the news",
            "BRIEFING":   "morning briefing",
            "HEALTH":     "health summary",
            "SCREEN":     "read my screen",
            "SYS_INFO":   "system info",
            "READ_NOTES": "read my notes",
            "EMAIL":      "check my email",
            "TIMER_DONE": None,
        }
        cmd = cmd_map.get(action)
        if cmd is None:
            return
        threading.Thread(target=_ws_run_cmd, args=(cmd,), daemon=True).start()

    elif t == "task_add":
        text = msg.get("text", "").strip()
        if text:
            tasks = load_tasks()
            tasks.append({"text": text, "done": False})
            save_tasks(tasks)
            _ws_push_tasks()
            if _app:
                _app.after(0, _app._render_tasks)

    elif t == "task_toggle":
        idx  = msg.get("index", -1)
        done = msg.get("done", False)
        tasks = load_tasks()
        if 0 <= idx < len(tasks):
            tasks[idx]["done"] = done
            save_tasks(tasks)
            _ws_push_tasks()
            if _app:
                _app.after(0, _app._render_tasks)

    elif t == "task_delete":
        idx = msg.get("index", -1)
        tasks = load_tasks()
        if 0 <= idx < len(tasks):
            tasks.pop(idx)
            save_tasks(tasks)
            _ws_push_tasks()
            if _app:
                _app.after(0, _app._render_tasks)

    elif t == "launch":
        app_name = msg.get("app", "")
        threading.Thread(target=_ws_launch_app, args=(app_name,), daemon=True).start()

    elif t == "cal_day":
        y, m, d = msg.get("year"), msg.get("month"), msg.get("day")
        if y and m and d:
            threading.Thread(target=_ws_cal_day, args=(y, m, d), daemon=True).start()

    elif t == "workout_save":
        day_idx = msg.get("day", 0)
        notes   = msg.get("notes", "")
        exs     = msg.get("exercises", [])
        routine = _load_workout_routine()
        day_key = DAYS[day_idx] if 0 <= day_idx < len(DAYS) else DAYS[0]
        routine[day_key]["exercises"] = [e.get("n", "") for e in exs if e.get("n")]
        routine[day_key]["notes"]     = notes
        _save_workout_routine(routine)
        ws_broadcast({"type": "toast", "text": "SESSION SAVED"})

    elif t == "get_state":
        pass  # full_state already sent on connect

def _ws_run_cmd(cmd: str):
    """Run a voice command from the UI button press."""
    global _busy
    if _busy:
        ws_broadcast({"type": "toast", "text": "BUSY — FINISH CURRENT TASK FIRST"})
        return
    _busy = True
    try:
        ws_broadcast({"type": "state", "state": "PROCESSING"})
        _ws_state["state"] = "PROCESSING"
        resp = route(cmd)
        _ws_state["response"] = resp
        ws_broadcast({"type": "response", "text": resp})
        ws_broadcast({"type": "state", "state": "SPEAKING"})
        speak(resp)
    except Exception as e:
        ws_broadcast({"type": "response", "text": str(e)})
    finally:
        _busy = False
        _ws_state["state"] = "STANDBY"
        ws_broadcast({"type": "state", "state": "STANDBY"})

def _ws_launch_app(app_name: str):
    lad = os.environ.get("LOCALAPPDATA", "")
    app_paths = {
        "Chrome":      r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "Spotify":     SPOTIFY_EXE,
        "Discord":     os.path.join(lad, r"Discord\Update.exe"),
        "VS Code":     os.path.join(lad, r"Programs\Microsoft VS Code\Code.exe"),
        "Antigravity": os.path.join(lad, r"Antigravity\Antigravity.exe"),
    }
    folder_paths = {
        "Downloads": os.path.expanduser("~/Downloads"),
        "Documents": os.path.expanduser("~/Documents"),
        "Desktop":   os.path.expanduser("~/Desktop"),
    }
    url_map = {
        "GitHub":   "https://github.com",
        "WhatsApp": "https://web.whatsapp.com",
        "Google":   "https://google.com",
    }
    try:
        if app_name in url_map:
            webbrowser.open(url_map[app_name])
        elif app_name in folder_paths:
            os.startfile(folder_paths[app_name])
        elif app_name == "Discord":
            p = app_paths["Discord"]
            if os.path.exists(p):
                subprocess.Popen([p, "--processStart", "Discord.exe"])
            else:
                webbrowser.open("https://discord.com")
        elif app_name in app_paths:
            p = app_paths[app_name]
            if os.path.exists(p):
                subprocess.Popen([p])
            else:
                webbrowser.open("https://google.com")
        else:
            webbrowser.open("https://google.com")
    except Exception as e:
        print(f"[WS launch] {e}")

def _ws_cal_day(year, month, day):
    try:
        from googleapiclient.discovery import build as _gbuild
        import datetime as dt_mod
        creds = _get_google_creds()
        if not creds:
            ws_broadcast({"type": "toast", "text": "GOOGLE NOT CONFIGURED"})
            return
        svc = _gbuild("calendar", "v3", credentials=creds)
        local_tz = dt_mod.timezone(dt_mod.timedelta(hours=1))
        start = dt_mod.datetime(year, month, day, 0, 0, 0, tzinfo=local_tz)
        end   = dt_mod.datetime(year, month, day, 23, 59, 59, tzinfo=local_tz)
        res   = svc.events().list(
            calendarId="primary",
            timeMin=start.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy="startTime"
        ).execute()
        evs = res.get("items", [])
        day_key = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        events_dict = {}
        for ev in evs:
            t_str = ev.get("start", {}).get("dateTime", "")
            t_label = t_str[11:16] if len(t_str) > 15 else "All day"
            events_dict.setdefault(day_key, []).append({"time": t_label, "title": ev.get("summary", "")})
        ws_broadcast({"type": "events", "events": events_dict})
        if not evs:
            ws_broadcast({"type": "toast", "text": f"NO EVENTS ON {day:02d}/{month:02d}"})
    except Exception as e:
        ws_broadcast({"type": "toast", "text": "CALENDAR ERROR"})
        print(f"[WS cal_day] {e}")

def _ws_stats_loop():
    """Periodically push system stats and nutrition to connected clients."""
    while True:
        time.sleep(3)
        if _ws_clients:
            _ws_push_stats()
            _ws_push_nutrition()

def _ws_active_win_loop():
    """Periodically push active window info."""
    while True:
        time.sleep(2)
        if _ws_clients:
            try:
                title = _get_active_window()
                parts = title.rsplit(" — ", 1) if " — " in title else [title, ""]
                ws_broadcast({"type": "active_win",
                               "app": parts[-1] if parts[-1] else parts[0],
                               "title": parts[0] if parts[-1] else "",
                               "pid": ""})
            except Exception:
                pass

def _start_ws_server():
    global _ws_loop
    if not _WS_OK:
        print("[NOOR] websockets not installed — pip install websockets")
        return

    loop = asyncio.new_event_loop()
    _ws_loop = loop
    asyncio.set_event_loop(loop)

    async def _serve():
        try:
            async with _websockets.serve(_ws_handler, "127.0.0.1", 8765):
                print("[NOOR] WebSocket server on ws://127.0.0.1:8765")
                threading.Thread(target=_ws_stats_loop,       daemon=True).start()
                threading.Thread(target=_ws_active_win_loop,  daemon=True).start()
                await asyncio.Future()   # run forever
        except OSError:
            print("[NOOR] Port 8765 already in use — UI may reconnect to existing server")

    loop.run_until_complete(_serve())

# ── Security ─────────────────────────────────────────────────────
_SHELL_CHARS = re.compile(r'[;&|`$><\\]')

def _safe(text: str) -> str:
    """Strip shell-injection characters from voice-sourced strings."""
    return _SHELL_CHARS.sub('', str(text))


# ╔══════════════════════════════════════════════════════════════╗
#  AUDIO — TTS
# ╚══════════════════════════════════════════════════════════════╝

async def _speak_async(text: str):
    comm = edge_tts.Communicate(text, VOICE, rate=VOICE_RATE, pitch=VOICE_PITCH)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    await comm.save(tmp)
    pygame.mixer.init()
    pygame.mixer.music.load(tmp)
    pygame.mixer.music.play()
    global _interrupt_speech
    _interrupt_speech = False
    while pygame.mixer.music.get_busy():
        if _interrupt_speech:
            pygame.mixer.music.stop()
            break
        time.sleep(0.01)
    pygame.mixer.quit()
    try:
        os.unlink(tmp)
    except Exception:
        pass


def speak(text: str):
    global is_speaking
    is_speaking = True
    if _app:
        _app.after(0, _app.set_status, "SPEAKING")
    ws_broadcast({"type": "state", "state": "SPEAKING"})
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_speak_async(text))
        loop.close()
    except Exception as e:
        print(f"TTS error: {e}")
    finally:
        time.sleep(1.5)   # let room echo settle BEFORE re-enabling mic
        is_speaking = False
        if _app:
            _app.after(0, _app.set_status, "STANDBY")
        ws_broadcast({"type": "state", "state": "STANDBY"})


# ╔══════════════════════════════════════════════════════════════╗
#  AUDIO — STT
# ╚══════════════════════════════════════════════════════════════╝

def record_and_transcribe(seconds: int, after_speech: bool = False) -> str:
    """Wait for TTS to finish, then record and transcribe. Speaking stops if mic picks up voice."""
    global _interrupt_speech
    # If user speaks while Noor is talking, interrupt it
    if is_speaking:
        _interrupt_speech = True
    while is_speaking:
        time.sleep(0.05)
    try:
        with sr.Microphone() as source:
            stt.adjust_for_ambient_noise(source, duration=0.3)
            audio = stt.listen(source, timeout=seconds, phrase_time_limit=seconds)
            return stt.recognize_google(audio, language="en-IE")
    except sr.WaitTimeoutError:
        return ""
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print(f"STT error: {e}")
        return ""
    except Exception as e:
        print(f"Mic error: {e}")
        return ""


# ╔══════════════════════════════════════════════════════════════╗
#  BRAIN — Claude API
# ╚══════════════════════════════════════════════════════════════╝

def think(prompt: str, system: str = None) -> str:
    global history
    history.append({"role": "user", "content": prompt})
    if len(history) > 20:
        history = history[-20:]
    sys_p = system or SYSTEM_PROMPT
    hdrs = {
        "x-api-key": config.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 80,
        "system": sys_p,
        "messages": history,
    }
    try:
        r = requests.post(CLAUDE_URL, json=body, headers=hdrs, timeout=20)
        r.raise_for_status()
        reply = r.json()["content"][0]["text"].strip()
    except Exception as e:
        print(f"Claude error: {e}")
        reply = "I couldn't reach the API, sir. Check your connection."
    history.append({"role": "assistant", "content": reply})
    return reply


# ╔══════════════════════════════════════════════════════════════╗
#  SCREEN — Claude Vision
# ╚══════════════════════════════════════════════════════════════╝

def _get_active_window() -> str:
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        return win.title if win else "Desktop"
    except Exception:
        return "Desktop"


def read_screen(prompt_override: str = None) -> str:
    """Capture screen and send to Claude vision. Announces before sending."""
    if _app:
        _app.after(0, _app.show, "Reading screen — sending to Claude...")
    active = _get_active_window()
    screenshot = pyautogui.screenshot()
    buf = io.BytesIO()
    screenshot.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    user_prompt = prompt_override or (
        f"Active window: {active}. "
        "Analyze what's on screen. If there's code, explain it and suggest improvements. "
        "If there's an error, tell me exactly how to fix it. Be direct (3-4 sentences max)."
    )

    hdrs = {
        "x-api-key": config.CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 400,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/png", "data": img_b64
                }},
                {"type": "text", "text": user_prompt}
            ]
        }]
    }
    try:
        r = requests.post(CLAUDE_URL, json=payload, headers=hdrs, timeout=30)
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    except Exception as e:
        return f"Screen read failed: {e}"


def help_with_coding() -> str:
    return read_screen(
        "I'm working on my computer. Look at what's on screen — "
        "if there's code, spot any bugs and tell me the single most important next step. "
        "If there's an error, tell me exactly how to fix it. Be specific and direct."
    )


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Weather / News
# ╚══════════════════════════════════════════════════════════════╝

def get_weather(city: str = None) -> str:
    city = city or getattr(config, "HOME_CITY", "Dublin")
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1}, timeout=10
        ).json()
        result = geo["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        wx = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "current_weather": True,
                "hourly": "precipitation_probability",
                "forecast_days": 1,
            }, timeout=10
        ).json()
        cw = wx["current_weather"]
        codes = {
            0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast",
            51: "light drizzle", 53: "drizzle", 61: "light rain", 63: "rain",
            71: "light snow", 73: "snow", 80: "showers", 95: "thunderstorm"
        }
        desc = codes.get(cw["weathercode"], f"code {cw['weathercode']}")
        rain = wx.get("hourly", {}).get("precipitation_probability", [0])[0]
        return (f"{city}: {cw['temperature']:.0f}°C, {desc}, "
                f"wind {cw['windspeed']:.0f} km/h. Rain chance {rain}%.")
    except Exception as e:
        return f"Weather unavailable: {e}"


_NEWS_FEEDS = {
    "ireland":   "https://www.rte.ie/news/rss/news-ireland.xml",
    "world":     "http://feeds.bbci.co.uk/news/world/rss.xml",
    "tech":      "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "science":   "http://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "business":  "http://feeds.bbci.co.uk/news/business/rss.xml",
    "sport":     "http://feeds.bbci.co.uk/sport/rss.xml",
    "politics":  "http://feeds.bbci.co.uk/news/politics/rss.xml",
    "us":        "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "america":   "http://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",
    "middle east":"http://feeds.bbci.co.uk/news/world/middle_east/rss.xml",
    "ai":        "https://feeds.feedburner.com/venturebeat/SZYF",
}

def get_news(region: str = "world") -> str:
    rl = region.lower()
    feed_url = _NEWS_FEEDS["world"]
    for key, url in _NEWS_FEEDS.items():
        if key in rl:
            feed_url = url
            break
    try:
        feed  = feedparser.parse(feed_url)
        items = [e.title for e in feed.entries[:6]]
        if not items:
            return "No news available."
        headlines = ". ".join(items)
        return think(
            f"Summarise these headlines in 2 spoken sentences, no markdown:\n{headlines}",
            system="Summarise news headlines into 2 natural spoken sentences. No lists, no markdown."
        )
    except Exception:
        return "News unavailable."


def morning_briefing() -> str:
    now = datetime.now()
    day = now.strftime("%A, %B %d")
    parts = [f"Good morning, sir. Today is {day}.", get_weather()]
    cal = get_calendar_events(days=1)
    if "not set up" not in cal and "No events" not in cal:
        parts.append(cal)
    email_b = get_email_brief(days=1)
    if "not set up" not in email_b and "No emails" not in email_b:
        parts.append(f"Email brief: {email_b}")
    parts.append(get_news("ireland"))
    return " ".join(parts)


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Google (Calendar + Gmail)
# ╚══════════════════════════════════════════════════════════════╝

def _get_google_creds():
    """Return valid Google OAuth credentials, or None if not configured."""
    if not _GOOGLE_LIBS:
        return None
    if not os.path.exists(GCREDS_F):
        return None
    creds = None
    if os.path.exists(GTOKEN_F):
        try:
            creds = GCredentials.from_authorized_user_file(GTOKEN_F, GSCOPES)
        except Exception:
            pass
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(GRequest())
            except Exception:
                creds = None
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(GCREDS_F, GSCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Google auth error: {e}")
                return None
        with open(GTOKEN_F, "w") as f:
            f.write(creds.to_json())
    return creds


def get_calendar_events(days: int = 1) -> str:
    creds = _get_google_creds()
    if not creds:
        return "Google not set up. Add google_credentials.json to the Noor folder."
    try:
        import datetime as dt_mod
        local_tz = dt_mod.timezone(dt_mod.timedelta(hours=1))  # Europe/Dublin BST
        now_local = datetime.now(tz=local_tz)
        end_local = now_local + timedelta(days=days)
        svc = _gbuild("calendar", "v3", credentials=creds)
        result = svc.events().list(
            calendarId="primary",
            timeMin=now_local.isoformat(),
            timeMax=end_local.isoformat(),
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        events = result.get("items", [])
        if not events:
            label = "today" if days == 1 else f"the next {days} days"
            return f"No events {label}."
        parts = []
        for e in events:
            start = e["start"].get("dateTime", e["start"].get("date", ""))
            if "T" in start:
                dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                t_str = dt.strftime("%I:%M %p").lstrip("0")
            else:
                t_str = "all day"
            parts.append(f"{e['summary']} at {t_str}")
        label = "today" if days == 1 else f"next {days} days"
        return f"{len(events)} event{'s' if len(events)>1 else ''} {label}: " + "; ".join(parts) + "."
    except Exception as e:
        return f"Calendar error: {e}"


def add_calendar_event(title: str, when: str, duration_h: int = 1) -> str:
    creds = _get_google_creds()
    if not creds:
        return "Google not set up. Add google_credentials.json."
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    # Ask Claude to extract both title and ISO datetime from natural language
    parsed = think(
        f"Extract the event title and start time from: '{when}'. "
        f"Now is {today} (Europe/Dublin). "
        "Reply ONLY as JSON: {{\"title\": \"...\", \"start\": \"2026-05-18T21:00:00\"}}",
        system="Extract calendar event details. Reply only with JSON, no markdown."
    ).strip()
    try:
        m = re.search(r'\{.*\}', parsed, re.DOTALL)
        d = json.loads(m.group()) if m else {}
        event_title = d.get("title", title)
        start_str   = d.get("start", "")
        start_dt    = datetime.fromisoformat(start_str)
        end_dt      = start_dt + timedelta(hours=duration_h)
        svc  = _gbuild("calendar", "v3", credentials=creds)
        body = {
            "summary": event_title,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "Europe/Dublin"},
            "end":   {"dateTime": end_dt.isoformat(),   "timeZone": "Europe/Dublin"},
        }
        svc.events().insert(calendarId="primary", body=body).execute()
        return f"Added '{event_title}' on {start_dt.strftime('%a %d %b at %I:%M %p').lstrip('0')}."
    except Exception as e:
        return f"Couldn't add event: {e}"


def get_email_brief(days: int = 1) -> str:
    creds = _get_google_creds()
    if not creds:
        return "Google not set up. Add google_credentials.json to the Noor folder."
    try:
        svc = _gbuild("gmail", "v1", credentials=creds)
        after = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
        q = f"after:{after} in:inbox -category:promotions -category:social"
        result = svc.users().messages().list(userId="me", q=q, maxResults=15).execute()
        msgs = result.get("messages", [])
        if not msgs:
            label = "today" if days == 1 else "the last 2 days"
            return f"No emails {label}."
        summaries = []
        for m in msgs[:12]:
            detail = svc.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            hdrs    = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
            sender  = hdrs.get("From", "Unknown").split("<")[0].strip().strip('"')
            subject = hdrs.get("Subject", "(no subject)")
            snippet = detail.get("snippet", "")[:80]
            summaries.append(f"From {sender}: {subject} — {snippet}")
        raw = "\n".join(summaries)
        label = "today" if days == 1 else "yesterday and today"
        return think(
            f"Give a spoken email brief for {label}. Highlight anything urgent or needing action. "
            f"Max 3 sentences, no bullet points, no markdown.\n\nEmails:\n{raw}",
            system="You summarise emails into concise spoken briefings."
        )
    except Exception as e:
        return f"Email brief failed: {e}"


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Web Query (DuckDuckGo + Wikipedia + Claude)
# ╚══════════════════════════════════════════════════════════════╝

def web_query(query: str) -> str:
    """Search the web and return a spoken answer using live data + Claude."""
    # 1. Try DuckDuckGo Instant Answer
    try:
        r = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            timeout=8
        )
        data = r.json()
        context = data.get("Answer", "") or data.get("AbstractText", "")
        if not context:
            topics = data.get("RelatedTopics", [])
            snippets = [t.get("Text", "") for t in topics[:3] if isinstance(t, dict) and "Text" in t]
            context = " | ".join(snippets)
        if context:
            return think(
                f"Use this live data to answer the question. 1-2 sentences, no markdown:\n"
                f"Context: {context}\nQuestion: {query}",
                system="Answer using the provided context. Concise spoken sentences only."
            )
    except Exception:
        pass

    # 2. Try Wikipedia summary
    try:
        wiki_q = query.replace(" ", "_")
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{wiki_q}",
            timeout=8
        )
        if r.status_code == 200:
            extract = r.json().get("extract", "")
            if extract:
                return think(
                    f"Answer this concisely using this Wikipedia extract:\n"
                    f"{extract[:600]}\nQuestion: {query}",
                    system="Answer using the provided context. 1-2 sentences, no markdown."
                )
    except Exception:
        pass

    # 3. Fall back to Claude's own knowledge
    return think(query)


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Spotify
# ╚══════════════════════════════════════════════════════════════╝

_sp = None

def _get_sp():
    global _sp
    if _sp:
        return _sp
    try:
        import spotipy
        from spotipy.oauth2 import SpotifyOAuth
        _sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=config.SPOTIFY_CLIENT_ID,
            client_secret=config.SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-modify-playback-state user-read-playback-state user-library-modify",
        ))
        return _sp
    except Exception:
        return None

def _sp_launch():
    """Launch the Spotify desktop app."""
    try:
        os.startfile(SPOTIFY_EXE)
        time.sleep(3)
    except Exception:
        pass

def _sp_active_device(wait: bool = False):
    """Return first device id. If wait=True, launch app and retry for up to 8s."""
    sp = _get_sp()
    if not sp:
        return None
    for attempt in range(1 if not wait else 8):
        try:
            devs = sp.devices().get("devices", [])
            active = [d for d in devs if d["is_active"]]
            if active:
                return active[0]["id"]
            if devs:
                return devs[0]["id"]
        except Exception:
            pass
        if wait:
            time.sleep(1)
    return None

def sp_play() -> str:
    sp = _get_sp()
    if not sp:
        return "Spotify not configured."
    dev = _sp_active_device()
    if not dev:
        _sp_launch()
        dev = _sp_active_device(wait=True)
    if not dev:
        return "Open Spotify on this device first, sir."
    try:
        sp.start_playback(device_id=dev)
        return "Playing."
    except Exception as e:
        return f"Spotify: {e}"

def sp_pause() -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    try: sp.pause_playback(); return "Paused."
    except: return "Nothing playing."

def sp_next() -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    try: sp.next_track(); return "Skipped."
    except Exception as e: return f"Spotify error: {e}"

def sp_prev() -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    try: sp.previous_track(); return "Going back."
    except Exception as e: return f"Spotify error: {e}"

def sp_search(q: str) -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    dev = _sp_active_device()
    if not dev:
        _sp_launch()
        dev = _sp_active_device(wait=True)
    try:
        res    = sp.search(q=q, type="track", limit=1)
        tracks = res["tracks"]["items"]
        if not tracks:
            return f"Nothing found for {q}."
        tr = tracks[0]
        sp.start_playback(device_id=dev, uris=[tr["uri"]])
        return f"Playing {tr['name']} by {tr['artists'][0]['name']}."
    except Exception as e:
        return f"Spotify: {e}"

def sp_now() -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    try:
        pb = sp.current_playback()
        if pb and pb.get("item"):
            t = pb["item"]
            return f"{t['name']} by {t['artists'][0]['name']}."
        return "Nothing playing."
    except: return "Spotify unavailable."

def sp_like() -> str:
    sp = _get_sp()
    if not sp: return "Spotify not configured."
    try:
        pb = sp.current_playback()
        if pb and pb.get("item"):
            sp.current_user_saved_tracks_add([pb["item"]["id"]])
            return f"Liked {pb['item']['name']}."
        return "Nothing playing."
    except Exception as e: return f"Spotify error: {e}"

def sp_open() -> str:
    _sp_launch()
    return "Opening Spotify."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — GitHub
# ╚══════════════════════════════════════════════════════════════╝

def github_repos() -> str:
    tok = getattr(config, "GITHUB_TOKEN", "")
    if not tok:
        return "GitHub token not set in config.py."
    hdrs = {"Authorization": f"token {tok}"}
    try:
        r = requests.get("https://api.github.com/user/repos",
                         headers=hdrs, params={"sort": "updated", "per_page": 5}, timeout=10)
        repos = [x["full_name"] for x in r.json()]
        return "Your recent repos: " + ", ".join(repos)
    except: return "GitHub unavailable."

def github_issues() -> str:
    tok = getattr(config, "GITHUB_TOKEN", "")
    if not tok:
        return "GitHub token not set in config.py."
    hdrs = {"Authorization": f"token {tok}"}
    try:
        r = requests.get("https://api.github.com/issues",
                         headers=hdrs,
                         params={"filter": "assigned", "state": "open", "per_page": 5},
                         timeout=10)
        issues = [f"{x['title']} ({x['repository']['name']})" for x in r.json()]
        return ("Open issues: " + "; ".join(issues)) if issues else "No open issues."
    except: return "GitHub unavailable."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Code / Clipboard
# ╚══════════════════════════════════════════════════════════════╝

def explain_code() -> str:
    code = pyperclip.paste()
    if not code or len(code) < 5:
        return "Nothing useful in clipboard."
    return think(f"Explain this code concisely, focusing on what it does and any issues:\n\n{code[:2000]}")

def summarize_clipboard() -> str:
    text = pyperclip.paste()
    if not text or len(text) < 5:
        return "Clipboard is empty."
    return think(f"Summarize this in 2-3 sentences: {text[:2000]}")


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Health
# ╚══════════════════════════════════════════════════════════════╝

def _load_health():
    if os.path.exists(HEALTH_F):
        try:
            with open(HEALTH_F) as f:
                return json.load(f)
        except: pass
    return {"logs": []}

def _save_health(data):
    with open(HEALTH_F, "w") as f:
        json.dump(data, f, indent=2)

def log_meal(desc: str) -> str:
    macros = think(f"Estimate macros for: {desc}. Reply in one line: protein Xg, carbs Xg, fat Xg, ~Xcal")
    data = _load_health()
    data["logs"].append({"type": "meal", "data": f"{desc} — {macros}",
                         "timestamp": datetime.now().isoformat()})
    _save_health(data)
    return f"Logged. {macros}"

def log_workout(desc: str) -> str:
    data = _load_health()
    data["logs"].append({"type": "workout", "data": desc,
                         "timestamp": datetime.now().isoformat()})
    _save_health(data)
    return f"Workout logged: {desc}"

def health_summary() -> str:
    data = _load_health()
    today = datetime.now().date().isoformat()
    logs  = [l for l in data["logs"] if l["timestamp"][:10] == today]
    meals    = [l["data"] for l in logs if l["type"] == "meal"]
    workouts = [l["data"] for l in logs if l["type"] == "workout"]
    parts = []
    if meals:    parts.append("Meals: " + "; ".join(meals))
    else:        parts.append("No meals logged today.")
    if workouts: parts.append("Workouts: " + "; ".join(workouts))
    else:        parts.append("No workout logged today.")
    return " ".join(parts)


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Workout Routine
# ╚══════════════════════════════════════════════════════════════╝

def _load_workout_routine() -> dict:
    if os.path.exists(WORKOUT_F):
        try:
            with open(WORKOUT_F, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Default empty routine
    return {d: {"exercises": [], "notes": ""} for d in DAYS}

def _save_workout_routine(data: dict):
    with open(WORKOUT_F, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Calories
# ╚══════════════════════════════════════════════════════════════╝

CALORIE_GOAL = 2100

def _load_calories() -> dict:
    if os.path.exists(CALORIES_F):
        try:
            with open(CALORIES_F, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_calories(data: dict):
    with open(CALORIES_F, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def log_calories(amount: int) -> str:
    data = _load_calories()
    today = datetime.now().date().isoformat()
    data[today] = data.get(today, 0) + amount
    _save_calories(data)
    total = data[today]
    remaining = CALORIE_GOAL - total
    if _app:
        _app.after(0, _app._refresh_calories)
    if remaining > 0:
        return f"Logged {amount} calories. Total today: {total} of {CALORIE_GOAL}. {remaining} remaining."
    else:
        return f"Logged {amount} calories. Total today: {total}. You've hit your goal, sir."

def get_today_calories() -> int:
    data = _load_calories()
    today = datetime.now().date().isoformat()
    return data.get(today, 0)


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Notes
# ╚══════════════════════════════════════════════════════════════╝

def take_note(text: str) -> str:
    with open(NOTES_F, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now():%Y-%m-%d %H:%M}] {text}\n")
    # Keep history in context so Noor knows what was noted
    history.append({"role": "user",    "content": f"[system] Note saved: {text}"})
    history.append({"role": "assistant","content": "Noted."})
    if len(history) > 20:
        history[-20:]
    if _app:
        _app.after(0, _app._refresh_notes)
    return "Note saved."

def read_notes() -> str:
    if not os.path.exists(NOTES_F):
        return "No notes saved yet."
    with open(NOTES_F, encoding="utf-8") as f:
        return f.read().strip() or "No notes yet."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Maps
# ╚══════════════════════════════════════════════════════════════╝

def open_maps(q: str) -> str:
    webbrowser.open(f"https://www.google.com/maps/search/{_safe(q).replace(' ', '+')}")
    return f"Opened maps for {q}."

def get_directions(dest: str) -> str:
    webbrowser.open(f"https://www.google.com/maps/dir/?api=1&destination={_safe(dest).replace(' ', '+')}")
    return f"Directions to {dest} opened."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — File / Computer Control
# ╚══════════════════════════════════════════════════════════════╝

def open_file(name: str) -> str:
    search_dirs = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
    ]
    name_l = name.lower()
    for d in search_dirs:
        try:
            for f in os.listdir(d):
                if name_l in f.lower():
                    os.startfile(os.path.join(d, f))
                    return f"Opening {f}."
        except Exception:
            continue
    return f"No file found matching '{name}'."

def take_screenshot_save() -> str:
    path = os.path.expanduser(f"~/Desktop/screenshot_{datetime.now():%Y%m%d_%H%M%S}.png")
    pyautogui.screenshot().save(path)
    return "Screenshot saved to Desktop."

def type_text(text: str) -> str:
    time.sleep(0.5)
    pyautogui.typewrite(text, interval=0.03)
    return "Typed."

def keyboard_shortcut(combo: str) -> str:
    keys = combo.lower().replace(" ", "").split("+")
    pyautogui.hotkey(*keys)
    return f"Pressed {combo}."

def create_word_doc(filename: str, content: str = "") -> str:
    try:
        from docx import Document as DocxDoc
        doc = DocxDoc()
        doc.add_heading(filename, 0)
        if content:
            doc.add_paragraph(content)
        path = os.path.expanduser(f"~/Documents/{_safe(filename)}.docx")
        doc.save(path)
        os.startfile(path)
        return f"Created and opened {filename}.docx."
    except ImportError:
        return "python-docx not installed."
    except Exception as e:
        return f"Document error: {e}"


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Email
# ╚══════════════════════════════════════════════════════════════╝

def compose_email(raw: str) -> str:
    """Parse email intent and set up pending confirmation."""
    global _pending_act
    ea = getattr(config, "EMAIL_ADDRESS", "")
    ap = getattr(config, "EMAIL_APP_PASS", "")
    if not ea or not ap:
        return "Email not configured, sir. Add EMAIL_ADDRESS and EMAIL_APP_PASS to config.py."

    parsed_raw = think(
        f"Extract email details from: '{raw}'. "
        "Return ONLY a JSON object with keys: to_name, to_email, subject, body. "
        "If email address is unknown, set to_email to empty string."
    )
    try:
        m = re.search(r'\{.*\}', parsed_raw, re.DOTALL)
        d = json.loads(m.group()) if m else {}
    except Exception:
        d = {}

    to_addr = d.get("to_email", "")
    to_name = d.get("to_name", to_addr) or to_addr
    subject = d.get("subject", "Message from Noor")
    body    = d.get("body", raw)

    if not to_addr:
        return f"I couldn't find {to_name}'s email address. Tell me the address and I'll send it."

    def _do_send():
        try:
            msg = MIMEMultipart()
            msg["From"]    = ea
            msg["To"]      = to_addr
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(ea, ap)
                s.send_message(msg)
            return f"Email sent to {to_name}."
        except Exception as e:
            return f"Email failed: {e}"

    _pending_act = (_do_send, f"Email to {to_name}")
    return f"Ready to send to {to_name}. Subject: '{subject}'. Shall I send it? Say yes or no."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — System Control
# ╚══════════════════════════════════════════════════════════════╝

def get_system_info() -> str:
    cpu  = psutil.cpu_percent(interval=0.5)
    ram  = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.expanduser("~"))
    return (f"CPU {cpu:.0f}%, RAM {ram.percent:.0f}% "
            f"({ram.available // 1024**3}GB free), "
            f"Disk {disk.percent:.0f}% used.")

def set_volume(level: int) -> str:
    global _current_vol
    level = max(0, min(100, int(level)))
    try:
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        devices   = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        vol       = cast(interface, POINTER(IAudioEndpointVolume))
        vol.SetMasterVolumeLevelScalar(level / 100.0, None)
        _current_vol = level
        return f"Volume set to {level}%."
    except Exception as e:
        return f"Volume control unavailable: {e}"

def lock_screen() -> str:
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
    return "Screen locked."

def set_reminder(text: str, minutes: int) -> str:
    def _fire():
        time.sleep(minutes * 60)
        try:
            from plyer import notification
            notification.notify(title="Noor Reminder", message=text,
                                app_name="Noor", timeout=10)
        except Exception:
            pass
        if _app:
            speak(f"Reminder, sir: {text}")
    threading.Thread(target=_fire, daemon=True).start()
    return f"Reminder set for {minutes} minutes."


# ╔══════════════════════════════════════════════════════════════╗
#  TOOLS — Tasks
# ╚══════════════════════════════════════════════════════════════╝

def load_tasks():
    if os.path.exists(TASKS_F):
        try:
            with open(TASKS_F) as f:
                return json.load(f).get("tasks", [])
        except: pass
    return []

def save_tasks(tasks):
    with open(TASKS_F, "w") as f:
        json.dump({"tasks": tasks}, f, indent=2)
    ws_broadcast({"type": "tasks", "tasks": tasks})


# ╔══════════════════════════════════════════════════════════════╗
#  ROUTER
# ╚══════════════════════════════════════════════════════════════╝

def _extract_after(text: str, *prefixes) -> str:
    tl = text.lower()
    for p in prefixes:
        if p in tl:
            return text[tl.index(p) + len(p):].strip()
    return text.strip()

def route(text: str) -> str:
    global _pending_act, _current_vol
    t = text.lower().strip()

    # ── Capabilities / help ───────────────────────────────────
    if any(x in t for x in ["what can you do", "what are your abilities",
                              "your capabilities", "how can you help",
                              "what do you do", "list your features"]):
        return (
            "I'm your digital PA, sir. I can: check weather, read news, "
            "give you a morning briefing, control Spotify, manage your tasks and notes, "
            "log meals and workouts, send emails, create Word documents, "
            "read your screen and help with coding, type text for you, "
            "press keyboard shortcuts, open any app or file, "
            "set volume, lock your screen, set reminders, show system stats, "
            "open maps and directions, search the web, "
            "and answer any question you have. Just ask."
        )

    # ── Tasks ────────────────────────────────────────────────
    if any(x in t for x in ["add task", "add a task", "new task", "create task",
                              "task -", "task:", "remind me to"]):
        raw = _extract_after(t, "add task", "add a task", "new task",
                               "create task", "remind me to")
        # Strip leading dash/colon/space that STT often adds
        raw = raw.lstrip("-:– ").strip()
        if not raw:
            raw = text.strip()
        tasks = load_tasks()
        tasks.append({"text": raw, "done": False})
        save_tasks(tasks)
        if _app:
            _app.after(0, _app._render_tasks)
        return f"Added: {raw}."

    if any(x in t for x in ["remove task", "delete task", "complete task", "mark task done"]):
        raw = _extract_after(t, "remove task", "delete task", "complete task", "mark task done").lstrip("-:– ").strip()
        tasks = load_tasks()
        for i, task in enumerate(tasks):
            if raw.lower() in task["text"].lower():
                tasks.pop(i)
                save_tasks(tasks)
                if _app:
                    _app.after(0, _app._render_tasks)
                return f"Removed: {task['text']}."
        return f"No task found matching '{raw}'."

    # ── Meeting / reminder / event → Calendar + Tasks ────────
    _EVENT_TRIGGERS = [
        "i have a meeting", "i've got a meeting", "i got a meeting",
        "i have an appointment", "i have a call", "i have a class",
        "schedule a meeting", "add a meeting", "book a meeting",
        "set a meeting", "i have a lecture", "i have an interview",
        "set a reminder to", "set reminder", "add a reminder",
        "remind me to", "remind me at",
    ]
    _HAS_TIME = any(x in t for x in ["am", "pm", "o'clock", "oclock", "tomorrow",
                                       "today", "monday", "tuesday", "wednesday",
                                       "thursday", "friday", "saturday", "sunday",
                                       "morning", "afternoon", "evening", "night"])
    _HAS_EVENT = any(x in t for x in ["meeting", "appointment", "call", "interview",
                                        "class", "lecture", "reminder", "gym", "session"])
    if any(x in t for x in _EVENT_TRIGGERS) or (_HAS_TIME and _HAS_EVENT):
        cal_result = add_calendar_event(text, text)
        # Extract just the activity for the task label (strip trigger phrases and times)
        task_text = text
        for strip in ["set a reminder to", "set reminder to", "add a reminder to",
                      "remind me to", "remind me at", "i have a meeting", "i have an appointment",
                      "i have a call", "i have a", "schedule a", "book a", "add a meeting",
                      "set a meeting"]:
            if strip in task_text.lower():
                task_text = task_text[task_text.lower().index(strip) + len(strip):].strip()
                break
        # Strip trailing time if present (e.g. "at 9am", "at 9pm tomorrow")
        task_text = re.sub(r'\s+at\s+\d+\s*(am|pm).*$', '', task_text, flags=re.IGNORECASE).strip()
        task_text = re.sub(r'\s+(tomorrow|today|tonight|morning|evening).*$', '', task_text, flags=re.IGNORECASE).strip()
        if not task_text:
            task_text = text
        tasks = load_tasks()
        tasks.append({"text": task_text, "done": False})
        save_tasks(tasks)
        if _app:
            _app.after(0, _app._render_tasks)
        return cal_result

    # ── Briefing ─────────────────────────────────────────────
    if any(x in t for x in ["morning briefing", "good morning", "daily briefing"]):
        return morning_briefing()

    # ── Weather ──────────────────────────────────────────────
    cities = ["dublin", "london", "new york", "paris", "tokyo", "lahore",
              "karachi", "islamabad", "rome", "morocco", "croatia"]
    for c in cities:
        if c in t and any(x in t for x in ["weather", "temperature", "forecast", "degrees"]):
            return get_weather(c.title())
    if any(x in t for x in ["weather", "temperature", "forecast"]):
        return get_weather()

    # ── News ─────────────────────────────────────────────────
    if any(x in t for x in ["news", "headlines", "what's happening", "what is happening",
                              "latest", "going on in"]):
        if any(x in t for x in ["ireland", "irish"]):
            region = "ireland"
        elif any(x in t for x in ["tech", "technology", "ai", "artificial intelligence"]):
            region = "ai" if "ai" in t or "artificial" in t else "tech"
        elif any(x in t for x in ["business", "finance", "market", "economy"]):
            region = "business"
        elif any(x in t for x in ["science", "health"]):
            region = "science"
        elif any(x in t for x in ["sport", "football"]):
            region = "sport"
        elif any(x in t for x in ["politic", "government", "election"]):
            region = "politics"
        elif any(x in t for x in ["america", "us ", "usa", "united states", "trump"]):
            region = "america"
        elif any(x in t for x in ["palestine", "israel", "gaza", "middle east", "hamas"]):
            region = "middle east"
        else:
            region = "world"
        return get_news(region)

    # ── Calendar ─────────────────────────────────────────────
    if any(x in t for x in ["open google calendar", "open calendar", "show my calendar",
                              "launch calendar"]):
        webbrowser.open("https://calendar.google.com")
        return "Opening Google Calendar."

    if any(x in t for x in ["what do i have today", "my calendar", "my events today",
                              "what's on today", "whats on today", "what's in my calendar"]):
        return get_calendar_events(days=1)
    if any(x in t for x in ["this week", "upcoming events", "my week", "events this week",
                              "what do i have this week"]):
        return get_calendar_events(days=7)
    if any(x in t for x in ["tomorrow", "what do i have tomorrow"]) and "event" in t:
        return get_calendar_events(days=2)
    if any(x in t for x in ["add an event", "schedule ", "add to my calendar",
                              "put on my calendar", "create an event", "new event"]):
        # Extract title and time from the command
        raw = _extract_after(t, "add an event", "schedule", "add to my calendar",
                              "put on my calendar", "create an event", "new event")
        # Ask Claude to parse it
        parsed = think(
            f"Extract event title and time from: '{raw}'. "
            "Reply ONLY as: TITLE | WHEN  (e.g. 'Meeting with Alex | tomorrow at 3pm')",
            system="Extract event title and time. Reply only as: TITLE | WHEN"
        )
        if "|" in parsed:
            parts = parsed.split("|", 1)
            title = parts[0].strip()
            when  = parts[1].strip()
        else:
            title = raw
            when  = raw
        return add_calendar_event(title, when)

    # ── Email reading ─────────────────────────────────────────
    _EMAIL_READ = [
        "check my email", "check my emails", "read my email", "read my emails",
        "read my gmail", "check gmail", "my gmail", "gmail brief", "email brief",
        "what emails", "any emails", "my inbox", "my email", "show my emails",
        "email summary", "what's in my inbox", "whats in my inbox",
        "email update", "unread emails", "new emails", "see my emails",
        "yesterday's emails", "emails from yesterday", "email brief for yesterday",
    ]
    if any(x in t for x in _EMAIL_READ):
        days = 2 if any(x in t for x in ["yesterday", "last 2", "two days"]) else 1
        return get_email_brief(days=days)

    # ── Screen / Coding assistance ───────────────────────────
    _SCREEN_HELP = [
        "help me with this", "assist me", "what should i do",
        "debug this", "what's wrong", "whats wrong", "help with this",
        "code review", "what am i doing", "what am i working on",
        "can you see what", "help me with what", "look at this",
        "what should i", "assist with this", "see what i'm doing",
        "see what im doing", "help me code",
    ]
    _SCREEN_READ = [
        "read my screen", "read screen", "what's on my screen",
        "whats on my screen", "look at my screen", "see my screen",
        "can you see", "see on my screen", "what's on screen",
        "what's on the screen", "look at the screen", "screen read",
        "look at what i have", "see what i have",
    ]
    if any(x in t for x in _SCREEN_HELP):
        return help_with_coding()
    if any(x in t for x in _SCREEN_READ):
        return read_screen()
    if any(x in t for x in ["explain code", "explain this code", "what does this code"]):
        return explain_code()
    if any(x in t for x in ["summarize clipboard", "what did i copy", "summarise clipboard"]):
        return summarize_clipboard()

    # ── Spotify ──────────────────────────────────────────────
    if any(x in t for x in ["open spotify", "launch spotify", "start spotify"]):
        return sp_open()
    if any(x in t for x in ["play spotify", "play music", "resume music", "resume spotify",
                              "unpause", "continue playing", "continue music"]):
        return sp_play()
    if any(x in t for x in ["pause music", "pause spotify", "pause", "stop music"]):
        return sp_pause()
    if any(x in t for x in ["next song", "next track", "skip song", "skip track", "skip"]):
        return sp_next()
    if any(x in t for x in ["previous song", "previous track", "last song", "go back"]):
        return sp_prev()
    if any(x in t for x in ["what's playing", "whats playing", "current track", "now playing",
                              "what song is this", "what's this song"]):
        return sp_now()
    if any(x in t for x in ["like this song", "like this", "add to liked",
                              "save this song", "heart this", "like the song"]):
        return sp_like()
    if t.startswith("play "):
        q = t[5:].strip()
        return sp_search(q) if q else sp_play()

    # ── GitHub ───────────────────────────────────────────────
    if any(x in t for x in ["my repos", "github repos", "my repositories"]):
        return github_repos()
    if any(x in t for x in ["github issues", "my issues", "open issues"]):
        return github_issues()
    if "open github" in t:
        webbrowser.open("https://github.com")
        return "Opening GitHub."

    # ── Email ────────────────────────────────────────────────
    if any(x in t for x in ["send an email", "send email", "email to ", "write an email"]):
        return compose_email(text)

    # ── Word documents ───────────────────────────────────────
    if any(x in t for x in ["create a doc", "make a word doc", "new document",
                              "create document", "new word doc"]):
        name = _extract_after(t, "called", "named", "for", "titled") or "Untitled"
        return create_word_doc(name)

    # ── Screenshots ──────────────────────────────────────────
    if any(x in t for x in ["take a screenshot", "screenshot", "capture screen"]):
        return take_screenshot_save()

    # ── Keyboard / Typing ────────────────────────────────────
    if t.startswith("type "):
        return type_text(t[5:].strip())
    if t.startswith("write ") and len(t) > 10:
        return type_text(t[6:].strip())
    if t.startswith("press ") or t.startswith("hold "):
        return keyboard_shortcut(_extract_after(t, "press ", "hold "))

    # ── File open ────────────────────────────────────────────
    if t.startswith("open ") and not any(x in t for x in [
        "open maps", "open github", "open chrome", "open vscode", "open discord",
        "open spotify", "open notepad", "open calculator", "open file explorer",
        "open google", "open youtube", "open gmail", "open instagram", "open reddit",
        "open linkedin", "open ucd", "open word", "open excel",
    ]):
        name = t[5:].strip()
        if name:
            return open_file(name)

    # ── Volume ───────────────────────────────────────────────
    if any(x in t for x in ["volume up", "turn up", "louder"]):
        return set_volume(_current_vol + 10)
    if any(x in t for x in ["volume down", "turn down", "quieter", "lower volume"]):
        return set_volume(_current_vol - 10)
    if "mute" in t:
        return set_volume(0)
    vm = re.search(r"volume to (\d+)|set volume (\d+)", t)
    if vm:
        return set_volume(int(vm.group(1) or vm.group(2)))

    # ── System ───────────────────────────────────────────────
    if any(x in t for x in ["lock screen", "lock my screen", "lock computer"]):
        return lock_screen()
    if any(x in t for x in ["system info", "how's my computer", "cpu usage",
                              "ram usage", "system status", "computer status"]):
        return get_system_info()

    # ── Reminder ─────────────────────────────────────────────
    rm = re.search(r"remind me in (\d+) minute", t)
    if rm:
        mins = int(rm.group(1))
        msg  = _extract_after(t, "to ", "about ") or "something"
        return set_reminder(msg, mins)

    # ── Calories ─────────────────────────────────────────────
    cal_m = re.search(r"(\d+)\s*(?:calories|cals|kcal)", t)
    if cal_m and any(x in t for x in ["had", "ate", "eaten", "logged", "adding",
                                        "that's", "thats", "was", "calories"]):
        return log_calories(int(cal_m.group(1)))
    if any(x in t for x in ["calories today", "how many calories", "calorie count"]):
        total = get_today_calories()
        rem   = CALORIE_GOAL - total
        return (f"{total} calories today out of {CALORIE_GOAL}. "
                f"{'%d remaining.' % rem if rem > 0 else 'Goal reached.'}")

    # ── Health ───────────────────────────────────────────────
    if any(x in t for x in ["log meal", "i ate", "i had", "food log"]):
        desc = _extract_after(t, "log meal", "i ate", "i had", "food log") or text
        return log_meal(desc)
    if any(x in t for x in ["log workout", "i worked out", "i trained", "gym session"]):
        desc = _extract_after(t, "log workout", "i worked out", "i trained", "gym session") or text
        return log_workout(desc)
    if any(x in t for x in ["health summary", "health check", "how am i doing",
                              "protein today", "macros today"]):
        return health_summary()
    if any(x in t for x in ["what's my workout", "today's workout", "my workout today",
                              "what do i train today", "what am i training"]):
        dow = datetime.now().weekday()
        day_key = DAYS[dow]
        routine = _load_workout_routine()
        d = routine.get(day_key, {})
        exercises = d.get("exercises", [])
        notes     = d.get("notes", "")
        if not exercises and not notes:
            return f"No workout set for {DAY_FULL[dow]}."
        parts = [f"{DAY_FULL[dow]}: " + ", ".join(exercises)]
        if notes:
            parts.append(notes)
        return ". ".join(parts)

    # ── Notes ────────────────────────────────────────────────
    if any(x in t for x in ["take a note", "note this", "save a note", "remember this"]):
        note = _extract_after(t, "take a note", "note this", "save a note", "remember this") or text
        return take_note(note)
    if any(x in t for x in ["read my notes", "show my notes", "what did i note", "my notes"]):
        return read_notes()

    # ── Maps / Directions ────────────────────────────────────
    if any(x in t for x in ["directions to", "navigate to", "how do i get to"]):
        dest = _extract_after(t, "directions to", "navigate to", "how do i get to")
        return get_directions(dest)
    if any(x in t for x in ["where is", "open maps", "maps "]):
        q = _extract_after(t, "where is", "open maps", "maps ")
        return open_maps(q)

    # ── Google + search combo (must be before generic sites loop) ──
    if "google" in t and any(x in t for x in ["search", "search for", "look up", "find"]):
        q = _extract_after(t, "search for", "search", "look up", "find") or ""
        if q:
            url = f"https://www.google.com/search?q={q.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Searching Google for {q}."

    # ── Websites ─────────────────────────────────────────────
    sites = {
        "youtube":      "https://youtube.com",
        "instagram":    "https://instagram.com",
        "gmail":        "https://mail.google.com",
        "reddit":       "https://reddit.com",
        "linkedin":     "https://linkedin.com",
        "google":       "https://google.com",
        "twitter":      "https://twitter.com",
        "x.com":        "https://x.com",
        "ucd":          "https://ucd.ie",
        "blackboard":   "https://brightspace.ucd.ie",
        "netflix":      "https://netflix.com",
        "notion":       "https://notion.so",
        "whatsapp":     "https://web.whatsapp.com",
        "facebook":     "https://facebook.com",
        "tiktok":       "https://tiktok.com",
        "snapchat":     "https://snapchat.com",
        "twitch":       "https://twitch.tv",
        "amazon":       "https://amazon.co.uk",
        "chatgpt":      "https://chat.openai.com",
        "claude":       "https://claude.ai",
        "github":       "https://github.com",
        "stackoverflow":"https://stackoverflow.com",
        "maps":         "https://maps.google.com",
        "translate":    "https://translate.google.com",
        "spotify":      "https://open.spotify.com",
        "canva":        "https://canva.com",
        "figma":        "https://figma.com",
        "trello":       "https://trello.com",
        "slack":        "https://slack.com",
        "zoom":         "https://zoom.us",
        "paypal":       "https://paypal.com",
        "revolut":      "https://revolut.com",
        "bbc":          "https://bbc.co.uk/news",
        "rte":          "https://rte.ie",
    }
    for k, v in sites.items():
        if k in t and any(x in t for x in ["open", "go to", "visit", "launch", "show"]):
            webbrowser.open(v)
            return f"Opening {k}."

    # ── Chrome + search combo (must be before generic app_map) ──
    if ("chrome" in t or "browser" in t) and any(x in t for x in ["search", "look up", "find", "google"]):
        q = _extract_after(t, "search for", "search", "look up", "find", "google") or ""
        url = f"https://www.google.com/search?q={q.replace(' ', '+')}" if q else "https://google.com"
        webbrowser.open(url)
        return f"Searching for {q}." if q else "Opening Chrome."

    # ── Apps ─────────────────────────────────────────────────
    app_map = {
        "chrome":        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        "vscode":        "code",
        "vs code":       "code",
        "discord":       r"C:\Users\tayya\AppData\Local\Discord\Update.exe",
        "notepad":       "notepad.exe",
        "calculator":    "calc.exe",
        "file explorer": "explorer.exe",
        "spotify":       SPOTIFY_EXE,
        "word":          "winword",
        "excel":         "excel",
    }
    for k, v in app_map.items():
        if k in t and any(x in t for x in ["open", "launch", "start", "run"]):
            try:
                if v in ("code", "notepad.exe", "calc.exe", "explorer.exe", "winword", "excel"):
                    subprocess.Popen([v])
                else:
                    os.startfile(v)
                return f"Opening {k}."
            except Exception:
                pass

    # ── Folders ──────────────────────────────────────────────
    folders = {
        "downloads": os.path.expanduser("~/Downloads"),
        "documents": os.path.expanduser("~/Documents"),
        "desktop":   os.path.expanduser("~/Desktop"),
        "pictures":  os.path.expanduser("~/Pictures"),
    }
    for k, v in folders.items():
        if k in t and any(x in t for x in ["open", "show", "go to"]):
            os.startfile(v)
            return f"Opening {k}."

    # ── Web search (verbal answer) ────────────────────────────
    if any(x in t for x in ["search for", "look up", "what is ", "who is ",
                              "tell me about", "what happened", "how does ",
                              "explain ", "latest on ", "news about "]):
        q = (
            _extract_after(t, "search for", "look up", "what is", "who is",
                            "tell me about", "what happened", "how does",
                            "explain", "latest on", "news about") or text
        )
        return web_query(q)

    # Open Google in browser (when user explicitly says "open google" or "google X")
    if t.startswith("google ") or "open google" in t:
        q = t[7:].strip() if t.startswith("google ") else ""
        url = f"https://google.com/search?q={q.replace(' ', '+')}" if q else "https://google.com"
        webbrowser.open(url)
        return f"Opening Google{f' and searching for {q}' if q else ''}."

    # ── Fallback: web query then Claude ──────────────────────
    # If it sounds like a question about the world, try web first
    question_words = ("what", "who", "where", "when", "why", "how", "which", "is ", "are ", "does ", "did ")
    if any(t.startswith(w) for w in question_words):
        return web_query(text)

    return think(text)


# ╔══════════════════════════════════════════════════════════════╗
#  MIC LEVEL MONITOR
# ╚══════════════════════════════════════════════════════════════╝

def _mic_level_loop():
    global _mic_stream, _interrupt_speech

    def callback(indata, frames, time_info, status):
        raw   = float(np.abs(indata).mean() * 300)
        level = 0.0 if is_speaking else min(raw, 100.0)
        # Only cut if user is actually speaking loudly (not ambient noise)
        if is_speaking and raw > 20:
            _interrupt_speech = True
        if _app:
            _app.after(0, _app._update_mic_level, level)

    try:
        _mic_stream = sd.InputStream(
            callback=callback, channels=1,
            samplerate=SAMPLE_RATE, blocksize=1024, dtype="float32"
        )
        _mic_stream.start()
        while True:
            time.sleep(0.05)
    except Exception as e:
        print(f"Mic level error: {e}")


# ╔══════════════════════════════════════════════════════════════╗
#  WAKE LOOP + HANDLE
# ╚══════════════════════════════════════════════════════════════╝

def _wake_loop():
    print("[Noor] Wake loop started. Say 'hey noor' to begin.")
    while True:
        try:
            if _busy or is_speaking:
                time.sleep(0.3)
                continue
            heard = record_and_transcribe(3).lower()
            if heard:
                print(f"[Wake] {heard}")
            if any(w in heard for w in WAKE_WORDS):
                threading.Thread(target=_handle, daemon=True).start()
                # Wait for the full session to finish before listening again
                time.sleep(1.0)              # let _handle set _busy=True
                while _busy or is_speaking:  # wait for session + echo to clear
                    time.sleep(0.3)
                time.sleep(2.0)              # extra cooldown so Noor's voice doesn't self-trigger
        except Exception as e:
            print(f"[Wake error] {e}")
            time.sleep(2)


def _handle():
    global _busy, _pending_act, _interrupt_speech, _force_stop
    if _busy:
        return
    _busy = True
    _force_stop = False
    app = _app

    try:
        if app:
            app.set_status("LISTENING")
        ws_broadcast({"type": "state", "state": "LISTENING"})

        for _ in range(MAX_TURNS):
            if _force_stop:
                break
            if app:
                app.set_status("LISTENING")
            ws_broadcast({"type": "state", "state": "LISTENING"})
            cmd = record_and_transcribe(COMMAND_SECS, after_speech=True)

            if not cmd or len(cmd.strip()) <= 2:
                break

            if app:
                app.show_heard(cmd)
            ws_broadcast({"type": "said", "text": cmd})
            print(f"[User] {cmd}")

            cl = cmd.lower()

            # Hard stop — kill speech, exit session, no response
            if any(w in cl for w in ["stop", "shut up", "quiet", "silence", "stop noor"]):
                _interrupt_speech = True
                _force_stop = True
                break

            if any(w in cl for w in EXIT_WORDS):
                _interrupt_speech = True
                break

            # Handle pending confirmation
            if _pending_act:
                if any(x in cl for x in ["yes", "yeah", "yep", "send it", "do it", "confirm"]):
                    fn, _ = _pending_act
                    _pending_act = None
                    if app: app.set_status("PROCESSING")
                    ws_broadcast({"type": "state", "state": "PROCESSING"})
                    result = fn()
                    if app: app.show(result)
                    ws_broadcast({"type": "response", "text": result})
                    speak(result)
                    continue
                elif any(x in cl for x in ["no", "nope", "cancel", "don't", "dont"]):
                    _pending_act = None
                    speak("Cancelled.")
                    continue

            if app:
                app.set_status("PROCESSING")
                app.show("...")
            ws_broadcast({"type": "state", "state": "PROCESSING"})

            resp = route(cmd)
            if _force_stop:
                break
            if app:
                app.show(resp)
            ws_broadcast({"type": "response", "text": resp})
            print(f"[Noor] {resp}")
            speak(resp)

    except Exception as e:
        print(f"[Handle error] {e}")
    finally:
        _busy = False
        _force_stop = False
        _pending_act = None
        ws_broadcast({"type": "state", "state": "STANDBY"})
        ws_broadcast({"type": "said", "text": "—"})
        if app:
            try:
                app.set_status("STANDBY")
                app.after(0, app._do_show_heard, "—")
            except: pass


# ╔══════════════════════════════════════════════════════════════╗
#  UI BRIDGE — routes all GUI calls to the NOOR WebSocket layer
# ╚══════════════════════════════════════════════════════════════╝

class NoorApp:
    """Thin bridge replacing the tkinter GUI.
    Exposes the same public interface (_render_tasks, set_status, show,
    show_heard, _refresh_calories, _refresh_notes, _update_mic_level, after)
    but routes everything through ws_broadcast() to noor.html.
    """

    def __init__(self):
        global _app
        _app = self
        self._status = "STANDBY"
        threading.Thread(target=_wake_loop,        daemon=True).start()
        threading.Thread(target=_mic_level_loop,   daemon=True).start()
        threading.Thread(target=self._calorie_reset_loop, daemon=True).start()
        # Push initial tasks + nutrition to any client that connects
        threading.Thread(target=self._initial_push, daemon=True).start()

    def _initial_push(self):
        time.sleep(1.5)   # give WS server time to bind
        _ws_push_tasks()
        _ws_push_nutrition()
        _ws_push_workout()

    # ── Calorie reset at 23:00 ────────────────────────────────
    def _calorie_reset_loop(self):
        while True:
            time.sleep(60)
            now = datetime.now()
            if now.hour == 23 and now.minute == 0:
                data  = _load_calories()
                today = now.date().isoformat()
                if today in data:
                    data[today] = 0
                    _save_calories(data)
                    _ws_push_nutrition()

    # ── Public interface called by voice / route code ─────────
    def after(self, _delay, fn=None, *args):
        """Fire-and-forget: schedule fn(*args) immediately in a thread."""
        if fn is None:
            return
        threading.Thread(target=fn, args=args, daemon=True).start()

    def set_status(self, s: str):
        self._status = s
        ws_broadcast({"type": "state", "state": s})

    def show(self, text: str):
        ws_broadcast({"type": "response", "text": text})

    def show_heard(self, cmd: str):
        ws_broadcast({"type": "said", "text": cmd})

    def _do_show_heard(self, cmd: str):
        self.show_heard(cmd)

    def _render_tasks(self):
        _ws_push_tasks()

    def _refresh_calories(self):
        _ws_push_nutrition()

    def _refresh_notes(self):
        pass  # notes are read on demand via voice; no push needed

    def _update_mic_level(self, level: float):
        ws_broadcast({"type": "mic_level", "level": level})

    def mainloop(self):
        """Block the main thread — keep-alive loop."""
        print("[Noor] Running. Open noor.html in Chrome.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


# ╔══════════════════════════════════════════════════════════════╗
#  ENTRY POINT
# ╚══════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    _html_path = os.path.join(BASE, "noor.html").replace("\\", "/")

    def _start_backend():
        """Called by pywebview after the GUI loop starts — safe to spin up threads here."""
        threading.Thread(target=_start_ws_server, daemon=True).start()
        time.sleep(0.6)
        NoorApp()

    try:
        import webview
        _win = webview.create_window(
            "N O O R  —  Personal AI",
            f"file:///{_html_path}",
            fullscreen=False,
            frameless=False,
            width=1280,
            height=800,
            resizable=True,
            maximized=True,
        )
        webview.start(_start_backend, debug=False)
    except Exception as e:
        print(f"[NOOR] pywebview failed ({e}), falling back to browser")
        # Fallback: start backend then open in browser
        threading.Thread(target=_start_ws_server, daemon=True).start()
        time.sleep(0.6)
        app = NoorApp()
        webbrowser.open(f"file:///{_html_path}")
        app.mainloop()
