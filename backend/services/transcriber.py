import os
import whisperx
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
DEVICE   = "cpu"
MODEL    = "base"  # options: tiny, base, small, medium, large-v3

print("[INFO] Loading WhisperX model... (first time takes ~30 seconds)")
model = whisperx.load_model(MODEL, device=DEVICE, compute_type="int8")
print("[INFO] WhisperX model loaded.")


def transcribe_audio(filepath: str) -> str:
    """
    Transcribes audio with speaker diarization using WhisperX.
    Returns transcript as a string with speaker labels.
    E.g: "SPEAKER_00: Hello everyone.\nSPEAKER_01: Good morning."
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    print(f"[INFO] Transcribing: {filepath}")

    # Step 1 — Transcribe
    audio  = whisperx.load_audio(filepath)
    result = model.transcribe(audio, batch_size=4)
    print(f"[INFO] Transcription done. Aligning words...")

    # Step 2 — Align for word-level timestamps
    try:
        align_model, metadata = whisperx.load_align_model(
            language_code=result["language"],
            device=DEVICE
        )
        result = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            DEVICE,
            return_char_alignments=False
        )
        print("[INFO] Alignment done. Running diarization...")
    except Exception as e:
        print(f"[WARN] Alignment failed: {e}. Skipping alignment.")

    # Step 3 — Diarize (identify speakers)
    try:
        diarize_model  = whisperx.DiarizationPipeline(
            use_auth_token=HF_TOKEN,
            device=DEVICE
        )
        diarize_result = diarize_model(audio)
        result         = whisperx.assign_word_speakers(diarize_result, result)
        print("[INFO] Diarization complete.")
        return _format_with_speakers(result["segments"])

    except Exception as e:
        print(f"[WARN] Diarization failed: {e}. Falling back to plain transcript.")
        return _format_plain(result["segments"])


def _format_with_speakers(segments: list) -> str:
    """Formats segments into readable speaker-labeled transcript."""
    lines      = []
    last_spk   = None

    for seg in segments:
        speaker = seg.get("speaker", "SPEAKER_00")
        text    = seg.get("text", "").strip()

        if not text:
            continue

        # Only print speaker label when speaker changes
        if speaker != last_spk:
            lines.append(f"\n{speaker}:")
            last_spk = speaker

        lines.append(f"  {text}")

    transcript = "\n".join(lines).strip()
    print(f"[INFO] Transcript length: {len(transcript)} characters")
    return transcript


def _format_plain(segments: list) -> str:
    """Fallback — no speaker labels, just plain text."""
    transcript = " ".join(
        seg.get("text", "").strip()
        for seg in segments
        if seg.get("text", "").strip()
    )
    print(f"[INFO] Transcript length: {len(transcript)} characters")
    return transcript