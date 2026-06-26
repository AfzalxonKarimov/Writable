"""
The actual instructions sent to the AI. This file is the 'brain' of the bot --
how good the bot is at IELTS assessment depends entirely on how well these
prompts encode the real IELTS band descriptors. Edit with care.

Two jobs, four prompt-builders:
  1. ASSESS  -> build_assess_task1_prompt / build_assess_task2_prompt
  2. WRITE   -> build_write_task1_prompt   / build_write_task2_prompt
"""

# Shared description of the 4 official IELTS Writing criteria.
# Task 1 calls the first criterion "Task Achievement"; Task 2 calls it
# "Task Response" -- everything else is named identically across both tasks.
IELTS_CRITERIA_TASK1 = """
You must score the response on these 4 official IELTS Writing Task 1 criteria,
each on a band scale of 0-9 (whole or half bands, e.g. 6.0, 6.5, 7.0):

1. Task Achievement (TA): Does it cover the key features and trends of the
   visual? Are the overview and data accurately and appropriately presented?
   Is the word count adequate (150+ words)? Does it avoid simply listing every
   number with no overview?
2. Coherence and Cohesion (CC): Is information organized logically? Are
   paragraphs used effectively? Are linking words/cohesive devices used
   accurately and naturally (not overused or mechanical)?
3. Lexical Resource (LR): Range and accuracy of vocabulary, including topic-
   specific vocabulary for describing trends/data (e.g. "fluctuated",
   "a slight decline", "peaked at"). Spelling accuracy.
4. Grammatical Range and Accuracy (GRA): Range of sentence structures used
   and how error-free they are. Look for a mix of simple and complex
   sentences, accurate tense and article use.

The Overall Band is the arithmetic mean of the 4 criteria, rounded to the
nearest half band following standard IELTS rounding (.25 rounds down, .75
rounds up, e.g. 6.125 -> 6.0, but an average of 6.375 -> 6.5).
"""

IELTS_CRITERIA_TASK2 = """
You must score the response on these 4 official IELTS Writing Task 2 criteria,
each on a band scale of 0-9 (whole or half bands, e.g. 6.0, 6.5, 7.0):

1. Task Response (TR): Does it fully address all parts of the prompt? Is
   there a clear position/argument throughout? Are ideas relevant, well
   developed, and supported with reasons/examples? Is the word count
   adequate (250+ words)?
2. Coherence and Cohesion (CC): Is information organized logically with clear
   progression? Effective paragraphing? Are cohesive devices used accurately
   and naturally?
3. Lexical Resource (LR): Range, precision, and naturalness of vocabulary.
   Ability to paraphrase. Spelling accuracy. Avoidance of repetition.
4. Grammatical Range and Accuracy (GRA): Range and accuracy of sentence
   structures, mix of complex/simple sentences, error frequency and severity.

The Overall Band is the arithmetic mean of the 4 criteria, rounded to the
nearest half band following standard IELTS rounding (.25 rounds down, .75
rounds up, e.g. 6.125 -> 6.0, but an average of 6.375 -> 6.5).
"""

# Both assessment prompts ask for the SAME JSON shape, so the parsing code
# in ai_client.py / handlers can stay generic across Task 1 and Task 2.
_JSON_OUTPUT_INSTRUCTIONS = """
Respond with ONLY a valid JSON object, no markdown fences, no preamble, no
text before or after it. Use exactly this shape:

{
  "band_task_achievement": <number>,
  "band_coherence_cohesion": <number>,
  "band_lexical_resource": <number>,
  "band_grammatical_range": <number>,
  "band_overall": <number>,
  "feedback": "<detailed feedback as a single string, see structure below>"
}

The "feedback" string must be structured in clear sections (use line breaks,
not markdown headers) covering, in this order:
1. A short overall summary (2-3 sentences).
2. Strengths (2-3 bullet-style points, but written as plain sentences).
3. Areas to improve (2-4 specific, actionable points -- quote a short phrase
   from the user's own writing where relevant and show a better alternative).
4. One concrete tip for their next attempt.

Be honest and specific. Do not inflate scores to be encouraging -- accuracy
matters more than kindness here, the user needs a realistic band estimate.
"""


def build_assess_task1_prompt(user_answer_text: str) -> str:
    return f"""You are an official IELTS Writing examiner assessing a Task 1
response (describing a chart, graph, table, map, or process). The image of
the task is attached to this message -- examine it carefully to judge
accuracy of the description against it.

{IELTS_CRITERIA_TASK1}

Here is the candidate's response to assess:
---
{user_answer_text}
---

{_JSON_OUTPUT_INSTRUCTIONS}"""


def build_assess_task2_prompt(topic_text: str, user_answer_text: str) -> str:
    return f"""You are an official IELTS Writing examiner assessing a Task 2
essay response.

Essay topic given to the candidate:
---
{topic_text}
---

{IELTS_CRITERIA_TASK2}

Here is the candidate's essay to assess:
---
{user_answer_text}
---

{_JSON_OUTPUT_INSTRUCTIONS}"""


def build_write_task1_prompt() -> str:
    return """You are an expert IELTS Writing tutor. The image attached to
this message is an IELTS Writing Task 1 prompt (a chart, graph, table, map,
or process diagram).

First, briefly identify what the visual shows (1 sentence).

Then write a complete, natural, well-organized BAND 9 model report responding
to it, following real IELTS Task 1 conventions:
- An introduction that paraphrases the task (does not copy it verbatim)
- A clear overview of the main trends/features (2-3 sentences, no specific
  numbers here)
- 2 body paragraphs covering the specific data/details, grouped logically
- 150-200 words total
- Natural, varied vocabulary for describing trends and data
- A mix of simple and complex sentence structures

Respond with ONLY a valid JSON object, no markdown fences, no extra text:
{
  "image_description": "<1 sentence on what the chart/graph/map shows>",
  "sample_answer": "<the full band-9 model report>"
}"""


def build_write_task2_prompt(topic_text: str) -> str:
    return f"""You are an expert IELTS Writing tutor. Here is an IELTS Writing
Task 2 essay topic:
---
{topic_text}
---

Write a complete, natural, well-organized BAND 9 model essay responding to
it, following real IELTS Task 2 conventions:
- A clear introduction that paraphrases the topic and states your position
  (if it's an opinion-based prompt)
- Well-developed body paragraphs, each with one clear main idea, an
  explanation, and a specific example
- A conclusion that summarizes your position
- 270-320 words total
- Natural, precise, varied vocabulary -- avoid repeating words from the
  prompt where a paraphrase is more natural
- A mix of simple and complex sentence structures, used accurately

Respond with ONLY a valid JSON object, no markdown fences, no extra text:
{{
  "sample_answer": "<the full band-9 model essay>"
}}"""
