# Python base image ကို အသုံးပြုမယ်။
FROM python:3.9-slim-buster

# aria2c နဲ့ yt-dlp ကို install လုပ်မယ်။
# apt update, apt install, rm -rf /var/lib/apt/lists/* ကို တစ်ခါတည်း run ရင် image size သေးမယ်။
RUN apt-get update && \
    apt-get install -y aria2 ffmpeg && \
    pip install yt-dlp && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Working directory ကို သတ်မှတ်မယ်။
WORKDIR /app

# requirements.txt ကို copy လုပ်ပြီး dependencies တွေ install လုပ်မယ်။
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code တွေကို copy လုပ်မယ်။
COPY . .

# Flask app ကို run ဖို့ PORT ကို expose လုပ်မယ်။
EXPOSE 5000

# Gunicorn ကိုအသုံးပြုပြီး Flask app ကို run မယ်။
# Production အတွက် Gunicorn ကိုအသုံးပြုတာ ပိုကောင်းပါတယ်။
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]