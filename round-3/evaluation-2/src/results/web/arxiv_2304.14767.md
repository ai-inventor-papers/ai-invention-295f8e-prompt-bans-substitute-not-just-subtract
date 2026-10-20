warning: The `fitz` API is deprecated and will be removed in future. Use `import pymupdf` instead.
URL: https://arxiv.org/abs/2304.14767
Type: HTML
Length: 8156 chars (truncated)

--- Content ---

Skip to main content

[](https://arxiv.org/IgnoreMe) [ ](https://arxiv.org/) [ Search ](https://arxiv.org/search) [Submit](https://arxiv.org/submit) [Donate](https://info.arxiv.org/about/donate.html) [Log in](https://arxiv.org/login)

Search arXiv

Press Enter to search * [Advanced search](https://arxiv.org/search/advanced)

# Computer Science > Computation and Language

**arXiv:2304.14767** (cs) 

[Submitted on 28 Apr 2023 ([v1](https://arxiv.org/abs/2304.14767v1)), last revised 13 Oct 2023 (this version, v3)]

# Title:Dissecting Recall of Factual Associations in Auto-Regressive Language Models

Authors:[Mor Geva](https://arxiv.org/search/cs?searchtype=author&query=Geva,+M), [Jasmijn Bastings](https://arxiv.org/search/cs?searchtype=author&query=Bastings,+J), [Katja Filippova](https://arxiv.org/search/cs?searchtype=author&query=Filippova,+K), [Amir Globerson](https://arxiv.org/search/cs?searchtype=author&query=Globerson,+A)

View a PDF of the paper titled Dissecting Recall of Factual Associations in Auto-Regressive Language Models, by Mor Geva and 3 other authors

[View PDF](/pdf/2304.14767) [HTML (experimental)](https://arxiv.org/html/2304.14767v3)

> Abstract:Transformer-based language models (LMs) are known to capture factual knowledge in their parameters. While previous work looked into where factual associations are stored, only little is known about how they are retrieved internally during inference. We investigate this question through the lens of information flow. Given a subject-relation query, we study how the model aggregates information about the subject and relation to predict the correct attribute. With interventions on attention edges, we first identify two critical points where information propagates to the prediction: one from the relation positions followed by another from the subject positions. Next, by analyzing the information at these points, we unveil a three-step internal mechanism for attribute extraction. First, the representation at the last-subject position goes through an enrichment process, driven by the early MLP sublayers, to encode many subject-related attributes. Second, information from the relation propagates to the prediction. Third, the prediction representation "queries" the enriched subject to extract the attribute. Perhaps surprisingly, this extraction is typically done via attention heads, which often encode subject-attribute mappings in their parameters. Overall, our findings introduce a comprehensive view of how factual associations are stored and extracted internally in LMs, facilitating future research on knowledge localization and editing. 

Comments: | Accepted at EMNLP 2023  
---|---  
Subjects: |  Computation and Language (cs.CL)  
Cite as: | [arXiv:2304.14767](https://arxiv.org/abs/2304.14767) [cs.CL]  
  | (or  [arXiv:2304.14767v3](https://arxiv.org/abs/2304.14767v3) [cs.CL] for this version)   
  |  <https://doi.org/10.48550/arXiv.2304.14767> Focus to learn more arXiv-issued DOI via DataCite  
  
## Submission history

From: Mor Geva [[view email](/show-email/024a1110/2304.14767)]   
**[[v1]](/abs/2304.14767v1)** Fri, 28 Apr 2023 11:26:17 UTC (7,482 KB)  
**[[v2]](/abs/2304.14767v2)** Wed, 11 Oct 2023 09:49:59 UTC (7,572 KB)  
**[v3]** Fri, 13 Oct 2023 19:01:20 UTC (7,570 KB)  


Full-text links:

## Access Paper:

View a PDF of the paper titled Dissecting Recall of Factual Associations in Auto-Regressive Language Models, by Mor Geva and 3 other authors

  * [View PDF](/pdf/2304.14767
