PY=$(bash tools/skill_py.sh)   # the aii-web-tools skill interpreter
$PY -I tools/fetch_texts.py --url tc_crosscoders_2024 https://transformer-circuits.pub/2024/crosscoders/index.html
$PY -I tools/fetch_texts.py --url tc_crosscoder_diffing_2025 https://transformer-circuits.pub/2025/crosscoder-diffing-update/index.html
$PY -I tools/fetch_texts.py --url pmlr_hindsight_merging https://proceedings.mlr.press/v286/veselovsky25a.html
$PY -I tools/fetch_texts.py --url pmlr_hindsight_merging_pdf https://raw.githubusercontent.com/mlresearch/v286/main/assets/veselovsky25a/veselovsky25a.pdf
$PY -I tools/fetch_texts.py --url af_kissane_sae_transfer https://www.alignmentforum.org/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models
$PY -I tools/fetch_texts.py --url lw_diff_base_chat https://www.lesswrong.com/posts/xmpauEXEerzYcJKNm/what-we-learned-trying-to-diff-base-and-chat-models-and-why
$PY -I tools/fetch_texts.py --url lw_runtime_steering https://www.lesswrong.com/posts/dvbRv97GpRg5gXKrf/run-time-steering-can-surpass-post-training-reasoning-task
$PY -I tools/fetch_texts.py --url or_HIUqeO9OOr "https://api2.openreview.net/notes?forum=HIUqeO9OOr&limit=5"
$PY -I tools/fetch_texts.py --url acl_nudging https://aclanthology.org/2025.acl-long.623/
$PY -I tools/fetch_texts.py --url acl_lee_findings https://aclanthology.org/2025.findings-emnlp.10/
