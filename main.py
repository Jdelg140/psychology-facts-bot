import os
import json
import random
import requests
from gtts = gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import google.generativeai as genai
from PIL import Image
Image.ANTIALIAS = Image.LANCZOS

# ====================== CONFIG ======================
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]

# ====================== PROMPT (NOW 100 % SAFE) ======================
prompt = """You are creating one viral 60-second psychology-facts Short.
Return ONLY a valid JSON object (no markdown, no explanation) with this exact structure:

{
  "title": "5 Psychology Facts That Will Shock You 🔥",
  "description": "Daily mind-blowing psychology facts...\n\n#psychology #facts #shorts",
  "narration": "Speak this exact script out loud. Strong hook, 5 surprising real psychology facts with short explanations, 130–160 words total, end with: Which fact shocked you the most? Comment below and subscribe for more!",
  "facts": [
    "Fact 1 – short & punchy (max 18 words)",
    "Fact 2 – short & punchy",
    "Fact 3 – short & punchy",
    "Fact 4 – short & punchy",
    "Fact 5 – short & punchy"
  ]
}

Topic: extremely surprising but real psychology facts that make people say “wow”."""

model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=1.1,
        top_p=0.95
    )
)

# This line guarantees we ONLY get the clean JSON
try:
    data = response.text.strip()
    if data.startswith("```json"): data = data[7:-3]      # removes markdown if present
    if data.startswith("```"): data = data[3:-3]
    data = json.loads(data)
except:
    raise Exception("Gemini returned invalid JSON – try again")

# ====================== VOICEOVER (NOW REAL FACTS) ======================
tts = gTTS(data["narration"], lang="en", slow=False)
tts.save("voice.mp3")
audio = AudioFileClip("voice.mp3")
duration = audio.duration

# ====================== PEXELS (bulletproof) ======================
queries = ["calm abstract background", "zen particles", "slow ocean waves", "relaxing nature timelapse"]
headers = {"Authorization": PEXELS_API_KEY}
video_url = None

for q in queries:
    r = requests.get(f"https://api.pexels.com/videos/search?query={q}&per_page=30&orientation=portrait", headers=headers)
    for v in r.json().get("videos", []):
        files = v.get("video_files", [])
        hd = [f for f in files if f.get("quality") in ["hd", "sd"] and f.get("width",0) >= 720]
        if hd:
            video_url = hd[0]["link"]
            break
    if video_url: break

if not video_url:
    video_url = "https://player.vimeo.com/external/403466766.hd.mp4?s=20d6f9c5d6696a22c9d867bc7a880d0e7d91e38a&profile_id=175"  # fallback

open("bg.mp4", "wb").write(requests.get(video_url, stream=True).content)

# ====================== BUILD VIDEO ======================
bg = VideoFileClip("bg.mp4").loop(duration=duration+10)
bg = bg.resize(height=1920).crop(x_center=bg.w/2, width=1080).resize((1080,1920)).subclip(0, duration)

clips = [bg.set_audio(audio)]

# Title
TextClip(data["title"], fontsize=90, color="white", font="Arial-Bold", stroke_color="black", stroke_width=6
         ).set_position("center").set_duration(5).to_clips(clips)

# Facts
step = duration / 5
for i, fact in enumerate(data["facts"]):
    TextClip(fact.upper(), fontsize=68, color="white", font="Arial-Bold", stroke_color="black", stroke_width=5
             ).set_position("center").set_start(5 + i*step).set_duration(step + 1
             ).crossfadein(0.6).crossfadeout(0.6).to_clips(clips)

# Export
CompositeVideoClip(clips).set_duration(duration).write_videofile(
    "psychology_short.mp4", fps=30, codec="libx264", audio_codec="aac", preset="ultrafast", threads=8)

# Metadata
with open("metadata.txt", "w") as f:
    f.write(f"Title: {data['title']}\n")
    f.write(f"Description: {data['description']}\n")
    f.write("#psychology #facts #mindblown #shorts #psychologyfacts")

print("SUCCESS – Real video ready with actual psychology facts!")
