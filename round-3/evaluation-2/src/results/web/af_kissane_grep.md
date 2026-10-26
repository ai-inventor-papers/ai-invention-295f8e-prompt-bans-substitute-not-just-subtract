warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
URL: https://www.greaterwrong.com/posts/fmwk6qxrpW8d4jvbd/saes-usually-transfer-between-base-and-chat-models
Type: HTML
Pattern: Gemma|fine-tun|BOS (58 matches in 24337 chars)

--- Content ---

1679:...ase-and-chat-models?comments=false&hide-nav-bars=true)

Contents

  * Executive Summary
  * Introduction
  * Investigating SAE Transfer between base and chat models
  * Identifying failures: Outlier norm activations and Gemma v1 2B
  * Investigating SAE Transfer on Instruction Formatted Data
  * Fine-tuning Base SAEs for Chat Models
  * Conclusion
  * Limitations
  * Citing this work
  * Author contributions Statement



 _This is an interim...
--
2333:...odel pairs and find that **SAEs trained on the base model transfer surprisingly well to reconstructing chat activations** (and vice versa) on Mistral-7B and Qwen 1.5 0.5B.
    * We also find that they don’t transfer on [Gemma v1 2B](https://huggingface.co/google/gemma-2b-it), and are generally bad at reconstructing <1% of unusually high norm activations (e.g. BOS tokens) from the opposite model.

  * **We fine-tune our base Mistral-7B SAE (** on 5 million chat activations)**to cheaply obtain an SAE with competitive sparsity and reconstruction fidelity to a chat SAE trained from scratch** (on 800M tokens).

  * **We open source base, chat, and fine-tuned SAEs** (plus wandb runs) for Mistral-7B and Qwen 1.5 0.5B.[1]
    * [Mistral 7B base SAEs](https://wandb.ai/ckkissane/mistral-7B-base/artifacts/model/sae_mistral-7b_blocks.16.hook_resid_pre_131072/v8/files), [Mistral 7B chat SAEs](https://wandb.ai/ckkissane/mistral-7B-chat/artifacts/model/sae_mistral-7b-instruct_blocks.16.hook_resid_pre_131072/v8/files), [Mistral 7B base SAEs fine-tuned on chat](https://wandb.ai/ckkissane/mistral-7B-base-finetuning/artifacts/model/sae_mistral-7b_blocks.16.hook_resid_pre_131072/v1/files)

    * [Qwen 1.5 0.5B base SAEs](https://wandb.ai/ckkissane/qwen-500M-base/artifa...
--
[52 more matches not shown]
