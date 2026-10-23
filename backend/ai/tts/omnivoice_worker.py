"""One-shot OmniVoice child process entrypoint; run only in .venv-omnivoice."""

from __future__ import annotations

import json
import sys
import traceback


def main() -> int:
    try:
        request = json.load(sys.stdin)
        import soundfile as sf
        import torch
        from omnivoice import OmniVoice

        model = OmniVoice.from_pretrained(
            request["model_path"], device_map="cuda:0", dtype=torch.float16,
        )
        audio = model.generate(
            text=request["text"], instruct=request["instruct"], speed=request["speed"],
        )
        if not audio or audio[0] is None:
            raise RuntimeError("The model returned empty audio")
        sf.write(request["output_path"], audio[0], 24000, format="WAV", subtype="PCM_16")
        print(json.dumps({"ok": True}))
        return 0
    except Exception as exc:
        # Keep machine-readable output free of the input text and traceback.
        print(json.dumps({"ok": False, "error": type(exc).__name__}))
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
