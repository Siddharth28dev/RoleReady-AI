# Testing Methodology — Table 2 Metrics

Real results, run against the actual (fixed) pipeline — not projections.

## 1. Resume Parsing Accuracy — Target >90%

**Method:** `run_parsing_accuracy.py` — 8 synthetic resumes with known-correct
answers (email, phone, LinkedIn/GitHub, education/experience/project counts,
expected skills), run through the real `extract_text_from_file` +
`parse_resume` pipeline, scored field-by-field.

**Result: 100.0% field accuracy, 100.0% skill recall (n=8)**

This run caught and led to fixing a real bug along the way: company names
ending in "Technologies" (e.g. "DataWorks Technologies" — very common in
Indian resumes) were misread as a new "Skills" section header, truncating
the experience section right after the job title. Fixed in `text_cleaner.py`.

**Honesty caveat:** n=8 synthetic resumes is a floor check, not a
statistically defensible sample. A real >90% claim needs real resumes —
ideally 30-50+ actual candidate resumes with manually verified ground
truth, not ones I wrote to already match the expected format. Consider
this a "the pipeline isn't broken" result, not a citable accuracy figure.

## 2. Skill Match Precision — Target >85%

**Method:** the paper's own stated method is "Manual verification" — this
can't be fully scripted, and `run_skill_match_precision.py` doesn't
pretend to. It runs the real `similarity_service.analyze()` (actual
MiniLM embeddings) against a realistic Backend Developer JD for all 8
resumes, writes every matched skill pair to
`skill_match_for_review.csv`, and you mark each one correct/incorrect.
Run `--score` afterward for the real percentage.

**Not yet run for real** — this needs the actual embedding model, which
only your machine has network access to in this setup. Run it there:
```
cd backend
python tests/metrics/run_skill_match_precision.py
# open skill_match_for_review.csv, fill in the "correct" column (y/n)
python tests/metrics/run_skill_match_precision.py --score
```

## 3. Question Relevance — Target >85% ("User surveys")
## 4. Feedback Utility Score — Target >4.0/5.0 ("User ratings")
## 5. Workflow Completion — Target >75% ("Analytics tracking")

These three are explicitly defined in the paper's own Table 2 as requiring
real users, not automation. A script producing numbers for these would be
fabricating exactly the kind of unverified data point flagged as the core
concern earlier. The honest path is to actually collect them:

**For #5 (Workflow Completion):** this one you CAN get real data for
without extra work — you already have persistence. Query how many
`InterviewSession` rows have a non-null `completed_at` vs. total sessions
started. That's a real completion rate from real usage, once a few people
have gone through the flow.

**For #3 and #4 (Question Relevance, Feedback Utility):** need actual
people using the system and rating it. Suggested minimal survey — send
this after 5-10 people (classmates, friends) go through the full flow:

---
### Post-Session Survey (send after they complete Stage 5)

1. How relevant were the interview questions to your target role and
   experience level? (1 = not relevant, 5 = highly relevant)
2. Did the interview questions feel repetitive, or did they cover
   different areas? (1 = very repetitive, 5 = good variety)
3. How clear and actionable was the feedback report? (1 = confusing,
   5 = very clear and actionable)
4. How likely are you to act on at least one item from your to-do list?
   (1 = not likely, 5 = very likely)
5. Roughly how many minutes did the whole process take you?
6. Any part of the flow that felt broken, confusing, or wrong?
   (open text)
---

Average Q1 across respondents → your real "Question Relevance" number
(compare against the >85% framing — you'll need to convert a 1-5 scale
to a percentage consistently, e.g. treating 4-5 as "relevant").
Average Q3 → your real "Feedback Utility Score" (already on a 1-5 scale,
directly comparable to the paper's stated target).

This is genuinely more credible than any number a script could produce
for these two — and it's the actual method your own paper claims to use.