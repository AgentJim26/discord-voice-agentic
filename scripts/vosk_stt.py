#!/usr/bin/env python3
import json
import sys
import wave

from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)
MODEL_PATH = "/home/jim/.local/share/vosk/vosk-model-small-en-us-0.15"


def main() -> None:
    if len(sys.argv) < 2:
        return
    wf = wave.open(sys.argv[1], "rb")
    rec = KaldiRecognizer(Model(MODEL_PATH), wf.getframerate())
    rec.SetWords(False)
    parts = []
    while True:
        data = wf.readframes(4000)
        if not data:
            break
        if rec.AcceptWaveform(data):
            text = json.loads(rec.Result()).get("text", "").strip()
            if text:
                parts.append(text)
    text = json.loads(rec.FinalResult()).get("text", "").strip()
    if text:
        parts.append(text)
    print(" ".join(parts).strip())


if __name__ == "__main__":
    main()
