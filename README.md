---
title: MoM AI
emoji: ⚡
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# ⚡ MoM AI - Free AI Meeting Assistant & Action Tracker

A 100% free, high-standard AI Meeting Assistant that captures up to **4-hour unrecorded MS Teams meetings**, transcribes speech in real-time, fuses human assistant notes & task matrix assignments, and generates executive Minutes of Meeting (MoM) using **Google Gemini 2.0 Flash** (1,000,000+ token context window).

---

## 🌟 Key Features

- **🎙️ Unrecorded MS Teams Audio Stream Capture**: Capture Teams tab/system audio in real-time using browser Media APIs without requiring Teams recording permissions.
- **📝 Human Assistant Co-Pilot Studio**: Dedicated interface for note-takers to record live notes and explicitly assign action items (`Assignee`, `Department`, `Timeframe / Target Date`, `Priority`).
- **🧠 4-Hour Meeting Intelligence**: Powered by Google AI Studio's Gemini 2.0 Flash (Free API Key), handling up to ~50,000 words / 80k-100k tokens in a single prompt.
- **📊 Premium MoM Executive Dashboard**: Glassmorphic dark UI featuring executive summary, topic-by-topic highlights, binding decisions, and filterable task matrix.
- **📄 Multi-Format Export**: Export report to **DOCX**, **PDF**, or **Markdown** with 1-click.

---

## 🚀 Free API Setup

Get a 100% free Gemini API key from [Google AI Studio](https://aistudio.google.com/).
Enter your API Key in the top-right header of the web application.

---

## 🛠️ Local Development & Running

```bash
git clone https://github.com/SRoy-777/MoM-AI.git
cd MoM-AI
pip install -r requirements.txt
python app.py
```

Open `http://localhost:7860` in Google Chrome or Microsoft Edge.
