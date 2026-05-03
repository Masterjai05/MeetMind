import os
import assemblyai as aai
from dotenv import load_dotenv

load_dotenv()

aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")


def transcribe_audio(filepath: str) -> str:
    """
    Transcribes audio with speaker diarization using AssemblyAI.
    Works on Render (cloud API, no heavy packages).
    Handles any number of speakers.
    Labels as Speaker A, Speaker B, etc.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")

    print(f"[INFO] Uploading to AssemblyAI: {filepath}")

    config = aai.TranscriptionConfig(
        speaker_labels=True,
        speakers_expected=None,
        speech_models=["universal-2"],
    )

    transcriber = aai.Transcriber(config=config)
    transcript  = transcriber.transcribe(filepath)

    if transcript.status == aai.TranscriptStatus.error:
        raise Exception(f"Transcription failed: {transcript.error}")

    print(f"[INFO] Transcription complete. Building speaker-labeled transcript...")
    return _format_transcript(transcript)


def _format_transcript(transcript) -> str:
    """
    Formats transcript with speaker labels.
    Output:
        Speaker A:
          Good morning everyone.
        Speaker B:
          Thanks for joining.
    """
    if not transcript.utterances:
        print("[WARN] No utterances found. Returning plain transcript.")
        return transcript.text or ""

    lines    = []
    last_spk = None

    for utterance in transcript.utterances:
        speaker = f"Speaker {utterance.speaker}"
        text    = utterance.text.strip()

        if not text:
            continue

        if speaker != last_spk:
            lines.append(f"\n{speaker}:")
            last_spk = speaker

        lines.append(f"  {text}")

    result = "\n".join(lines).strip()
    print(f"[INFO] Transcript length: {len(result)} chars")
    return result