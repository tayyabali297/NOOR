# N.O.O.R — How It Works (Plain English)

Written for Tayyab. No jargon. Just a straight explanation of every decision made.

---

## What Is N.O.O.R?

N.O.O.R is your personal AI assistant that runs on your Windows laptop. You talk to it, it talks back, and it can do things on your computer — open apps, check your calendar, control Spotify, log your meals, and a lot more. Think Iron Man's Jarvis but running locally, privately, on your own machine with no monthly subscription.

The name stands for... well, it's a good name. Clean, personal, yours.

---

## What Happens When You Double-Click the Shortcut

1. You double-click `N.O.O.R` on your desktop
2. Windows runs a tiny script called `noor.vbs` in the background
3. That script starts `main.py` (the whole app) without showing a black terminal window
4. The GUI pops up — dark theme, three columns, animated orb in the middle
5. N.O.O.R starts listening through your microphone immediately
6. It stays in **STANDBY** mode, doing almost nothing, just waiting for you to say the wake word

**Why VBS for the launcher?**
Because if you ran it directly with Python, you'd get an ugly black console window behind the app. The VBS script hides that. It's a Windows quirk.

---

## The Wake Word System

N.O.O.R listens 24/7 in a background thread. The microphone is always on at low sensitivity, just waiting to hear your wake word.

**What counts as a wake word:**

| What you say | Works? |
|---|---|
| "Hey Noor" | Yes — primary |
| "Noor" | Yes |
| "Okay Noor" | Yes |
| "Hello Noor" / "Yo Noor" | Yes |
| "Wake up Noor" / "Noor wake up" | Yes |
| "Hey Nor" / "Hey Nur" / "Hey New" | Yes — STT variants |

**Why so many variations?**

Google's speech recognition sometimes mishears "Noor" as "nor", "nur", "new", or "no". Your accent (Pakistani/Irish mix) means the pronunciation can land differently each time. So instead of one exact wake word, the app checks against a whole list of acceptable variations. If any of them match, it activates.

**What happens after you say the wake word:**

1. Status changes to **LISTENING** (green)
2. You have 7 seconds to say your command
3. N.O.O.R processes it and responds
4. You can keep talking for up to 5 back-and-forth turns without saying the wake word again
5. Say "thanks", "bye", "stop", or "dismiss" to end the session

---

## How N.O.O.R Understands What You Say

The app uses Google's free speech-to-text service. Your voice gets turned into text. Then that text goes into a function called `route()`.

**The route() function is simple but long.** It's basically a giant list of "if you said X, do Y":

```
Did you say "weather"?          → get the weather
Did you say "play [song]"?      → search Spotify
Did you say "add task"?         → add to task list
Did you say "check my email"?   → read Gmail
... (about 60 more checks)
```

Each check is straightforward. The function is ~450 lines but it's not complicated — it's just a lot of rules. Splitting it into smaller functions would actually make it harder to read, because you'd have to jump around the file to understand what's happening.

**What if none of the rules match?**

If your command doesn't match any of the built-in rules, it goes to Claude (the AI) as a general question. Claude reads your personal profile from `noor_knowledge.md` and gives a sharp, one-sentence reply.

---

## The Brain — Claude API

When N.O.O.R can't handle something itself, it sends your message to Claude Haiku via the Anthropic API.

**Why Haiku and not a bigger model like GPT-4 or Claude Sonnet?**

Speed. Haiku is fast — it replies in under a second. For a voice assistant, nothing kills the experience more than waiting 3-4 seconds for a response. Haiku is smart enough for one-sentence answers and casual conversation, which is all that's needed here. Bigger models would be slower and more expensive for no real benefit in this use case.

**How the conversation memory works:**

Every exchange gets stored in a Python list called `history`. The last 20 messages are kept and sent with every new request so Claude remembers what you were just talking about. After 20 messages, the oldest ones get dropped. This prevents the API call from getting too large (and expensive).

---

## Voice Output — edge-tts

When N.O.O.R speaks, it uses a library called `edge-tts`. This uses Microsoft's text-to-speech system that's already built into Windows/Edge — completely free, no API key needed, and the voice quality is genuinely good.

**The voice used:** `en-GB-SoniaNeural` — British female, clear and professional.

**Why not a different voice?**
This was changed from the original male voice (Ryan). Sonia sounds cleaner and more like a real assistant. The pitch is lowered slightly (-4Hz) and speed is bumped up a tiny bit (+4%) to sound more natural.

**The echo problem:**
The biggest technical issue with any voice assistant is that the microphone picks up the speaker's own voice and thinks it's a new command. To prevent this, the app sets a flag called `is_speaking` to True while talking, and mutes the microphone level indicator during that time. The speech recognition threshold is also set manually (not auto-adjusted) so it doesn't recalibrate itself to the room noise from the speaker.

---

## The GUI

Built with `customtkinter`, which is a modern-looking version of Python's built-in Tkinter. Three columns:

```
┌──────────────┬─────────────────────┬──────────────┐
│   TASKS      │    NOOR ORB         │  CALENDAR    │
│              │   (animated dot)    │  (monthly)   │
│  your task   │   ● STANDBY         │              │
│  list here   │                     │  Mon 26 ●    │
│              │   [what you said]   │              │
│  + Add Task  │   [response text]   │              │
│              │   [quick buttons]   │              │
├──────────────┼─────────────────────┼──────────────┤
│   TIMER      │                     │   MAPS       │
│   00:00      │                     │  [search]    │
│ START  RESET │                     │ UCD CITY...  │
└──────────────┴─────────────────────┴──────────────┘
```

- **Left column:** Task list (pulled from `data/tasks.json`), plus a timer
- **Centre:** The orb (changes colour by status), what you said, what N.O.O.R replied, quick-action buttons
- **Right:** Monthly calendar with event dots, maps search

The whole GUI runs on the main thread. All the voice listening, API calls, and TTS happen on separate background threads so the UI never freezes.

---

## Google Calendar and Gmail

N.O.O.R can read your Google Calendar and Gmail. This uses Google's official API.

**How the login works (one-time setup):**

1. You put a file called `google_credentials.json` in the project folder (downloaded from Google Cloud Console)
2. The first time N.O.O.R needs calendar or email access, a browser window opens asking you to log in
3. Once you approve, Google gives N.O.O.R a token that gets saved as `google_token.json`
4. From then on, N.O.O.R uses that saved token — no browser needed again
5. If the token expires, it auto-refreshes silently

**Why is this more complicated than Spotify?**
Google requires OAuth2 for security reasons. You can't just use a simple API key. The token file stores your permission so you don't have to re-approve every time.

**If Google libraries aren't installed:**
The app handles this gracefully — it imports the Google libraries inside a `try/except` block, and if they're not there, calendar/email features are silently disabled while everything else still works.

---

## Spotify

Spotify is controlled via the `spotipy` library, which talks to Spotify's official API.

**What it can do:**
- Play / pause / skip / previous
- Search for a song or artist and play it
- Show what's currently playing
- Like (save) the current song

**How it connects:**
Your Spotify `client_id` and `client_secret` are in `config.py`. The app authenticates and controls Spotify's desktop app directly. Spotify needs to be open and playing for most commands to work — N.O.O.R will try to open it automatically if it's closed.

---

## Health Tracking

All health data is stored in simple JSON files in the `data/` folder:

| File | What's in it |
|---|---|
| `health.json` | Logged meals with macro estimates |
| `workout.json` | Your weekly training split + logged sessions |
| `calories.json` | Daily calorie totals by date |

**Why JSON files and not a database?**

For one person's personal data, a database would be massive overkill. JSON files are simple, readable, and you can open them in Notepad if you ever need to. They're fast enough for this scale. If you were building this for 1000 users, you'd use a database. For just you — JSON is perfect.

**How macros are estimated:**
When you say "I ate chicken and rice", that text gets sent to Claude, which estimates the calories and protein. Not 100% precise, but close enough for tracking purposes.

---

## Tasks

Tasks are stored in `data/tasks.json` as a simple list. When you add or remove a task by voice, the file gets updated immediately and the GUI refreshes to show the change. The task list in the GUI is always in sync with the file.

---

## Difficulties Faced (and How They Were Solved)

### 1. The microphone picking up N.O.O.R's own voice
**Problem:** When N.O.O.R was speaking, the microphone would hear its own TTS output and think it was a new command.

**Fix:** Added an `is_speaking` flag. When set to True, the mic sensitivity indicator goes to zero and speech recognition ignores input. A bit hacky but it works cleanly.

---

### 2. Wake word too strict
**Problem:** "Noor" has to be heard perfectly by Google STT for it to trigger. Your accent plus varying pronunciations meant it missed a lot.

**Fix:** Instead of one exact wake word, a list of 17 variations is checked, including common STT mis-transcriptions like "nor", "nur", "new". If any match, it activates.

---

### 3. UI freezing during API calls
**Problem:** When Claude was processing a response, the whole GUI would freeze until it got an answer (sometimes 1-2 seconds).

**Fix:** All voice handling runs on background threads, completely separate from the GUI thread. The GUI stays responsive while N.O.O.R thinks.

---

### 4. Wrong folder path after rename from Jarvis → N.O.O.R
**Problem:** The VBS launcher still pointed to `C:\Users\tayya\Downloads\Jarvis` — the old folder name. Double-clicking the shortcut gave a "file not found" error.

**Fix:** Updated `noor.vbs` to point to the correct path: `C:\Users\tayya\Downloads\Ai projects\N.O.O.R`.

---

### 5. Google search extracting "google for X" instead of "X"
**Problem:** When you said "search Google for Python tutorial", the app extracted "google for Python tutorial" as the search query instead of just "Python tutorial".

**Fix:** Added "search google for" as the highest-priority prefix to strip. The extractor tries the most specific phrase first before falling back to shorter ones.

---

### 6. History not being trimmed
**Problem:** The conversation history was supposed to be capped at 20 messages to keep API calls fast and cheap. The line `history[-20:]` created a new slice but didn't save it back — so history kept growing forever.

**Fix:** Changed to `history = history[-20:]` — one character added, problem solved.

---

## What Could Be Improved Next

These are not urgent — everything works. But if you ever want to improve it:

1. **Microphone quality** — The #1 issue remaining. A USB microphone with noise cancellation would make a huge difference vs. the built-in laptop mic.

2. **Faster Whisper STT** — `faster-whisper` is already in requirements.txt but not used. Switching from Google STT to a local Whisper model would work offline and be more accurate with your accent.

3. **Morning briefing notification** — Currently you have to ask for the briefing. It could auto-trigger at 8am.

4. **The route() function** — It's 450 lines but works fine. If it ever gets much longer, splitting it into separate files (one for health, one for Spotify, etc.) would help. Not needed yet.

5. **Calorie reset loop** — Currently checks every 60 seconds whether it's 11pm to reset the daily total. A proper scheduler would be cleaner. Very low priority.

---

## Files at a Glance

| File | What it does |
|---|---|
| `main.py` | The whole app — GUI, voice, routing, tools, everything |
| `config.py` | Your API keys (Claude, Spotify, GitHub) |
| `config.example.py` | Template — copy this to make your own config.py |
| `noor_knowledge.md` | Your personal profile loaded into every Claude prompt |
| `noor.vbs` | Silent launcher (no black console window) |
| `launch.bat` | Alternative launcher via terminal |
| `noor.html` | Browser-based dashboard (connects via WebSocket) |
| `requirements.txt` | Python packages to install |
| `README.md` | Full project documentation |
| `test_jarvis.py` | Automated tests for the routing logic |
| `data/tasks.json` | Your task list |
| `data/health.json` | Meal logs |
| `data/workout.json` | Workout split + logs |
| `data/calories.json` | Daily calorie totals |
| `data/notes.txt` | Voice notes |
| `google_credentials.json` | Google API credentials (never share this) |
| `google_token.json` | Saved Google login token (auto-generated) |
