import os
import json
import random
import requests
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import google.generativeai as genai

from PIL import Image
Image.ANTIALIAS = Image.LANCZOS
# ====================== CONFIGURATION ======================
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
PEXELS_API_KEY = os.environ["PEXELS_API_KEY"]

# ====================== GENERATE CONTENT WITH GEMINI ======================
prompt = """
You are an expert YouTube Shorts creator in the psychology/self-improvement niche.
Create VIRAL content that gets millions of views.

Output ONLY valid JSON (no markdown, no extra text) with exactly this structure:

{
  "title": "Mind-Blowing Psychology Fact That Will Change How You Think 🔥 #psychology #facts #shorts",
  "description": "This one psychology fact will blow your mind... Subscribe for daily facts!\n\n#psychology #psychologyfacts #mindblown #interestingfacts #didyouknow #selfimprovement #youtubeshorts",
  "narration": "Full spoken script. Write 130–160 words so it lasts ~45–60 seconds when spoken normally. Start with a strong hook, calmly narrate exactly 5 surprising psychology facts with short explanations, end with 'Which fact shocked you the most? Comment below and subscribe for more!'",
  "facts": [
    "Fact 1 – short & punchy for big text overlay (max 20 words)",
    "Fact 2 – short & punchy...",
    "Fact 3 – short & punchy...",
    "Fact 4 – short & punchy...",
    "Fact 5 – short & punchy..."
  ]
}

Topic: Extremely surprising real psychology facts that make people go "wow".
"""

model = genai.GenerativeModel("gemini-2.5-flash")  # Updated to current stable model

response = model.generate_content(
    prompt,
    generation_config=genai.types.GenerationConfig(
        response_mime_type="application/json",
        temperature=1.0,
    )
)

data = json.loads(response.text)
print("Generated JSON:")
print(json.dumps(data, indent=2))

# ====================== CREATE VOICEOVER (gTTS – completely free & unlimited) ======================
tts = gTTS(text=data["narration"], lang="en", slow=False)
tts.save("narration.mp3")

audio_clip = AudioFileClip("narration.mp3")
duration = audio_clip.duration
print(f"Audio duration: {duration:.2f} seconds")

# ====================== DOWNLOAD RANDOM PEXELS BACKGROUND VIDEO ======================
queries = [
    "calm abstract background", "relaxing nature timelapse", "zen particles",
    "peaceful ocean waves", "abstract colors slow", "meditation visual",
    "relaxing clouds", "slow motion nature", "ambient light particles"
]

query = random.choice(queries)
headers = {"Authorization": PEXELS_API_KEY}

params = {
    "query": query,
    "per_page": 30,
    "min_duration": 20
}

resp = requests.get("https://api.pexels.com/videos/search", headers=headers, params=params)
videos = resp.json().get("videos", [])

if not videos:
    raise Exception("No videos found on Pexels – check your API key or query")

video = random.choice(videos)

# Pick highest resolution MP4 link
video_files = [f for f in video["video_files"] if "hd" in f["quality"] or f["width"] >= 1080]
if not video_files:
    video_files = video["video_files"]

video_files.sort(key=lambda x: x["width"] * x["height"], reverse=True)
video_url = video_files[0]["link"]

print(f"Downloading background video: {video_url}")
r = requests.get(video_url, stream=True)
with open("background.mp4", "wb") as f:
    for chunk in r.iter_content(chunk_size=1024 * 1024):
        if chunk:
            f.write(chunk)

# ====================== PROCESS VIDEO ======================
background = VideoFileClip("background.mp4")

# Loop video to cover full duration + buffer
background = background.loop(duration=duration + 15)

# Crop & resize to 1080x1920 (9:16) – works for any orientation
target_w, target_h = 1080, 1920
ratio = target_w / target_h
current_ratio = background.w / background.h

if current_ratio > ratio:  # too wide → crop sides
    new_w = int(background.h * ratio)
    x_center = background.w / 2
    background = background.crop(x_center=x_center, width=new_w)
elif current_ratio < ratio:  # too tall → crop top/bottom
    new_h = int(background.w / ratio)
    y_center = background.h / 2
    background = background.crop(y_center=y_center, height=new_h)

background = background.resize((target_w, target_h))
background = background.subclip(0, duration)  # final cut to audio length

# ====================== ADD TEXT OVERLAYS ======================
clips = []

# Optional big title at start
title_clip = TextClip(data["title"], fontsize=90, color="white", font="Arial-Bold",
                      stroke_color="black", stroke_width=6, size=(1000, None), method="label")
title_clip = title_clip.set_pos("center").set_duration(6).set_start(0).crossfadein(1).crossfadeout(1)
clips.append(title_clip)

# Fact texts
time_per_fact = duration / len(data["facts"])
for i, fact in enumerate(data["facts"]):
    txt = TextClip(fact.upper(), fontsize=68, color="white", font="Arial-Bold",
                   stroke_color="black", stroke_width=5, size=(980, None), method="center")
    txt = txt.set_position("center")
    txt = txt.set_start(i * time_per_fact + 3)  # start facts after title
    txt = txt.set_duration(time_per_fact + 2)  # slight overlap for smooth feel
    txt = txt.crossfadein(0.6).crossfadeout(0.6)
    clips.append(txt)

# Final video assembly
video_with_audio = background.set_audio(audio_clip)
final_video = CompositeVideoClip([video_with_audio] + clips)

# ====================== EXPORT ======================
output_path = "psychology_short.mp4"
final_video.write_videofile(
    output_path,
    fps=30,
    codec="libx264",
    audio_codec="aac",
    threads=8,
    preset="ultrafast",  # fast for GitHub Actions
    bitrate="5000k"
)

# Save metadata for easy upload
with open("metadata.txt", "w") as f:
    f.write(f"Title: {data['title']}\n")
    f.write(f"Description: {data['description']}\n")
    f.write("#psychology #psychologyfacts #mindblown #facts #selfimprovement #interestingfacts #didyouknow #viral #shorts")

print("SUCCESS! psychology_short.mp4 and metadata.txt created.")
print(f"Upload the video with the title/description from metadata.txt")
print("You're all set – run this daily via GitHub Actions → $500+/month passive income machine is live.")
