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

# ====================== GEMINI ======================
prompt = """
Output ONLY valid JSON:
{
  "title": "5 Mind-Blowing Psychology Facts 🔥",
  "description": "Daily psychology facts that will blow your mind!\n\n#psychology #facts #shorts #mindblown",
  "narration": "Strong hook. 5 real surprising psychology facts. 130–160 words. End with: Which shocked you most? Comment & subscribe!",
  "facts": ["Fact 1 (max 18 words)", "Fact 2", "Fact 3", "Fact 4", "Fact 5"]
}
"""

model = genai.GenerativeModel("gemini-2.5-flash")
response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json", "temperature": 1.0})
data = json.loads(response.text)

# ====================== VOICE ======================
tts = gTTS(data["narration"], lang="en", slow=False)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
duration = audio.duration

# ====================== PEXELS – ROBUST VERSION ======================
queries = ["calm abstract background", "relaxing nature timelapse", "zen particles", "slow ocean waves", "ambient lights"]
headers = {"Authorization": PEXELS_API_KEY}

video_url = None
for query in queries:
    resp = requests.get(f"https://api.pexels.com/videos/search?query={query}&per_page=30&orientation=portrait", headers=headers)
    videos = resp.json().get("videos", [])
    random.shuffle(videos)
    for video in videos:
        files = video.get("video_files", [])
        if not files:
            continue
        hd_files = [f for f in files if f.get("quality") == "hd" or f.get("width", 0) >= 1080]
        if hd_files:
            video_url = hd_files[0]["link"]
            break
    if video_url:
        break

if not video_url:
    raise Exception("No suitable video found on Pexels after trying multiple queries")

print(f"Downloading background: {video_url}")
open("bg.mp4", "wb").write(requests.get(video_url, stream=True).content)

# ====================== VIDEO PROCESSING ======================
bg = VideoFileClip("bg.mp4").loop(duration=duration+10)
bg = bg.resize(height=1920).crop(x1=(bg.w-1080)/2).resize((1080,1920)).subclip(0, duration)

clips = [bg.set_audio(audio)]

# Title
title = TextClip(data["title"], fontsize=85, color="white", font="Arial-Bold", stroke_color="black", stroke_width=6)
title = title.set_pos("center").set_duration(5)
clips.append(title)

# Facts
for i, fact in enumerate(data["facts"]):
    txt = TextClip(fact.upper(), fontsize=68, color="white", font="Arial-Bold", stroke_color="black", stroke_width=5)
    txt = txt.set_pos("center").set_start(5 + i*(duration/5)).set_duration(duration/5 + 2)
    txt = txt.crossfadein(0.6).crossfadeout(0.6)
    clips.append(txt)

# Export
final = CompositeVideoClip(clips).set_duration(duration)
final.write_videofile("psychology_short.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", threads=8)

# Metadata
with open("metadata.txt", "w") as f:
    f.write(f"Title: {data['title']}\n")
    f.write(f"Description: {data['description']}\n")
    f.write("#psychology #facts #mindblown #shorts #viral")

print("SUCCESS! Video ready → psychology_short.mp4")
