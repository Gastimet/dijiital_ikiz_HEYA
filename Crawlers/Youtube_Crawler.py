# pip install git+https://github.com/m-bain/whisperX.git
# pip install torch torchvision torchaudio
# pip install yt-dlp
import whisperx
import gc
import os
import subprocess
from datetime import datetime

# --- Configuration ---
VIDEO_URL = "https://www.youtube.com/watch?v=xf4qieSPIEE"  # Your video URL
DEVICE = "cuda"  # "cuda" for GPU, "cpu" for CPU
AUDIO_FILE = "downloaded_audio.wav"
#YOUR_HF_TOKEN = os.getenv("HF_TOKEN")

# Generate output filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_TXT = f"turkish_transcript_{timestamp}.txt"

# --- 1. Download Audio from YouTube using yt-dlp ---
print("Downloading audio from YouTube using yt-dlp...")
try:
    subprocess.run([
        "yt-dlp",
        "-x", "--audio-format", "wav",
        "-o", AUDIO_FILE,
        VIDEO_URL
    ], check=True)
    print(f"Audio downloaded as {AUDIO_FILE}")
except subprocess.CalledProcessError as e:
    print(f"Error downloading audio with yt-dlp: {e}")
    print("Please ensure yt-dlp is installed and accessible in your environment.")
    exit()

# --- 2. Transcribe with WhisperX - TURKISH OPTIMIZED ---
print("Loading WhisperX model for Turkish transcription...")

# Best models for Turkish (in order of recommendation):
# 1. large-v3-turbo - Best for Turkish (newest model)
# 2. large-v3 - Excellent for Turkish
# 3. distil-large-v3 - Good balance of speed/accuracy

try:
    # Try the best model for Turkish first
    model = whisperx.load_model("base", DEVICE, compute_type="float16")
    print("✓ base model (optimized for Turkish)")
except:
    try:
        model = whisperx.load_model("large-v3", DEVICE, compute_type="float16")
        print("✓ Using large-v3 model (excellent for Turkish)")
    except:
        model = whisperx.load_model("distil-large-v3", DEVICE, compute_type="float16")
        print("✓ Using distil-large-v3 model (fast with good Turkish accuracy)")

audio = whisperx.load_audio(AUDIO_FILE)

# Force Turkish language detection and transcription
result = model.transcribe(audio, batch_size=8, language="tr")

print(f"✓ Transcription completed in Turkish")

# Clean up memory
del model
gc.collect()

# --- 3. Align Transcript - TURKISH ---
print("Aligning Turkish transcript...")
try:
    # Load Turkish alignment model
    model_a, metadata = whisperx.load_align_model(language_code="tr", device=DEVICE)
    result = whisperx.align(result["segments"], model_a, metadata, audio, DEVICE, return_char_alignments=False)
    print("✓ Turkish alignment completed")
except Exception as e:
    print(f"Turkish alignment failed, using original segments: {e}")

# Clean up memory
del model_a
gc.collect()

# --- 4. Speaker Diarization ---
print("Performing speaker diarization...")
try:
    diarize_model = whisperx.DiarizationPipeline(use_auth_token=YOUR_HF_TOKEN, device=DEVICE)
    diarize_segments = diarize_model(audio, min_speakers=1, max_speakers=4)
    result = whisperx.assign_word_speakers(diarize_segments, result)
    print("✓ Diarization completed successfully")
except Exception as e:
    print(f"Diarization failed: {e}")
    print("Continuing without speaker diarization...")
    for segment in result["segments"]:
        segment["speaker"] = "KONUŞMACI_01"

# --- 5. Save Turkish Transcript to TXT File ---
print(f"Saving Turkish transcript to {OUTPUT_TXT}...")

with open(OUTPUT_TXT, 'w', encoding='utf-8') as f:
    # Write header in Turkish
    f.write(f"Video URL: {VIDEO_URL}\n")
    f.write(f"İşlem Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Dil: Türkçe\n")
    f.write("=" * 50 + "\n\n")

    # Write transcript content with Turkish speaker labels
    current_speaker = None
    speaker_line = ""

    for segment in result["segments"]:
        speaker = segment.get('speaker', 'KONUŞMACI_01')

        # Convert English speaker labels to Turkish if needed
        if speaker.startswith('SPEAKER_'):
            speaker_num = speaker.replace('SPEAKER_', '')
            speaker = f"KONUŞMACI_{speaker_num}"

        if speaker != current_speaker:
            if current_speaker is not None and speaker_line.strip():
                f.write(f"{current_speaker}: {speaker_line.strip()}\n\n")
            current_speaker = speaker
            speaker_line = segment.get('text', '').strip()
        else:
            speaker_line += " " + segment.get('text', '').strip()

    # Write the last speaker's content
    if current_speaker is not None and speaker_line.strip():
        f.write(f"{current_speaker}: {speaker_line.strip()}\n")

print(f"✓ Turkish transcript successfully saved to: {OUTPUT_TXT}")

# --- 6. Print Turkish sample to console ---
print("\n--- TÜRKÇE TRANSKRİPT ÖRNEĞİ ---")
with open(OUTPUT_TXT, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')
    # Show the first 10 lines of actual transcript content
    transcript_start = 0
    for i, line in enumerate(lines):
        if line.startswith('KONUŞMACI_') or line.startswith('SPEAKER_'):
            transcript_start = i
            break

    sample_lines = lines[transcript_start:transcript_start + 8]
    for line in sample_lines:
        print(line)

# --- 7. Statistics ---
total_segments = len(result["segments"])
speakers = set()
total_chars = 0

for segment in result["segments"]:
    speaker = segment.get('speaker', 'KONUŞMACI_01')
    if speaker.startswith('SPEAKER_'):
        speaker_num = speaker.replace('SPEAKER_', '')
        speaker = f"KONUŞMACI_{speaker_num}"
    speakers.add(speaker)
    total_chars += len(segment.get('text', ''))

print(f"\n--- İSTATİSTİKLER ---")
print(f"Toplam Bölüm: {total_segments}")
print(f"Konuşmacı Sayısı: {len(speakers)}")
print(f"Toplam Karakter: {total_chars}")
print(f"Tahmini Kelime: {total_chars // 6}")  # Rough estimate for Turkish

# --- 8. Cleanup ---
os.remove(AUDIO_FILE)
print(f"\n✓ Temizlik tamamlandı - geçici ses dosyası silindi")
print(f"✓ Türkçe transkript hazır: {OUTPUT_TXT}")
exit()