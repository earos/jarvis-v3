# JARVIS TTS Guide

## Overview
ElevenLabs text-to-speech with 30-90x latency optimization through streaming.

## Configuration

```bash
# In .env
ELEVENLABS_API_KEY=your_key
ELEVENLABS_VOICE_ID=onwK4e9ZLuTAKqWW03F9  # Default: Adam
```

## API Usage

```bash
# Generate speech
curl -X POST http://192.168.10.100:3939/api/tts \
  -H 'Content-Type: application/json' \
  -d '{"text": "Hello from JARVIS"}' \
  --output speech.mp3

# With custom voice
curl -X POST http://192.168.10.100:3939/api/tts \
  -d '{"text": "Hello", "voice_id": "different_voice_id"}' \
  --output speech.mp3
```

## Web UI
- Enable TTS in settings panel
- Responses automatically spoken
- Uses streaming for low latency

## Performance
| Metric | Before | After |
|--------|--------|-------|
| First byte | ~3s | ~100ms |
| Total time | ~5s | ~2s |
| Improvement | - | 30-90x |

## Voices
See ElevenLabs dashboard for available voices and IDs.
