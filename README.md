# F.R.I.D.A.Y. Advanced Assistant

A highly advanced, AI-powered desktop and mobile assistant built with Python and PyQt5. F.R.I.D.A.Y. acts as a central hub for home automation, navigation, space telemetry, real-time object detection via mobile camera, and more.

## Features
- **Neural Link Chat**: Conversational AI powered by multiple language models.
- **Mobile Command Center**: A remote web dashboard hosted over your local network to control F.R.I.D.A.Y. from your phone.
- **Real-Time GPS & Navigation**: Track your phone's location, get turn-by-turn navigation, and estimate traffic automatically.
- **Mobile Vision System**: Capture live frames from your phone and stream them to F.R.I.D.A.Y. for real-time object detection using YOLOv8.
- **Space Telemetry**: Live feeds from NASA's APOD, active orbital launch countdowns, and randomized imagery from the James Webb and Hubble Space Telescopes with deep zooming.
- **System Automation**: Full system control including opening apps, adjusting brightness/volume, taking screenshots, and more.

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/F.R.I.D.A.Y..git
   cd F.R.I.D.A.Y.
   ```

2. **Setup Virtual Environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install Dependencies**
   Ensure you have all the necessary packages.
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**
   Rename `.env.example` to `.env` and fill in your API keys (Cohere, Groq, Twilio, Deepgram, etc.).
   ```bash
   copy .env.example .env
   ```

## Usage

Start the F.R.I.D.A.Y. core system:
```bash
python main.py
```
To access the Mobile Command Center, navigate to the local IP address displayed in your console (e.g., `http://192.168.1.100:5000`) on your smartphone's browser, and enter your `REMOTE_TOKEN` defined in the `.env` file.
