"""Gemma 3 27B on Modal, served by vLLM as an OpenAI-compatible API.

This file is deployed to Modal; it is not imported by the backend. The backend talks to
the deployed URL with plain HTTP (apps/ai/llm_provider.py).

One-time setup (each person who deploys; see apps/ai/README.md §Modal):
    pip install modal==1.6.4 && python3 -m modal setup
    modal secret create huggingface-secret HF_TOKEN=<token with Gemma access>
    modal secret create coach-llm-key VLLM_API_KEY=<long random string>

Deploy / check:
    modal deploy apps/ai/modal_app.py          # prints the https://...modal.run URL
    AI_BASE_URL=<url> AI_API_KEY=<key> modal run apps/ai/modal_app.py   # smoke test

Env read at deploy time: COACH_MODEL, COACH_GPU (defaults below), COACH_MIN_CONTAINERS
(default 0; set 1 during the demo so the model stays warm — a warm GPU is billed every
second it runs).
"""
import json
import os
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.request

import modal

# Defaults: the team's choice. Override at deploy time, e.g. the cheaper fallback:
#   COACH_MODEL=google/gemma-3-12b-it COACH_GPU=L40S modal deploy apps/ai/modal_app.py
MODEL = os.environ.get("COACH_MODEL", "google/gemma-3-27b-it")
SERVED_NAME = "gemma"  # what clients send as "model"
GPU = os.environ.get("COACH_GPU", "H100")  # 27B in bf16 needs ~55 GB weights + KV cache
PORT = 8000
MAX_MODEL_LEN = 16384  # our prompts are a few thousand tokens; keeps KV cache small
MINUTES = 60

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("vllm==0.31.0", "huggingface_hub[hf_transfer]")
    # FlashInfer's sampler JIT-compiles CUDA code at startup and needs nvcc, which the
    # slim image lacks ("Could not find nvcc"); vLLM's built-in sampler needs nothing.
    .env({"HF_HUB_ENABLE_HF_TRANSFER": "1", "VLLM_USE_FLASHINFER_SAMPLER": "0"})
)
# Weights (~55 GB) are downloaded once into a Volume, not on every cold start.
hf_cache = modal.Volume.from_name("coach-hf-cache", create_if_missing=True)
vllm_cache = modal.Volume.from_name("coach-vllm-cache", create_if_missing=True)

app = modal.App("sbank-coach-llm")


@app.function(
    image=image,
    gpu=GPU,
    volumes={"/root/.cache/huggingface": hf_cache, "/root/.cache/vllm": vllm_cache},
    secrets=[modal.Secret.from_name("huggingface-secret"),
             modal.Secret.from_name("coach-llm-key")],
    timeout=20 * MINUTES,
    scaledown_window=10 * MINUTES,
    min_containers=int(os.environ.get("COACH_MIN_CONTAINERS", "0")),
)
@modal.concurrent(max_inputs=16)
@modal.web_server(port=PORT, startup_timeout=20 * MINUTES)
def serve():
    cmd = [
        "vllm", "serve", MODEL,
        "--served-model-name", SERVED_NAME,
        "--host", "0.0.0.0", "--port", str(PORT),
        "--max-model-len", str(MAX_MODEL_LEN),
        "--gpu-memory-utilization", "0.92",
        "--api-key", os.environ["VLLM_API_KEY"],  # requests need "Authorization: Bearer"
    ]
    proc = subprocess.Popen(cmd)

    def watchdog():
        # If vLLM dies (e.g. no access to the gated model), end the container at once
        # instead of idling on a paid GPU until startup_timeout.
        code = proc.wait()
        print("vLLM exited with code %s; stopping the container" % code, flush=True)
        os._exit(1)

    threading.Thread(target=watchdog, daemon=True).start()


@app.function(secrets=[modal.Secret.from_name("huggingface-secret")], timeout=60)
def check_hf_access():
    """CPU-only, costs cents: can our HF token read the gated model? Run before deploying:
        modal run apps/ai/modal_app.py::check_hf_access
    """
    url = "https://huggingface.co/%s/resolve/main/config.json" % MODEL
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["HF_TOKEN"]})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("OK: token can read %s (HTTP %d)" % (MODEL, r.status))
    except urllib.error.HTTPError as e:
        raise SystemExit("NO ACCESS to %s: HTTP %d. Accept the licence on the model page and "
                         "use a token that can read gated repos." % (MODEL, e.code))


@app.local_entrypoint()
def smoke_test():
    """Ask the deployed model one question. Needs AI_BASE_URL and AI_API_KEY locally."""
    base = os.environ.get("AI_BASE_URL") or serve.get_web_url()
    key = os.environ["AI_API_KEY"]
    body = {"model": SERVED_NAME, "max_tokens": 80, "messages": [
        {"role": "user", "content": "Sano yhdellä lauseella, mitä on budjetointi."}]}
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    ctx = ssl.create_default_context()
    if not ctx.cert_store_stats()["x509_ca"] and os.path.exists("/etc/ssl/cert.pem"):
        ctx.load_verify_locations("/etc/ssl/cert.pem")  # python.org macOS builds lack CAs
    # Warm up with GET /health first: Modal answers long-waiting requests with a 303
    # redirect, which GETs can follow but POSTs cannot.
    print("waiting for", base, "(a cold start can take several minutes)")
    t0 = time.time()
    while True:
        try:
            with urllib.request.urlopen(base.rstrip("/") + "/health", timeout=5 * MINUTES,
                                        context=ctx) as r:
                if r.status == 200:
                    break
        except (urllib.error.URLError, TimeoutError) as e:
            if time.time() - t0 > 25 * MINUTES:
                raise SystemExit("model did not come up: %s (see `modal app logs`)" % e)
            time.sleep(10)
    print("up after %.0f s; asking one question" % (time.time() - t0))
    t1 = time.time()
    with urllib.request.urlopen(req, timeout=5 * MINUTES, context=ctx) as r:
        print(json.load(r)["choices"][0]["message"]["content"])
    print("answered in %.1f s (warm)" % (time.time() - t1))
