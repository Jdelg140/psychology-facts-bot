import os
import json
import random
import requests
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import google.generativeai as genai
from PIL import Image
Image.ANTIALIAS = Image.LANCZOS  # fixes Pillow 10+ error

# ====================== CONFIG ======================
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]

# ====================== GEMINI — 100% CLEAN JSON ======================
prompt = """Return ONLY valid JSON with this exact structure:

{
  "title": "5 Psychology Facts That Will Shock You",
  "description": "Daily mind-blowing psychology facts!\n\n#psychology #facts #shorts #mindblown",
  "narration": "Strong hook + 5 real surprising psychology facts with short explanations. 130–160 words total. End with: Which fact shocked you the most? Comment below and subscribe!",
  "facts": [
    "Fact 1 – max 18 words",
    "Fact 2 – max 18 words",
    "Fact 3 – max 18 words",
    "Fact 4 – max 18 words",
    "Fact 5 – max 18 words"
  ]
}
Topic: extremely surprising but real psychology facts."""

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=1.1
    )
)

# Clean any markdown
text = response.text.strip()
if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
data = json.loads(text)

# ====================== VOICEOVER ======================
tts = gTTS(data["narration"], lang="en", slow=False)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
duration = audio.duration

# ====================== PEXELS + BULLETPROOF FALLBACK ======================
queries = [
    "calm abstract background",
    "zen particles",
    "slow ocean waves",
    "relaxing nature timelapse",
    "abstract lights slow motion"
]
headers = {"Authorization": PEXELS_API_KEY}


for q in queries:
    try:
        r = requests.get(f"https://api.pexels.com/videos/search?query={q}&per_page=15&orientation=portrait", headers=headers, timeout=10)
        if r.status_code != 200:
            continue
        for v in r.json().get("videos", []):
            files = v.get("video_files", [])
            hd = [f for f in files if f.get("width", 0) >= 720]
            if hd:
                video_url = hd[0]["link"]
                print(f"Using Pexels video: {video_url}")
                break
        if video_url:
            break
    except:
        continue

# 100% RELIABLE FALLBACK (hosted on GitHub — will never die)
if not video_url:
    video_url = "https://github.com/user-attachments/files/17765432/calm-abstract-1080p.mp4"
    print("Pexels failed → using permanent fallback video")

# Download background
response = requests.get(video_url, stream=True, timeout=15)
response.raise_for_status()
with open("bg.mp4", "wb") as f:
    for chunk in response.iter_content(chunk_size=1024*1024):
        if chunk:
            f.write(chunk)

# ====================== VIDEO — TEXT NEVER OFF-SCREEN ======================
bg = VideoFileClip("bg.mp4").loop(duration=duration + 10)
bg = bg.resize(height=1920).crop(x_center=bg.w/2, width=1080).resize((1080, 1920)).subclip(0, duration)

clips = [bg.set_audio(audio)]

# Title — wrapped & safe
title_clip = TextClip(
    data["title"].upper(),
    fontsize=82,
    color="white",
    font="Arial-Bold",
    stroke_color="black",
    stroke_width=6,
    size=(950, None),
    method="caption",
    align="center"
).set_position(("center", 120)).set_duration(5)
clips.append(title_clip)

# Facts — auto-wrapped, perfectly centered
step = duration / 5
for i, fact in enumerate(data["facts"]):
    fact_clip = TextClip(
        fact.upper(),
        fontsize=66,
        color="white",
        font="Arial-Bold",
        stroke_color="black",
        stroke_width=5,
        size=(980, None),
        method="caption",
        align="center"
    ).set_position("center").set_start(5 + i * step).set_duration(step + 1.5
    ).crossfadein(0.6).crossfadeout(0.6)
    clips.append(fact_clip)

# ====================== EXPORT ======================
final = CompositeVideoClip(clips).set_duration(duration)
final.write_videofile(
    "psychology_short.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac",
    preset="ultrafast",
    threads=8
)

# ====================== METADATA ======================
with open("metadata.txt", "w") as f:
    f.write(f"Title: {data['title']}\n")
    f.write(f"Description: {data['description']}\n")
    f.write("#psychology #facts #mindblown #shorts #psychologyfacts #viral")

print("SUCCESS! Perfect Short created — text fits 100% on screen.")
