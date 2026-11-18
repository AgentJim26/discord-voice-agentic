#!/usr/bin/env python3
"""Persistent local Vosk transcription server.

The model is loaded once. Each request supplies a 16 kHz mono WAV path over a
Unix socket and receives {"text": ...}. This removes the multi-second model
load from every Discord voice segment.
"""
import json
import os
import socket
import sys
import wave

from vosk import KaldiRecognizer, Model, SetLogLevel

SetLogLevel(-1)
MODEL_PATH = "/home/jim/.local/share/vosk/vosk-model-small-en-us-0.15"
SOCKET_PATH = os.path.expanduser("~/.cache/vosk-stt.sock")


def transcribe(path):
    with wave.open(path, "rb") as wf:
        recognizer = KaldiRecognizer(model, wf.getframerate())
        parts = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if recognizer.AcceptWaveform(data):
                text = json.loads(recognizer.Result()).get("text", "").strip()
                if text:
                    parts.append(text)
        text = json.loads(recognizer.FinalResult()).get("text", "").strip()
        if text:
            parts.append(text)
    return " ".join(parts).strip()


def main():
    global model
    model = Model(MODEL_PATH)
    if os.path.exists(SOCKET_PATH):
        os.unlink(SOCKET_PATH)
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(4)
    while True:
        conn, _ = server.accept()
        try:
            data = b""
            while not data.endswith(b"\n"):
                chunk = conn.recv(65536)
                if not chunk:
                    break
                data += chunk
            if not data:
                continue
            request = json.loads(data.decode("utf-8"))
            text = transcribe(request["path"])
            conn.sendall((json.dumps({"text": text}) + "\n").encode("utf-8"))
        except Exception as exc:
            try:
                conn.sendall((json.dumps({"error": str(exc)}) + "\n").encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if os.path.exists(SOCKET_PATH):
                os.unlink(SOCKET_PATH)
        except Exception:
            pass
