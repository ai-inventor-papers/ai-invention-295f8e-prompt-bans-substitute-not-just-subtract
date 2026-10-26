warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
URL: https://arxiv.org/abs/2610.09571
Type: HTML
Length: 8286 chars (truncated)

--- Content ---

Skip to main content

[](https://arxiv.org/IgnoreMe) [ ](https://arxiv.org/) [ Search ](https://arxiv.org/search) [Submit](https://arxiv.org/submit) [Donate](https://info.arxiv.org/about/donate.html) [Log in](https://arxiv.org/login)

Search arXiv

Press Enter to search * [Advanced search](https://arxiv.org/search/advanced)

# Computer Science > Computation and Language

**arXiv:2610.09571** (cs) 

[Submitted on 7 Oct 2026 ([v1](https://arxiv.org/abs/2610.09571v1)), last revised 8 Oct 2026 (this version, v2)]

# Title:How Do LLMs Change Predictions Under Negation?

Authors:[Jongwook Yoon](https://arxiv.org/search/cs?searchtype=author&query=Yoon,+J), [Jongwon Lim](https://arxiv.org/search/cs?searchtype=author&query=Lim,+J), [Sungjib Lim](https://arxiv.org/search/cs?searchtype=author&query=Lim,+S), [Woojin Cho](https://arxiv.org/search/cs?searchtype=author&query=Cho,+W), [Yohan Jo](https://arxiv.org/search/cs?searchtype=author&query=Jo,+Y)

View a PDF of the paper titled How Do LLMs Change Predictions Under Negation?, by Jongwook Yoon and 4 other authors

[View PDF](/pdf/2610.09571) [HTML (experimental)](https://arxiv.org/html/2610.09571v2)

> Abstract:Negation is an essential feature of human language, yet large language models (LLMs) remain unreliable in processing it. We evaluate recent open-source and closed-source LLMs on our negation benchmark and find that, in 37-71% of cases, they repeat the same answer under negation (e.g., "Madrid" for "What is not the capital of Spain?"). To understand and address this brittleness, we mechanistically examine how models operate under negation. Our main finding is that specialized attention heads and MLP neurons jointly implement negation by (1) suppressing retrieval of the original answer (e.g., "Madrid") while (2) promoting a favored candidate within the answer category (e.g., "Paris"). This contrasts with accounts of human negation processing, in which information about the original answer helps to determine what should be excluded. Furthermore, we find that this difference from human processing is a key source of negation failures: the model's mechanism relies on suppressing the original answer rather than using it to determine what to exclude, so the model can repeat the original answer when suppression is too weak or when a bias toward particular answers prevents it from selecting an alternative. To address this weakness in the model's negation mechanism, we propose a training objective that requires larger shifts in answer preference for more confident original predictions, and show that it reduces negation failures with less degradation of general capabilities than standard fine-tuning baselines. Together, our results demonstrate how mechanistic analysis can reveal why a linguistic capability fails and guide training that targets the underlying limitation. 

Comments: | Under Review  
---|---  
Subjects: |  Computation and Language (cs.CL); Artificial Intelligence (cs.AI)  
Cite as: | [arXiv:2610.09571](https://arxiv.org/abs/2610.09571) [cs.CL]  
  | (or  [arXiv:2610.09571v2](https://arxiv.org/abs/2610.09571v2) [cs.CL] for this version)   
  |  <https://doi.org/10.48550/arXiv.2610.09571> Focus to learn more arXiv-issued DOI via DataCite  
  
## Submission history

From: Jongwon Lim [[view email](/show-email/6e509dc6/2610.09571)]   
**[[v1]](/abs/2610.09571v1)** Wed, 7 Oct 2026 07:12:16 UTC (1,480 KB)  
**[v2]** Thu, 8 Oct 2026 14:21:26 UTC (1,482 KB)  


Full-text links:

## Access Paper:
