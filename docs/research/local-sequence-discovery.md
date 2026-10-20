# Local repetition discovery pilot

`script/research/discover_local_sequences.py` is an offline research command. It reads a completed, SHA-256-sealed discovery cache and searches a fixed grid of twelve 8×6 RGB regions in the 32×18 samples. It never reads the original recording or accepts reference cuts or a channel template.

```sh
python3 script/research/discover_local_sequences.py \
  --cache tmp/example-cache \
  --output tmp/local-discovery.json
```

The output must not already exist. The command verifies the cache size and seal before searching, then rechecks its hash and manifest afterwards. Progress reports the region being searched; it is not an estimate of remaining time.

Two-second windows must have local contrast and motion. Standardized temporal/spatial RGB descriptors shortlist comparisons through a deterministic approximate index. Verified matches require normalized correlation of at least 0.8, followed by correlation of at least 0.6 after subtracting each pixel’s temporal mean. This second check rejects similarity dominated by an otherwise static spatial layout. These are exploratory fixed thresholds, not measured accuracy guarantees. Every family contains at least three separated occurrences that directly match its anchor; transitive chains do not establish family membership. Correlation distances in this report are not RGB RMSE values or calibrated probabilities.

The default budget is 100,000 comparisons and 64 retained entries per bucket **per region**. Pair and bucket saturation are reported separately for every region. The fixed grid, approximate indexing, sampling phase and budgets can all miss relevant motifs. A region may contain shared text or graphics while the surrounding images differ. Repeated advertising, film scenes and graphics can also match.

This pilot produces no separator classification, departure/resume roles, cut coordinates, montage or queue operation. Times use the resampled five-frame-per-second timeline, whose alignment with editor coordinates is not guaranteed. Human reference cuts may be used in a separate evaluation after discovery, never to select discovery regions or accept a match. A successful synthetic test or a reference-selected comparison does not establish accuracy on independent recordings.

The UI and existing detector defaults remain unchanged. This command is for evaluating whether blind local matches provide useful evidence before considering any application integration.
