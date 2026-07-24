"""Research — gathering real facts BEFORE the LLM writes anything.

Born from a production incident: our first real video confidently stated
'RAG stands for Recurrent Attention Graph' (it doesn't) with an invented
statistic. Lesson: a small LLM writing from memory FABRICATES. The cure is
grounding — fetch trusted source material, inject it into prompts, forbid
facts from anywhere else. (This technique is literally called RAG:
Retrieval-Augmented Generation. Our pipeline now implements the concept
it once hallucinated about.)
"""
