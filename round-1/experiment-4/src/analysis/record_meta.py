#!/usr/bin/env python3
"""Write logs/hardware.json, results/protocol.json and results/deviations.json (the logged protocol record)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import GRID_C, LAYERS, LOGS_DIR, MODEL_ID, RESULTS_DIR, container_ram_bytes, detect_cpus, read_jsonl  # noqa: E402


def jl(p: Path):
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        gpu = None
    ram = container_ram_bytes()
    (LOGS_DIR / "hardware.json").write_text(json.dumps({"gpu": gpu, "cpus_quota": detect_cpus(),
                                                        "container_ram_gb": round(ram / 1e9, 1) if ram else None}))
    eng = {s: jl(LOGS_DIR / f"vllm_engine_{s}.json") for s in ("s1", "s2", "s3")}
    st = jl(RESULTS_DIR / "steer_state.json") or {}
    protocol = {
        "model": MODEL_ID, "thinking": "off", "prompt": "chat template, no system message, user = segment + blank line + SPEC; R = last token",
        "decoding": {"temperature": 1.0, "top_p": 1.0, "top_k": "disabled", "min_p": 0.0, "repetition_penalty": 1.0,
                     "note": "Qwen3 generation_config defaults (0.6/20/0.95) overridden and asserted"},
        "vllm": {"max_tokens": 1024, "enumerate_max_tokens": 1536, "engines": eng, "seed_rule": "stable_hash(task, condition, paraphrase_id)"},
        "hf": {"max_new_tokens": 768, "batch": "one baseline paraphrase x 10 samples", "seed_rule": "torch.manual_seed(stable_hash(task, paraphrase_id)) for every arm (common random numbers)",
               "dtype": "bfloat16", "attn": "sdpa"},
        "direction": {"frames": "LIST vs IMPLEMENT, 50 + 50 held-out paraphrases", "layers_considered": LAYERS,
                      "selection": "5-fold CV held-out AUC (mean over tasks), ties within 0.005 broken by d'",
                      "injection": "x <- x + c * ||x|| * d_hat at R (prefill) and every generated position, on layers[L-1] output"},
        "grid_c": GRID_C, "c_star_rule": "largest c with pass >= 0.8 x pass(HF c=0), pass rate only",
        "arms": {"vllm": ["baseline N=200", "enumerate N=100", "ban:X_t N=100", "mention:X_t N=100 (E3)", "succession:2 N=100 (E2)"],
                 "hf": ["dc c in {0,0.25,0.5,1,1.5} + bisection, N=100 each", "rand1/rand2 at c*", "placebo at c* (E1)",
                        "breadth at c* (E5)", "cross-task dc transfer at c*, N=50 (E4)"]},
        "labeller": "hidden tests + runtime tracer (3 probes) + AST rules; disagreements -> gemini-2.5-flash-lite judge; gate with gpt-4.1-mini + claude-haiku-4.5 resolver",
        "skipped_extensions": st.get("skipped_extensions", []), "done_extensions": st.get("done_extensions", []),
    }
    (RESULTS_DIR / "protocol.json").write_text(json.dumps(protocol, indent=1))
    devs = [
        {"what": "batch 10 instead of 8", "why": "one batch = one paraphrase so the random-number layout is identical across arms"},
        {"what": "HF c=0 control (hook attached, adds zero)", "why": "engine-matched zero-strength reference for steering arms"},
        {"what": "enumerate max_tokens 1536 (also re-scored as cut at 1024 = 'enumerate@1024')", "why": "lists need room before code"},
        {"what": "paraphrase-cluster bootstrap used for decisions (sample bootstrap reported)", "why": "samples within a paraphrase are correlated"},
        {"what": "rarefied Hill-1 at the common n of each comparison", "why": "plug-in Hill numbers are biased by the number of correct samples"},
        {"what": "layer tie-break by held-out d' plus stage-10 mini-sweep at L*+-4", "why": "held-out AUC saturates at 1.0 on every layer 9-28", "result": st.get("layer_rule")},
        {"what": "pre-registered bisection point per task", "why": "pass(0.25) < 0.8 pass(0) on T1 -> c=0.1; T2 crossing between 0.25 and 0.5 -> 0.375"},
        {"what": "per-task c*", "why": "as pre-registered"},
        {"what": "vLLM started with enforce_eager=True (gpu_memory_utilization 0.95, 8 seqs in s1, 16 in s2/s3)", "why": "torch.compile/inductor fails here: no C compiler; the compiled 0.92 config crashed during start-up"},
        {"what": "model weights read from the run's shared HF cache instead of a workspace hf_cache/", "why": "avoids a duplicate 16 GB copy (shared-cache rule)"},
        {"what": "RLIMIT_AS not set in GPU processes", "why": "the CUDA driver needs large virtual reservations (CUDA OOM at load with RLIMIT_AS=45 GB); CPU processes keep RLIMIT_AS"},
        {"what": "transformers pinned to 4.57.1", "why": "uv resolved 5.x for vllm 0.11.0, which is untested with it"},
        {"what": "labeller revision round 1 (before the gate)", "why": "T2 (dist,node) FIFO items were read as node=dist; Bellman-Ford over adjacency lists and argmin-scan Dijkstra fell to 'other' without the judge; Q2 probe weights scaled x10 so distances never collide with node ids"},
        {"what": "labeller revision round 2 (after the first gate run failed on T2 runtime-vs-adjudicated 0.83)", "why": "SPFA rule now requires a re-enqueued node to be re-processed; runtime Floyd-Warshall rule requires a real triple loop; heap-less array Dijkstra runtime rule; everything re-labelled; gate re-run passed"},
        {"what": "IDDFS reference makes the T1 time limit for two unreachable cases large (26 s, 126 s)", "why": "limit rule max(1 s, 10 x slowest reference median) applied as specified"},
        {"what": "listall frame defined as held-out 'list all approaches, do not implement' paraphrases", "why": "the plan named the set without wording; used as a generalisation check of the commitment coordinate"},
        {"what": "workspace is not a git repository, so forecasts were not git-committed", "why": "sha256 + commit_log.jsonl + generation guard used instead"},
        {"what": "testing-plan check 5 (same per-request seed -> identical vLLM text) FAILED on T1 (T2 identical)", "why": "likely prefix-cache / batch-shape numerics at T=1; vLLM arms are statistically but not bit-for-bit reproducible. Common-random-number analyses (flips, paired specificity) use only HF arms, whose c=0 no-op test is token-identical", "result": jl(RESULTS_DIR / "vllm_determinism.json")},
    ]
    (RESULTS_DIR / "deviations.json").write_text(json.dumps(devs, indent=1))
    print("meta written")


if __name__ == "__main__":
    main()
