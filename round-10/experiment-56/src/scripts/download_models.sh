#!/usr/bin/env bash
# Download the pinned model revisions into the run's shared HF cache (HF_HUB_CACHE).
set -u
log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*"; }
dl() { log "START $1@$2"; hf download "$1" --revision "$2" --exclude "*.gguf" > /dev/null 2>&1; rc=$?; log "END $1@$2 rc=$rc"; }
dl Qwen/Qwen3-8B b968826d9c46dd6066d109eabc6255188de91218
dl Qwen/Qwen3-8B-Base 49e3418fbbbca6ecbdf9608b4d22e5a407081db4
dl google/gemma-3-4b-it 093f9f388b31de276ce2de164bdc2081324b9767
dl google/gemma-3-4b-pt cc012e0a6d0787b4adcc0fa2c4da74402494554d
log ALLDONE
