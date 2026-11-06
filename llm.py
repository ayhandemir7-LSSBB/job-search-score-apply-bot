"""OpenAI calls with Structured Outputs: every response is parsed into a Pydantic model."""
import time
from functools import lru_cache

import config

CALLS = []  # one entry per call: model, schema, tokens, seconds (shown in the lab proof)


def available():
    return bool(config.OPENAI_API_KEY)


@lru_cache(None)
def client():
    from openai import OpenAI
    return OpenAI(api_key=config.OPENAI_API_KEY, timeout=180)


def parse(model, system, user, schema, effort=None):
    kwargs = {"reasoning_effort": effort} if effort and model.startswith(("gpt-5", "o")) else {}
    start = time.time()
    resp = client().chat.completions.parse(
        model=model, response_format=schema,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}], **kwargs)
    msg = resp.choices[0].message
    if msg.refusal or msg.parsed is None:
        raise RuntimeError(f"model returned no parsed output: {msg.refusal or resp.choices[0].finish_reason}")
    CALLS.append({"model": model, "schema": schema.__name__, "input_tokens": resp.usage.prompt_tokens,
                  "output_tokens": resp.usage.completion_tokens, "seconds": round(time.time() - start, 1)})
    return msg.parsed
