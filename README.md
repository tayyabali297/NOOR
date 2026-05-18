# N.O.O.R — Personal AI Assistant

> A voice-activated personal AI dashboard running fully on your desktop. No cloud deployment, no subscriptions beyond the APIs you configure. Just say *"Hey Noor"* and it responds.

---

## What Is This?

NOOR is a personal AI assistant built for Windows. It combines a futuristic HUD-style dashboard (HTML/CSS/JS) with a Python backend that handles voice recognition, text-to-speech, and a wide range of tools — weather, email, Spotify, calendar, screen reading, system control, health tracking, and more.

The name comes from the Arabic word for *light*. The design is inspired by Iron Man's J.A.R.V.I.S — a heads-up display that feels like it belongs in a sci-fi film but runs on your own machine.

---

## Demo / Screenshots

The dashboard is a three-column layout:

| Left | Centre | Right |
|---|---|---|
| Task list | Animated orb + voice responses | Monthly calendar |
| Active window | Mic level bar | System stats (CPU/RAM/Disk) |
| Quick notes | Quick action buttons | Nutrition tracker |
| | App launcher grid | Workout log |

The orb changes colour and animation based on state:
- **Standby** — slow pulse, dim teal
- **Listening** — bright green ring
- **Processing** — amber pulse
- **Speaking** — cyan glow

---

## Features

### Voice Control
- **Wake word:** "Hey Noor" (say it and the orb activates)
- **Continuous conversation:** stays active for up to 5 turns after wake word
- **British female voice:** edge-tts with `en-GB-SoniaNeural`
- **Echo prevention:** mic is blocked for 1.5s after Noor finishes speaking

### Weather
- Real-time weather via [Open-Meteo](https://open-meteo.com/) (no API key needed)
- Current conditions, temperature, wind speed

### News
- Live headlines via RSS feeds
- Ireland news, World news, Tech, Science, Health

### Email (Gmail)
- Read your unread emails from the last 1–2 days
- Summary-style brief: sender, subject, snippet
- Requires Gmail OAuth (see setup below)

### Google Calendar
- Upcoming events for today and tomorrow
- Add events by voice
- Reminders for meetings

### Spotify
- Play, pause, skip, previous
- Search and play any song/artist/playlist
- Volume control

### Screen Awareness (Claude Vision)
- "Help me with this" — sends a screenshot to Claude and gets context-aware advice
- "Read my screen" — describes what's on screen
- Detects the active window title for context

### System Control
- Volume up/down/set to N
- Lock screen
- CPU, RAM, disk usage
- Set reminders (spoken + system notification)

### Task Management
- Add, complete, delete tasks by voice or via the dashboard UI
- Tasks persist in `data/tasks.json`

### Health & Fitness Tracking
- Log meals: "I had 200g chicken" — Noor estimates macros and adds to daily total
- Log workouts: "I did chest day, bench press 5 sets"
- Daily health summary: calories, protein, workout log

### Notes
- "Take a note: [anything]" — saved to `data/notes.txt`
- "Read my notes" — Noor reads them back

### App Launcher
- Voice: "Open Chrome", "Open VS Code", "Open Discord", etc.
- Dashboard buttons for common apps

### File Operations
- "Open [filename]" — searches Documents, Desktop, Downloads
- "Take a screenshot" — saves PNG to Desktop with timestamp

### GitHub
- "My GitHub issues" — lists open issues from your repos
- Configurable via `GITHUB_TOKEN` in `config.py`

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    noor.html                        │
│          (Dashboard — HTML/CSS/JS)                  │
│                                                     │
│  WebSocket client  ←──────────────────→  User UI   │
└──────────────────────┬──────────────────────────────┘
                       │ ws://127.0.0.1:8765
                       │ (JSON messages)
┌──────────────────────┴──────────────────────────────┐
│                    main.py                          │
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Wake Loop  │  │  WebSocket   │  │  NoorApp  │  │
│  │  (thread)   │  │  Server      │  │  Bridge   │  │
│  └──────┬──────┘  └──────────────┘  └───────────┘  │
│         │                                           │
│  ┌──────▼──────┐                                   │
│  │    STT      │  Google Speech Recognition         │
│  │  record()   │  language="en-IE"                  │
│  └──────┬──────┘                                   │
│         │                                           │
│  ┌──────▼──────┐                                   │
│  │   route()   │  Pattern-matched command router    │
│  └──────┬──────┘                                   │
│         │ (unmatched)                               │
│  ┌──────▼──────┐                                   │
│  │   think()   │  Claude API (claude-haiku)         │
│  └──────┬──────┘                                   │
│         │                                           │
│  ┌──────▼──────┐                                   │
│  │   speak()   │  edge-tts → pygame audio           │
│  └─────────────┘                                   │
└─────────────────────────────────────────────────────┘
```

**How a voice command flows:**

1. Wake loop records 3-second audio snippets continuously
2. Google STT transcribes the audio
3. If the text matches a wake word → `_handle()` starts
4. `_handle()` records the actual command (7 seconds)
5. `route()` checks for known patterns (weather, email, Spotify, etc.)
6. If no pattern matches → `think()` sends it to Claude API
7. Response is spoken via `speak()` (edge-tts → MP3 → pygame)
8. Response is also sent to the dashboard via WebSocket

**WebSocket message types (backend → frontend):**

| Type | Payload | What it does |
|---|---|---|
| `state` | `{state: "LISTENING"}` | Changes orb colour + animation |
| `response` | `{text: "..."}` | Shows Noor's response in centre panel |
| `said` | `{text: "..."}` | Shows what you said |
| `tasks` | `{tasks: [...]}` | Updates task list |
| `nutrition` | `{calories, protein, ...}` | Updates nutrition panel |
| `workout` | `{...}` | Updates workout panel |
| `stats` | `{cpu, ram, disk}` | Updates system stats |
| `active_win` | `{title: "..."}` | Shows active window |
| `mic_level` | `{level: 0–100}` | Animates mic level bar |

---

## Prerequisites

- **Windows 10/11** (pywebview uses Edge WebView2, which ships with Windows 11 by default)
- **Python 3.11** — download from [python.org](https://www.python.org/downloads/release/python-3119/)
- **Microsoft Edge WebView2 Runtime** — comes pre-installed on Windows 11. If on Windows 10, download from [Microsoft](https://developer.microsoft.com/en-us/microsoft-edge/webview2/)
- **A microphone** — any mic works, including laptop built-in
- **Internet connection** — for Google STT, edge-tts, weather, Claude API

---

## Installation

### 1. Clone the repo

```bash
git clone https://github.com/tayyabali297/NOOR.git
cd NOOR
```

### 2. Install Python dependencies

```bash
py -3.11 -m pip install -r requirements.txt
```

> **Note on PyAudio:** If `pip install pyaudio` fails on Windows, install it via wheel:
> ```bash
> py -3.11 -m pip install pipwin
> py -3.11 -m pipwin install pyaudio
> ```

### 3. Create your config file

Copy the template and fill in your API keys:

```bash
copy config.example.py config.py
```

Open `config.py` and fill in:

```python
CLAUDE_API_KEY        = "sk-ant-..."       # From console.anthropic.com
SPOTIFY_CLIENT_ID     = "..."              # From developer.spotify.com
SPOTIFY_CLIENT_SECRET = "..."             # From developer.spotify.com
GITHUB_TOKEN          = ""                # Optional — github.com/settings/tokens
GITHUB_USERNAME       = ""                # Your GitHub username
HOME_CITY             = "Dublin"          # Your city for weather
EMAIL_ADDRESS         = ""               # Gmail address (optional)
EMAIL_APP_PASS        = ""               # Gmail App Password (optional)
```

### 4. Set up API keys

#### Claude API (required — this is Noor's brain)
1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an account and add billing (pay-as-you-go, very cheap for personal use — haiku model costs ~$0.001 per conversation)
3. Go to **API Keys** → **Create Key**
4. Paste into `CLAUDE_API_KEY` in `config.py`

#### Spotify (optional — for music control)
1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set the **Redirect URI** to `http://127.0.0.1:8888/callback`
4. Copy the **Client ID** and **Client Secret** into `config.py`
5. First time you use a Spotify command, a browser window will open asking you to log in — do that once and the token is cached

#### Gmail (optional — for email reading)
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project
3. Enable the **Gmail API** and **Google Calendar API**
4. Create **OAuth 2.0 credentials** (Desktop App type)
5. Download the credentials JSON and save it as `google_credentials.json` in the project folder
6. First time you run a Gmail or Calendar command, a browser will open to authorise — do this once and the token is cached in `google_token.json`

#### GitHub (optional)
1. Go to [github.com/settings/tokens](https://github.com/settings/tokens)
2. Generate a token with `repo` scope
3. Paste into `GITHUB_TOKEN` in `config.py`

### 5. Set up your personal profile

Edit `jarvis_knowledge.md` and replace the contents with your own profile. This file is loaded into every Claude prompt, so Noor understands your context. Include:
- Your name, age, location
- Current projects
- Goals and preferences
- Anything you want Noor to know about you

### 6. Run it

```bash
py -3.11 main.py
```

Or double-click `launch.bat`.

A desktop window will open showing the NOOR dashboard. Say **"Hey Noor"** to activate.

---

## Voice Commands Reference

### Wake Words
```
Hey Noor / Noor / Okay Noor / Wake up Noor
```

### Weather
```
What's the weather?
What's the temperature in [city]?
Will it rain today?
```

### News
```
What's the news?
Any headlines?
Tech news / Ireland news / Science news
```

### Email
```
Check my email
Read my emails
Email brief
What's in my inbox?
```

### Calendar
```
What have I got today?
Upcoming events
Add [event] on [day] at [time]
```

### Spotify
```
Play music / Resume
Pause / Stop music
Next / Skip / Previous
Play [song/artist/playlist]
Volume up / Volume down
Set volume to 50
```

### Screen & Code Help
```
Help me with this
Read my screen
What's on my screen?
Debug this
What should I do?
```

### Tasks
```
Add task [description]
Add [task] to my list
Complete task [name]
Delete task [name]
What are my tasks?
```

### Health & Fitness
```
I had [food] — logs nutrition
Log [meal] — logs nutrition
I did [workout] — logs exercise
Health summary
How am I doing today?
```

### Notes
```
Take a note: [text]
Note this: [text]
Read my notes
What did I note?
```

### System Control
```
Volume up / Volume down
Set volume to [0–100]
Lock screen / Lock my computer
System info / How's my computer?
Remind me in [N] minutes to [task]
Take a screenshot
```

### Apps & Files
```
Open Chrome / VS Code / Discord / Notepad
Open [filename]
Open file explorer
```

### GitHub
```
My GitHub issues
Open GitHub
```

### Directions & Maps
```
Directions to [place]
How do I get to [place]?
Open maps
```

### Conversation
```
[anything else] — falls through to Claude (conversational AI)
```

### End session
```
Thanks / Bye / Stop / That's all / Goodbye
```

---

## Project Structure

```
NOOR/
├── main.py                  # Backend — everything: voice, tools, WebSocket server, routing
├── noor.html                # Frontend dashboard — HTML/CSS/JS, connects via WebSocket
├── config.py                # Your API keys (never commit this)
├── config.example.py        # Template — copy this to config.py
├── jarvis_knowledge.md      # Your personal profile loaded into every Claude prompt
├── requirements.txt         # Python dependencies
├── launch.bat               # Double-click to run (opens in terminal)
├── jarvis.vbs               # Silent launcher (no terminal window)
├── make_shortcut.ps1        # Creates a Desktop shortcut
└── data/
    ├── tasks.json           # Task list (auto-created)
    ├── notes.txt            # Voice notes (auto-created)
    ├── health.json          # Meal & workout log (auto-created)
    └── calories.json        # Daily calorie tracker (auto-created)
```

### Key functions in `main.py`

| Function | What it does |
|---|---|
| `_wake_loop()` | Runs forever on a thread — listens for wake word |
| `_handle()` | Runs one conversation session (up to 5 turns) |
| `route(text)` | Pattern-matches text to a tool, or falls through to Claude |
| `think(prompt)` | Sends a prompt to Claude API, returns response |
| `speak(text)` | Converts text to speech via edge-tts, plays via pygame |
| `record_and_transcribe(N)` | Records N seconds of audio, returns transcription |
| `ws_broadcast(msg)` | Sends a JSON message to all connected dashboard clients |
| `get_weather()` | Fetches weather from Open-Meteo |
| `get_news(topic)` | Fetches RSS news headlines |
| `get_email_brief()` | Reads Gmail via OAuth |
| `get_calendar_events()` | Fetches Google Calendar events |
| `read_screen()` | Screenshots + sends to Claude Vision API |
| `log_meal(text)` | Parses food log and estimates macros via Claude |

---

## How It Works Under the Hood

### The WebSocket Bridge

The dashboard (`noor.html`) is a static HTML file that can't run Python. Instead, `main.py` runs a WebSocket server on `ws://127.0.0.1:8765`. The HTML page connects to this server and listens for JSON messages. When Noor speaks, the response is also sent to the dashboard. When you click a button on the dashboard, it sends a JSON message to the server which triggers the same code path as a voice command.

This approach means:
- The frontend is just HTML/CSS/JS — easy to customise the look
- The backend is pure Python — easy to add new tools
- They communicate via a clean JSON API

### The Command Router

Before every command reaches Claude, it goes through `route()` — a long chain of `if/elif` checks. This handles deterministic commands (weather, email, Spotify, etc.) without an API call, which makes them faster and cheaper. Only unrecognised commands reach Claude.

Example flow:
```
User: "play Frank Ocean"
  → route() sees t.startswith("play ")
  → extracts "Frank Ocean" as search query
  → calls spotify_search("Frank Ocean")
  → returns "Playing Frank Ocean, sir."
  → speak() reads that aloud
  → ws_broadcast sends it to dashboard
```

```
User: "what do you think about stoicism?"
  → route() finds no match
  → think() sends to Claude API with SYSTEM_PROMPT + jarvis_knowledge.md
  → Claude responds
  → speak() reads response
```

### Voice Pipeline

```
Microphone → PyAudio → SpeechRecognition → Google STT → text
```

The `record_and_transcribe()` function uses Google's free Speech-to-Text endpoint (via the `SpeechRecognition` library, no API key needed). It records audio with PyAudio and sends it to Google.

For accents (Irish/Pakistani/South Asian): the language is set to `en-IE` (Irish English) which handles mixed accents better than the default `en-US`.

### Text-to-Speech

```
text → edge-tts (en-GB-SoniaNeural) → MP3 → pygame audio
```

`edge-tts` uses Microsoft Edge's neural TTS engine, which is free and high-quality. The British female voice (`en-GB-SoniaNeural`) has a clear, natural delivery. The audio is generated into a temp file and played back via `pygame.mixer`.

**Echo prevention:** After Noor finishes speaking, the microphone stays blocked for 1.5 seconds to prevent the mic from picking up room echo of Noor's voice. An additional 2-second cooldown is applied in the wake loop after each conversation session.

---

## Customisation

### Change the wake word

In `main.py`, edit `WAKE_WORDS`:

```python
WAKE_WORDS = [
    "hey noor", "noor", "okay noor",
    # Add more variants here
]
```

### Change the voice

In `main.py`, change `VOICE`:

```python
VOICE = "en-GB-SoniaNeural"   # British female
# Other options:
# "en-US-JennyNeural"         # American female
# "en-IE-EmilyNeural"         # Irish female
# "en-GB-RyanNeural"          # British male
```

Full list: run `py -3.11 -c "import edge_tts, asyncio; asyncio.run(edge_tts.list_voices())"` or see the [edge-tts docs](https://github.com/rany2/edge-tts).

### Add a new voice command

In the `route()` function in `main.py`, add a new `if` block before the Claude fallback:

```python
if any(x in t for x in ["flip a coin", "coin flip"]):
    import random
    return "Heads." if random.random() > 0.5 else "Tails."
```

### Change the personal profile

Edit `jarvis_knowledge.md` with your own details. Everything in this file is prepended to every Claude API call, so Noor always has your context.

### Add a dashboard button

In `noor.html`, find the `.actions` div and add a button:

```html
<button class="btn" onclick="sendCmd('your command here')">LABEL</button>
```

---

## Troubleshooting

### "PyAudio not found" / microphone not working
```bash
py -3.11 -m pip install pipwin
py -3.11 -m pipwin install pyaudio
```

### "webview not found" / dashboard opens in Chrome instead
```bash
py -3.11 -m pip install pywebview
```

### Wake word not triggering
- Check your microphone is set as the default input device in Windows Sound Settings
- Say "Hey Noor" clearly — pause briefly before speaking
- If Google STT is mis-transcribing "Noor", add the mis-transcribed word to `WAKE_WORDS` (print the `[Wake]` output in the terminal to see what it hears)

### Spotify not working
- Make sure Spotify is open and playing (or has been open recently) before using voice commands
- The Redirect URI in your Spotify Developer app must be exactly `http://127.0.0.1:8888/callback`
- Delete `.cache` in the project folder and re-authenticate

### Dashboard shows blank / white page
- Make sure `main.py` is running (the WebSocket server must be up)
- Check the terminal for `[NOOR] WebSocket server on ws://127.0.0.1:8765`
- Try refreshing the pywebview window (right-click → Reload)

### High CPU usage
- The dashboard is GPU-composited — make sure hardware acceleration is enabled in your Edge/Chrome settings
- If your machine is under load, reduce the stats refresh rate in `main.py` by finding `_ws_stats_loop` and increasing the `time.sleep()` value

---

## Tech Stack

| Component | Technology |
|---|---|
| AI brain | [Claude API](https://www.anthropic.com/api) (claude-haiku-4-5) |
| Voice input | [Google Speech Recognition](https://pypi.org/project/SpeechRecognition/) via `sr` library |
| Voice output | [edge-tts](https://github.com/rany2/edge-tts) + pygame |
| Dashboard UI | Vanilla HTML/CSS/JS (no framework) |
| Desktop window | [pywebview](https://pywebview.flowrl.com/) (EdgeChromium on Windows) |
| Backend | Python 3.11 |
| Backend↔Frontend | WebSocket ([websockets](https://websockets.readthedocs.io/) v16) |
| Weather | [Open-Meteo](https://open-meteo.com/) (free, no key) |
| News | RSS feeds via [feedparser](https://feedparser.readthedocs.io/) |
| Email/Calendar | Gmail & Google Calendar APIs via OAuth |
| Music | [Spotipy](https://spotipy.readthedocs.io/) (Spotify Web API) |
| Screen capture | [pyautogui](https://pyautogui.readthedocs.io/) + Claude Vision |
| System stats | [psutil](https://psutil.readthedocs.io/) |
| Fonts | Orbitron, Rajdhani, JetBrains Mono (Google Fonts CDN) |

---

## Security Notes

- `config.py` is in `.gitignore` and will never be committed — keep your keys there
- `google_credentials.json` and `google_token.json` are also excluded from git
- All processing is local except: Claude API calls (prompts/responses), Google STT (3-second audio clips), edge-tts (text for synthesis), weather/news (public APIs)
- Screen capture is only sent to Claude when you explicitly say "read my screen" or "help me with this" — never automatic
- No incoming connections — NOOR is purely outbound. No server, no webhook, no remote access possible

---

## Contributing

This is a personal project but PRs are welcome. Some ideas if you want to extend it:

- [ ] Home Assistant integration (smart lights, thermostat)
- [ ] WhatsApp/Telegram message reading
- [ ] Pomodoro timer with voice alerts
- [ ] Local LLM option (Ollama) for offline use
- [ ] Multi-language support
- [ ] iOS/Android companion app for notifications

---

## License

MIT — do whatever you want with it. If you build something cool on top of it, I'd love to see it.

---

*Built by [Tayyab](https://github.com/tayyabali297) — Dublin, 2026*
