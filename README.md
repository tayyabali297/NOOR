# N.O.O.R — Personal AI Assistant

A voice-activated personal AI assistant for Windows. Talks back. Controls your computer. Knows your context. Runs entirely locally — no cloud deployment, no subscription.

Built for Tayyab. Dublin, Ireland. Windows 11. Python 3.11.

---

## How It Works — Architecture

```
You speak
    │
    ▼
┌─────────────────────┐
│  Microphone         │  Always listening at low sensitivity
│  (sounddevice)      │
└────────┬────────────┘
         │ audio stream
         ▼
┌─────────────────────┐
│  Wake Word Check    │  "hey noor", "noor", "okay noor" + variants
│  (SpeechRecognition)│
└────────┬────────────┘
         │ wake word detected
         ▼
┌─────────────────────┐
│  Command Recording  │  7 seconds to say your command
│  (Google STT)       │
└────────┬────────────┘
         │ text
         ▼
┌─────────────────────┐
│  Router (route())   │  ~60 built-in command patterns
└────┬──────────┬─────┘
     │ matched  │ no match
     ▼          ▼
┌─────────┐  ┌───────────────────┐
│  Tool   │  │  Claude Haiku API │  Conversational fallback
│ (local) │  │  (Anthropic)      │  Knows your personal profile
└────┬────┘  └────────┬──────────┘
     └────────────────┘
              │ text response
              ▼
┌─────────────────────┐
│  edge-tts           │  Microsoft Neural TTS, British voice
│  (en-GB-SoniaNeural)│
└────────┬────────────┘
         │ audio
         ▼
┌─────────────────────┐
│  pygame             │  Plays the audio
└────────┬────────────┘
         │
         ▼
     You hear it
```

---

## Folder Structure

```
N.O.O.R/
│
├── main.py                  ← The entire app (GUI + voice + tools + routing)
├── config.py                ← Your API keys — never commit this
├── config.example.py        ← Template to create config.py from
│
├── noor_knowledge.md        ← Your personal profile (loaded into every Claude prompt)
├── noor.html                ← Browser-based dashboard (connects via WebSocket)
│
├── noor.vbs                 ← Desktop launcher (no black console window)
├── launch.bat               ← Terminal launcher (with port cleanup)
│
├── requirements.txt         ← Python packages to install
├── test_jarvis.py           ← Automated tests for the routing logic
│
├── google_credentials.json  ← Google OAuth credentials (from Google Cloud Console)
├── google_token.json        ← Saved Google login token (auto-generated on first use)
│
├── tayyab_review/
│   └── HOW_IT_WORKS.md      ← Plain English explanation of every decision made
│
└── data/
    ├── tasks.json           ← Your task list
    ├── health.json          ← Logged meals
    ├── workout.json         ← Weekly training split + session logs
    ├── calories.json        ← Daily calorie totals by date
    └── notes.txt            ← Voice notes with timestamps
```

---

## Tech Stack

| Component | Library / Service | Why |
|---|---|---|
| GUI | customtkinter | Modern-looking, runs on Windows without setup |
| Voice input | SpeechRecognition + Google STT | Free, no API key needed |
| AI brain | Claude Haiku (Anthropic API) | Fast, cheap, smart enough for 1-sentence answers |
| Voice output | edge-tts (Microsoft Neural) | Free, high quality, no API key needed |
| Audio playback | pygame | Reliable cross-platform audio |
| Spotify | spotipy | Official Spotify API wrapper |
| Calendar / Gmail | google-api-python-client | Official Google API |
| System stats | psutil | CPU, RAM, disk info |
| Audio stream | sounddevice + numpy | Low-latency mic input for level meter |
| HTTP requests | requests | For weather, news, GitHub APIs |

---

## Wake Words

Say any of these to activate N.O.O.R:

```
"Hey Noor"           ← Primary wake word
"Noor"
"Okay Noor"
"Hello Noor"
"Yo Noor"
"Wake up Noor"
"Noor wake up"
```

STT variants (handles accent + mishearing):
`"hey nor"` / `"hey nur"` / `"hey nore"` / `"hey new"` / `"hey nu"` / `"a noor"` / `"a nor"`

**End a session:** say `"thanks"`, `"bye"`, `"stop"`, `"that's all"`, or `"dismiss"`

After activation, you can keep talking for up to **5 back-and-forth turns** before N.O.O.R returns to standby.

---

## All Voice Commands

### Briefings & Info
| Say | Does |
|---|---|
| `"Morning briefing"` | Date, weather, top news, calendar events, email summary |
| `"What's the weather"` | Dublin weather |
| `"Weather in [city]"` | Weather for any city |
| `"Tell me the news"` | World headlines |
| `"Irish news"` / `"Tech news"` / `"AI news"` | Topic-specific headlines |
| `"System info"` | CPU, RAM, disk usage, uptime |

### Google Calendar
| Say | Does |
|---|---|
| `"What do I have today"` | Today's events |
| `"My week"` / `"Events this week"` | Next 7 days |
| `"Add a meeting at 3pm tomorrow"` | Creates Google Calendar event |
| `"I have a lecture at 9am"` | Creates event + adds to task list |
| `"Open Google Calendar"` | Opens in browser |

### Gmail
| Say | Does |
|---|---|
| `"Check my email"` | Summary of today's inbox |
| `"Yesterday's emails"` | Last 2 days |
| `"Send an email to [name]"` | Compose and send |

### Tasks & Notes
| Say | Does |
|---|---|
| `"Add task [anything]"` | Adds to task list in GUI |
| `"Remove task [name]"` | Removes matching task |
| `"Take a note [text]"` | Saves timestamped note |
| `"Read my notes"` | Reads notes back |

### Spotify
| Say | Does |
|---|---|
| `"Play"` / `"Resume music"` | Resumes playback |
| `"Pause"` / `"Stop music"` | Pauses |
| `"Next song"` / `"Skip"` | Skips track |
| `"Previous song"` / `"Go back"` | Previous track |
| `"What's playing"` | Current song and artist |
| `"Like this song"` | Saves to Liked Songs |
| `"Play Frank Ocean"` | Searches and plays |
| `"Open Spotify"` | Launches Spotify app |

### Health & Fitness
| Say | Does |
|---|---|
| `"I ate chicken and rice"` | Logs meal with macro estimate |
| `"I had 500 calories"` | Logs calorie count |
| `"Log workout chest and back"` | Logs workout session |
| `"Health summary"` | Daily meals, calories, macros |
| `"Macros today"` | Protein + calorie total |
| `"What's my workout today"` | Today's training split |
| `"Calories today"` | How many kcal logged vs goal |

### Apps & Websites
| Say | Does |
|---|---|
| `"Open Chrome"` | Launches Chrome |
| `"Open VS Code"` | Launches VS Code |
| `"Open Discord"` | Launches Discord |
| `"Open Notepad"` | Opens Notepad |
| `"Open Calculator"` | Opens Calculator |
| `"Open File Explorer"` | Opens Explorer |
| `"Open YouTube"` | Opens youtube.com |
| `"Open GitHub"` | Opens github.com |
| `"Open UCD"` | Opens ucd.ie |
| `"Open Blackboard"` | Opens UCD Brightspace |
| `"Open Netflix"` / `"Open Notion"` | Any site in the list |
| `"Search Google for [topic]"` | Google search |

### Computer Control
| Say | Does |
|---|---|
| `"Type [text]"` | Types at cursor |
| `"Press Ctrl+C"` | Any keyboard shortcut |
| `"Take a screenshot"` | Captures and saves screen |
| `"Read my screen"` | Screenshots + AI analysis |
| `"Explain code"` | Reads clipboard, explains it |
| `"Volume up"` / `"Volume down"` | System volume ±10 |
| `"Mute"` | Mutes audio |
| `"Volume to 60"` | Sets exact level |
| `"Lock screen"` | Locks Windows |
| `"Remind me in 10 minutes to [x]"` | Sets a timed reminder |

### Maps & Directions
| Say | Does |
|---|---|
| `"Directions to UCD"` | Opens Google Maps route |
| `"Where is [place]"` | Opens Maps location |
| `"Open maps"` | Opens Google Maps |

### GitHub
| Say | Does |
|---|---|
| `"My repos"` | Lists your GitHub repositories |
| `"GitHub issues"` | Lists open issues |

### Documents
| Say | Does |
|---|---|
| `"Create a word doc called [name]"` | Creates and opens a .docx file |

---

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Create your config file
Copy `config.example.py` to `config.py` and fill in your keys:
```python
CLAUDE_API_KEY = "sk-ant-..."     # From console.anthropic.com
SPOTIFY_CLIENT_ID = "..."          # From developer.spotify.com
SPOTIFY_CLIENT_SECRET = "..."
GITHUB_TOKEN = "..."               # Optional — for repos/issues
```

### 3. Google Calendar & Gmail (optional)
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project, enable Calendar API and Gmail API
3. Create OAuth 2.0 credentials, download as `google_credentials.json`
4. Put it in the project folder
5. First time N.O.O.R uses calendar/email, a browser will open to ask permission — approve it once

### 4. Run it
```bash
py -3.11 main.py
```
Or double-click `N.O.O.R` on your desktop (uses `noor.vbs` to launch without a terminal window).

---

## GUI Layout

```
┌────────────────────────────────────────────────────────────┐
│  N.O.O.R                           PERSONAL AI  v1.0       │
├──────────────┬──────────────────────────┬──────────────────┤
│              │                          │                  │
│   TASKS      │      NOOR ORB            │   CALENDAR       │
│              │    (animated dot)        │  (monthly view)  │
│  [ ] Task 1  │     ● STANDBY            │                  │
│  [ ] Task 2  │                          │  May 2026        │
│              │  "what you said"         │  Mo Tu We Th...  │
│  + Add Task  │  "noor's response"       │  ● event dots    │
│              │                          │                  │
│  ──────────  │  WEATHER NEWS BRIEF      │                  │
│   TIMER      │  HEALTH EMAIL SCREEN     │   MAPS SEARCH    │
│   00:00      │                          │                  │
│  START RESET │  [mic level indicator]   │  UCD  CITY  HOME │
└──────────────┴──────────────────────────┴──────────────────┘
```

---

## Data Files

All your data stays local in the `data/` folder. Plain JSON files — readable in any text editor.

**tasks.json**
```json
{
  "tasks": [
    {"text": "Buy groceries", "done": false},
    {"text": "Submit lab report", "done": true}
  ]
}
```

**calories.json**
```json
{
  "2026-05-25": 2340,
  "2026-05-24": 2610
}
```

**workout.json** — your weekly split:
```json
{
  "mon": {"exercises": ["Chest", "Triceps"], "notes": ""},
  "tue": {"exercises": ["Back", "Biceps"], "notes": ""}
}
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| App won't start | Make sure `config.py` exists with your Claude API key |
| Wake word not triggering | Speak clearly, check microphone is set as default in Windows Sound settings |
| N.O.O.R hears itself | Normal — `is_speaking` flag mutes the mic during TTS. If it still happens, increase `energy_threshold` in main.py (line ~143) |
| Google Calendar not working | Check `google_credentials.json` is in the project folder and run once to approve access |
| Spotify commands not working | Spotify must be open. Check `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` in config.py |
| Desktop shortcut gives "file not found" | Right-click shortcut → Properties → check the path matches your actual folder location |
| GUI freezes | Shouldn't happen — all voice processing runs on background threads. If it does, restart with `launch.bat` |

---

## Running Tests

```bash
py -3.11 test_jarvis.py
```

Tests cover: routing for weather, news, tasks, notes, Spotify, workouts, meals, calories, and calendar. All 9 should pass.

---

## What's Not Included (By Design)

- **No cloud deployment** — runs 100% on your machine
- **No web server** — `noor.html` connects locally via WebSocket on port 8765
- **No database** — JSON files are enough for one person's data
- **No always-on cloud AI** — Claude is only called when the router can't handle a command locally
