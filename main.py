import os
import json
import requests
from gtts import gTTS
import pathlib
from moviepy.editor import (
VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, vfx
)
import google.generativeai as genai
from PIL import Image

# Pillow compatibility
Image.ANTIALIAS = Image.LANCZOS

# ====================== CONFIG ======================
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]
# Files
HISTORY_FILE = "used_facts.txt"


# ====================== NEVER REPEAT FACTS ======================
used_facts = []
if pathlib.Path(HISTORY_FILE).exists():
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        used_facts = [line.strip() for line in f if line.strip()]

banned_block = "\n".join([f"• {f}" for f in used_facts[-50:]]) if used_facts else "None yet."

prompt = f"""You are the #1 viral psychology Shorts creator with millions of views.
You have made hundreds of videos and NEVER repeat facts.

Generate 5 BRAND NEW, never-used-before psychology facts that are:
• 100% scientifically real
• Extremely shocking or counter-intuitive
• Max 18 words each

Return ONLY this exact JSON — no markdown, no extra text:

{{
  "title": "Clickbait title using the most shocking fact",
  "description": "These psychology facts will blow your mind! 🔥\\n\\n#psychology #facts #mindblown #shorts",
  "narration": "Strong hook + exactly these 5 new facts with tiny explanations. 100–130 words. End with: Which shocked you most? Comment below!",
  "facts": [
    "Fact 1 – max 18 words",
    "Fact 2 – max 18 words",
    "Fact 3 – max 18 words",
    "Fact 4 – max 18 words",
    "Fact 5 – max 18 words"
  ]
}}

ABSOLUTELY NEVER repeat any of these already-used facts:
{banned_block}
"""

model = genai.GenerativeModel("gemini-2.5-pro-exp-03-25")
response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=1.3,
    ),
)

raw = response.text.strip()
if raw.startswith("```"): raw = raw.strip("` \n")
if raw.lower().startswith("json"): raw = raw[4:].lstrip()

data = json.loads(raw)

# Save new facts to history
with open(HISTORY_FILE, "a", encoding="utf-8") as f:
    for fact in data["facts"]:
        f.write(fact + "\n")

# ====================== VOICEOVER (ElevenLabs) ======================
print("Generating premium voiceover...")
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
audio_stream = client.generate(
    text=data["narration"],
    voice="Rachel",           # change to "Antoni", "Bella", "Josh" if you want
    model="eleven_turbo_v2",
    stream=True
)
with open("voice.mp3", "wb") as f:
    for chunk in audio_stream:
        f.write(chunk)

audio = AudioFileClip("voice.mp3")
duration = audio.duration

# ====================== VOICEOVER ======================
tts = gTTS(data["narration"], lang="en", slow=False)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
duration = audio.duration

# ====================== PEXELS (bulletproof) ======================
queries = [
    "calm abstract background",
    "zen particles",
    "slow ocean waves",
    "relaxing nature timelapse",
]

headers = {"Authorization": PEXELS_API_KEY}
video_url = None

for q in queries:
    r = requests.get(
        "https://api.pexels.com/videos/search",
        params={"query": q, "per_page": 30},
        headers=headers,
        timeout=30,
    )
    r.raise_for_status()
    for v in r.json().get("videos", []):
        files = v.get("video_files", [])
        hd = [f for f in files if f.get("width", 0) >= 720]
        if hd:
            video_url = hd[0]["link"]
            break
    if video_url:
        break

# Fallback video if Pexels fails (public sample)
if not video_url:
    video_url = "https://player.vimeo.com/external/403466766.hd.mp4?s=20d6f9c5d6696a22c9d867bc7a880d0e7d91e38a&profile_id=175"

# Download background video safely
resp = requests.get(video_url, stream=True, timeout=60)
resp.raise_for_status()
with open("bg.mp4", "wb") as f:
    for chunk in resp.iter_content(chunk_size=8192):
        if chunk:
            f.write(chunk)

# ====================== VIDEO (TEXT NEVER GOES OFF-SCREEN) ======================
# ====================== VIDEO (TEXT NEVER GOES OFF-SCREEN) ======================
bg = VideoFileClip("bg.mp4")

# === SMART RESIZE THAT ACTUALLY SHOWS THE VIDEO ===
bg = bg.resize(height=1920)                    # first make it tall
if bg.w > 1080:                                # landscape → crop sides
    bg = bg.crop(x_center=bg.w / 2, width=2000)
else:                                          # portrait or square → add subtle blur bars
    bg = bg.fx(vfx.colorx, 0.9).margin(left=80, right=80, color=(10,10,30)).resize(width=1080)

bg = bg.resize((1080, 1920)).set_fps(30)
bg = bg.loop(duration=duration+10).subclip(0, duration).set_audio(audio)

clips = [bg]

# === Rest of your text clips (unchanged) ===
title = TextClip(
    data["title"].upper(),
    fontsize=74,
    color="white",
    font="DejaVu-Sans-Bold",
    stroke_color="black",
    stroke_width=6,
    size=(950, None),
    method="caption",
    align="center",
).set_position(("center", "top")).set_duration(5).margin(top=120, opacity=0)
clips.append(title)

step = duration / 5
for i, fact in enumerate(data["facts"]):
    fact_clip = TextClip(
        fact.upper(),
        fontsize=60,
        color="white",
        font="DejaVu-Sans-Bold",
        stroke_color="black",
        stroke_width=5,
        size=(980, None),
        method="caption",
        align="center",
    ).set_position("center")\
     .set_start(5 + i * step)\
     .set_duration(step + 1.5)\
     .crossfadein(0.6)
    clips.append(fact_clip)


for i, fact in enumerate(data["facts"]):
    fact_clip = TextClip(
        fact.upper(),
        fontsize=66,
        color="white",
        font="DejaVu-Sans-Bold",
        stroke_color="black",
        stroke_width=5,
        size=(980, None),       # safe width inside 1080
        method="caption",
        align="center",
    ).set_position("center").set_start(5 + i * step).set_duration(step + 1.5
    ).crossfadein(0.6).crossfadeout(0.6)

    clips.append(fact_clip)


# ====================== EXPORT ======================
final = CompositeVideoClip(clips)   # no set_duration here
final.write_videofile(
    "psychology_short.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac",
    preset="ultrafast",
    threads=8,
)

# ====================== METADATA ======================
with open("metadata.txt", "w", encoding="utf-8") as f:
    f.write(f"Title: {data['title']}\n")
    f.write(f"Description: {data['description']}\n")
    f.write("#psychology #facts #mindblown #shorts #psychologyfacts #viral")

print("SUCCESS – Perfect Short created! Text fits 100% on screen.")
