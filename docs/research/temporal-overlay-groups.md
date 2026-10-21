# Temporal groups of graphic occurrences

`script/research/group_overlay_occurrences.py` accepts a completed five-sample-per-second presence report and exterior programme times in seconds. It does not accept reviewed interior cuts, an expected number of breaks, or a channel name.

Occurrences outside the programme are counted separately. An occurrence straddling either exterior bound is retained as unresolved. Inside occurrences are grouped when the gap from the previous graphic end is at most 300 seconds. A group with at least two occurrences and a graphic span of 60–600 seconds is labelled `candidate_temporal_group`. Isolated, short and overlong groups remain explicit. An overlong adjacency chain is marked ambiguous, never silently split to fit the duration bound.

Interior graphic occurrences remain in each group. They are not automatically interpreted as returns to the programme or deleted. Graphic start/end times describe graphic presence; they omit portions of jingles and therefore are not ad-cut coordinates. The duration and gap settings are exploratory priors, not broadcasting regulations, measured probabilities or proof that all intervening content is advertising.

```sh
python3 script/research/group_overlay_occurrences.py \
  --report tmp/example-scan/report.json \
  --programme-start 100 --programme-end 5000 \
  --output tmp/new-temporal-groups.json
```

Output must not already exist. This operation reads the JSON report only; it does not decode video or create or apply a montage. Compatible time coordinates are required. Editor-frame counts divided by nominal FPS are only approximate exterior bounds unless source/editor mapping was separately verified. Such approximate bounds must not settle borderline occurrences or generate trusted source cut indices.

Grouping helps evaluate whether repeated graphics form plausible pause candidates. It does not establish detection precision or recall, and a missing or isolated group does not prove that a programme contains no advertising. Source identity, independent recordings, exact frame mapping and visual boundary validation remain separate concerns.
