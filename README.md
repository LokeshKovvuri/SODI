# 🎥 Random Video Chat (SODI)

> **Connect with strangers around the world for anonymous, peer-to-peer video & text chat — no signup, no data storage, 100% private.**

[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-sodi--86mj.onrender.com-667eea?style=for-the-badge)](https://sodi-86mj.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![WebRTC](https://img.shields.io/badge/WebRTC-P2P-333333?style=flat-square&logo=webrtc&logoColor=white)](https://webrtc.org)
[![License](https://img.shields.io/badge/License-MIT-10b981?style=flat-square)](LICENSE)

---

## 🌐 Live Application

**👉 [https://sodi-86mj.onrender.com](https://sodi-86mj.onrender.com)**

Open it in **two browsers or devices** (mobile + desktop recommended), tap **📞 Start Chatting**, and you'll be randomly matched with a stranger for a live video call! 🎥

> ⚠️ **Note:** The free Render tier sleeps after 15 minutes of inactivity. First load may take ~30–60 seconds to wake up.

---

## 📖 About This Project

**SODI** is a full-featured, production-grade **Omegle-style random video chat application** built with **Python (Flask + Socket.IO)** on the backend and **vanilla JavaScript + WebRTC** on the frontend.

Unlike centralized video platforms, SODI uses **peer-to-peer WebRTC** for video and audio — meaning your video stream flows **directly between browsers**, never through a server. The Python backend only handles **matchmaking** and **signaling** to help two strangers find each other.

The result: **no video is ever recorded, stored, or routed through a middleman**. Privacy by design. 🔒

---

## ✨ Features

### 🎯 Core Functionality
- 🎥 **Peer-to-peer video & audio chat** via WebRTC
- 💬 **Real-time text chat** using RTCDataChannel
- 🔀 **Random stranger matching** with a smart queue system
- 🎯 **Interest-based tags** — Music, Gaming, Movies, Just Chat, English, Hindi, Spanish, French, Arabic
- 🌍 **TURN server integration** — connects reliably on mobile data, college WiFi, and strict networks
- ⏭️ **Next / Skip** button to instantly find a new stranger

### 🛡️ Safety & Moderation
- 🔞 **Age gate (18+)** — confirms user is an adult before entering
- 🚨 **Report system** — flag inappropriate users with 6 categories
- 🚫 **Text filter** — blocks URLs and abusive content automatically
- 🔨 **IP-based ban system** — admin can ban repeat offenders permanently
- 📖 **Safety tips modal** — guidance on avoiding scams and protecting privacy
- 🌫️ **Blur on disconnect** — prevents last-frame flash when stranger leaves

### 👤 User Experience
- 📱 **Fully responsive** — works on mobile, tablet, and desktop
- 🖼️ **Fullscreen stranger video** with draggable self-view PiP
- 🔄 **Camera switch** — flip between front and back camera on mobile
- 🎨 **6 themes** — Purple, Blue, Green, Pink, Orange, Light
- 😊 **Emoji picker** — 56 emojis ready to drop into chat
- 🔊 **Sound notifications** on match and new messages
- 📳 **Haptic feedback** on mobile devices
- ⌨️ **Keyboard shortcuts** — `Space` = mute, `N` = next, `Esc` = end
- ⏱️ **Session timer** — tracks how long you've been chatting
- 🎤 **Speaking indicator** — green glow when your mic detects voice

### 🎥 Advanced Video Controls
- 🔇 **Mute stranger** — silence trolls instantly
- 🪞 **Mirror remote video** — flip stranger's feed horizontally
- 📸 **Screenshot** — capture a frame of the stranger's video
- ⚙️ **Quality selector** — switch between 720p / 480p / 360p
- 🖱️ **Draggable self-view** — move your PiP anywhere on screen

### 📱 Progressive Web App (PWA)
- 📲 **Installable** — "Add to Home Screen" on mobile
- 🔌 **Offline shell** — loads instantly even without internet
- 🎯 **Native app feel** — full-screen, no browser chrome

### 🛠️ Admin Dashboard
Access at `/admin?pw=YOUR_PASSWORD` (password printed in server logs on first start):
- 📊 **Live stats** — online users, waiting queue, active chats, peak online
- 📈 **Hourly connection chart**
- 🎯 **Popular interest tags**
- 🚨 **Recent reports** with chat snippets and reporter IPs
- 🔨 **Ban / unban IPs** with reasons and durations
- ♾️ **Permanent or timed bans**

### 📊 Analytics
- Total connections, matches, sessions, reports
- Average session duration
- Daily active users
- Unique IPs per day
- Public `/stats` endpoint

---

## 🏗️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Backend** | Python 3.11 + Flask 3.0 | Web framework |
| **Real-time** | Flask-SocketIO + Socket.IO | Signaling & matchmaking |
| **Video/Audio** | WebRTC (browser-native) | Peer-to-peer media streaming |
| **Chat** | RTCDataChannel | Text over WebRTC |
| **TURN/STUN** | Metered.ca (free tier) | NAT traversal |
| **Server** | Gunicorn + threading | Production WSGI |
| **Frontend** | Vanilla JS + CSS | No framework, fast load |
| **PWA** | Service Worker + Web Manifest | Installable & offline |
| **Hosting** | Render.com (free tier) | Live deployment |

---

## 📁 Project Structure
sodi/
├── app.py # Flask signaling server + admin API
├── requirements.txt # Python dependencies
├── admin_config.json # Auto-generated admin password
├── bans.json # Persistent IP ban list
├── templates/
│ ├── index.html # Main app (video chat UI)
│ └── admin.html # Admin dashboard
└── static/
├── manifest.json # PWA manifest
├── sw.js # Service worker (offline support)
└── icons/
├── icon-192.png # PWA icon (small)
└── icon-512.png # PWA icon (large)

text

---

## 🚀 Quick Start (Local)

### 1. Clone the repository
```bash
git clone https://github.com/LokeshKovvuri/SODI.git
cd SODI
2. Create and activate a virtual environment
bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
3. Install dependencies
bash
pip install -r requirements.txt
4. Configure TURN servers (optional but recommended)
Get free TURN credentials at metered.ca, then update these two lines in templates/index.html:

javascript
const METERED_APP_NAME = "your-app-name";
const METERED_API_KEY  = "your-api-key-here";
If you skip this step, the app still works using Google's free STUN servers — but connections on mobile data or strict WiFi may fail.

5. Run the server
bash
python app.py
6. Open in your browser
App: http://localhost:5000

Admin: http://localhost:5000/admin?pw=PASSWORD_FROM_LOGS

Test with two browser windows (Chrome + Firefox, or Chrome + Incognito) — click 📞 in both to match.

☁️ Deploy to Production
Deploy on Render.com (Free)
Push your code to GitHub

Sign up at render.com → New → Web Service

Connect your repo and configure:

Runtime: Python 3

Build Command: pip install -r requirements.txt

Start Command: gunicorn -w 1 --threads 100 app:app

Click Deploy — you get an HTTPS URL in ~3 minutes

Check Logs for the auto-generated admin password

💡 Keep it awake: Use UptimeRobot to ping /health every 5 minutes — prevents free-tier sleep.

🔒 Privacy & Data
✅ Video/audio flows P2P — never touches the server

✅ No user accounts, no signup

✅ No database — everything is in-memory

✅ Chat messages are kept only during the session and cleared on disconnect

✅ IP addresses are collected only for ban enforcement and are stored in bans.json

✅ Reports are kept in-memory and cleared on server restart

⚠️ Responsible Use
This app is intended for adults 18+. Random video chat platforms can attract bad actors. If you deploy this publicly, you are responsible for:

Complying with your local laws (some regions require age verification or moderation)

Handling abuse reports promptly (via the admin dashboard)

Blocking repeat offenders using the ban system

Reviewing your hosting provider's terms of service

Never storing personal data you don't need
