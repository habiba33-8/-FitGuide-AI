# Evaluation

An AI app is only as good as what you can measure. Run everything with `python -m evals.run_all` from `backend/`.

## 1. Retrieval (does the search find the right document?)
50 questions (English and Egyptian Arabic), each with the document that should answer it.

| Method | hit@1 | hit@3 | MRR |
| --- | --- | --- | --- |
| Word overlap baseline | 0.64 | 0.82 | 0.723 |
| BM25 (used) | 0.92 | 0.94 | 0.93 |

Misses: "how much protein should I eat every day", "I have diabetes can I follow the plan", and one Arabic knee-pain query. These point to missing synonyms and missing documents, which is how you improve it.

**Limit:** the questions and the documents have the same author, so scores are higher than real users would get.

## 2. Food matching
79 food names typed the way people write them. Result 79/79. Same author limit. This only tests name matching, not whether the calories in the table are right.

## 3. Plan constraints
2,880 generated profiles (sex, weight, goal, diet style, allergies, days...). Rules checked: calories within 12% of target, protein at least 80% of target, no allergen, no disliked food, injuries respected.

Pass rate 96.6%. Every failure is protein below 80% of target for vegetarian fat-loss profiles (mostly higher body weights), where vegetarian foods need very large portions to reach the target. We kept the rule strict instead of hiding it.

## 4. Photo calorie accuracy (you run this)
No number is shipped because no one has measured it yet. To measure:

1. Weigh a meal's foods and work out the true calories.
2. Take a photo and put it in `backend/evals/vision_samples/`.
3. Add a row to `manifest.csv`: `filename,true_kcal,description`.
4. Add your API key and run `python -m evals.vision_eval`. Try 20 to 30 meals.

You get: mean absolute error in kcal, mean percent error, share within 20%, and how often the true value falls inside the app's range. `--dry-run` only tests the script and says nothing about accuracy.

## Tests
`pytest` runs 55 tests with a fake model: calculations, data integrity, search, planner, chat flow, API, and the vision eval maths.
