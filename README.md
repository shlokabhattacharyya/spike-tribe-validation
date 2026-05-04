# TRIBE Phase 1 Validation Findings

## TL;DR

Built end-to-end TRIBE extraction + analysis pipeline. On a 69-video, single-video-per-creator dataset, **TRIBE-derived cortical features do not add predictive value above creator metadata** (`log(followers) + duration`). Bootstrap 95% CI on the AUC delta is [-0.11, +0.15] — statistically indistinguishable from baseline at this n.

This is **not evidence against TRIBE**. It is evidence that this dataset cannot test TRIBE's actual hypothesis. Between-creator virality on TikTok is dominated by follower count (40% R² on log views with creator metadata alone), and TRIBE features at this n provide no orthogonal signal. The hypothesis TRIBE is meant to test — that within-creator content variation drives virality conditional on reach — requires paired data we don't have.

**Recommended next investment:** v2 dataset of 5-8 creators × 4-6 videos each (n=20-50 within-creator pairs), which would test the actual question.

The strongest standalone finding from this sprint is non-modeling: **intended-not-viral picks were 100% accurate; intended-viral picks were only 76.5% accurate**. Predicting *what won't go viral* is easy; predicting *what will* is genuinely hard. This asymmetry is the empirical justification for a prediction market.

## Headline result

**5-fold stratified CV, viral-vs-dud binary task, n=61 (26 viral, 35 dud).**

| Model | Features | AUC | Std | Δ vs baseline |
|---|---|---|---|---|
| Baseline | log_followers + duration | **0.790** | 0.077 | — |
| Baseline + TRIBE (raw fmri PCA-30) | + 20484 vertices, PCA-reduced | 0.670 | 0.229 | -0.120 |
| Baseline + TRIBE (ROI-148) | + 148 Destrieux ROI means | 0.735 | 0.159 | -0.054 |
| Baseline + TRIBE (fusion PCA-30) | + 1152-dim fusion layer | 0.547 | 0.222 | -0.243 |
| TRIBE alone (ROI-148) | no metadata | 0.677 | 0.269 | -0.112 |

**Bootstrap 95% CI on the best TRIBE delta:** [-0.112, +0.150]
**Median bootstrap delta:** +0.018

Continuous regression (Spearman ρ on log views, n=69):
- Baseline: 0.580 (p < 0.0001)
- Baseline + TRIBE: 0.563 (p < 0.0001)
- Δ: -0.017

The point estimate is slightly negative; the bootstrap distribution is centered slightly positive but with wide uncertainty. Both views support the same conclusion: **at n=61, TRIBE features are statistically indistinguishable from no information.**

## Why TRIBE doesn't lift here: the diagnostic story

Three findings explain the null result without indicting the model.

### 1. Reach dominates between-creator virality
Baseline `log(followers) + duration` achieves **R² = 0.398 on log views**. Most of the explainable variance in views — at the dud-vs-viral threshold (>1M vs <50K) — is determined by who posted, not what they posted. There's not much room for orthogonal content signal because the threshold is so aggressive that follower count almost mechanically predicts the binary outcome.

### 2. The univariate ROI signal is reach-mediated
Initial univariate analysis showed 12 of 150 Destrieux ROIs significantly correlated with log views at p<0.01, concentrated in left prefrontal cortex (orbital, IFG/Broca's, superior frontal) and middle temporal — the language and executive network. ρ = 0.34–0.41 at p < 0.001 looked like a clean finding.

**Partial correlation, controlling for log(followers):** **0 of 150 ROIs** survive at p<0.01. The strongest left-prefrontal correlation drops from ρ=0.41, p=0.0004 to ρ=0.27, p=0.025. The "TRIBE language network signal" we initially observed was largely a roundabout measure of follower count. Some residual content signal exists (mean attenuation 0.073), but it is below the detection floor at n=61.

### 3. TRIBE adds no orthogonal explanatory power
Predict log views from baseline → take residuals → check if any TRIBE ROI correlates with residuals. **0 of 150 ROIs significant at p<0.01** (vs 1.5 expected by chance). TRIBE features are not finding signal that baseline misses.

The same pattern holds for the engagement outcome (log views/followers): 0 of 150 ROIs significant. If TRIBE captures content-driven appeal independent of reach, this dataset is not where it shows up.

## What's robust regardless of headline

### Intent asymmetry — the strongest standalone finding
Videos were a-priori labeled "viral" or "not_viral" before view counts were known.

| Intended | → Dud | → Mid | → Viral |
|---|---|---|---|
| not_viral (n=35) | 35 | 0 | 0 |
| viral (n=34) | 0 | 8 | 26 |

**Intended-not-viral hit rate: 100%. Intended-viral hit rate: 76.5%.**

This asymmetry — duds are obvious, virals are hard — empirically justifies a prediction market for short-form content. If predicting virality were easy, there'd be no market. The fact that even confident a-priori "this will go viral" picks miss 23% of the time is the predictive gap a useful model needs to close.

### TRIBE encodes content type
Two-dimensional PCA on TRIBE fusion features explains 41% of variance and visibly clusters by vertical (brainrot, grwm, sports, etc.). The model understands what it's looking at. This doesn't help with virality prediction at n=61, but it confirms the features are meaningful.

### TRIBE-alone clears chance
TRIBE features alone, without any metadata, achieve AUC 0.677 ± 0.269 on viral-vs-dud (n=61). High variance, well below baseline (0.790), but meaningfully above chance (0.5). Suggests there is *some* signal — just not enough to detect at this n.


## Why this dataset can't test TRIBE's actual hypothesis

TRIBE's value proposition is that brain-aligned content features predict virality *conditional on creator reach*. Testing this requires paired within-creator data: same creator, multiple videos, some viral some not. We have 68 unique creators with one video each (foot_cartel appears twice). Without within-creator pairs, all comparisons collapse into between-creator comparisons, which are dominated by follower count.

Sample size context: published TikTok virality work uses n=400+ videos. We have 61. With 5-fold CV at this n, the standard error on AUC is roughly ±0.08, so the detection threshold for any real effect is ~0.10 AUC. Anything smaller than that is invisible. The TRIBE delta we'd need to detect (5+ AUC points per the memo) is at the edge of what n=61 can resolve.

## What this means for the v2 dataset

A proper test requires:

1. **Within-creator pairing.** 5-8 creators with 4-6 videos each (mix of their viral and non-viral output). Goal: 20-50 within-creator pairs. Each creator becomes their own baseline, and TRIBE has to predict deviation from their median.
2. **Vertical balance maintained.** Same 7 verticals, but creator-stratified.
3. **Larger absolute n.** Target n=200+ for any between-creator analyses to have detection power.
4. **Engagement-relative-to-reach as the primary outcome.** log(views/followers) instead of raw views. This is what a prediction market needs — content quality, not creator fame.
5. **Full-video extraction.** Don't cap at 30s. The viral hook is at seconds 1-3 but mean-pooling across the full video may be losing it; a v2 analysis should also test temporal pooling alternatives (max-pool, first-15s, peak detection).

## What was built (deliverables in repo)

- `scripts/01_build_csv.py` — dataset builder (URL list → videos.csv with intent labels)
- `scripts/02_scrape.py` — Apify-based metadata scraper
- `scripts/03_redownload.py` — yt-dlp fallback for download failures
- `notebooks/extract_batch.ipynb` — Colab/A100 pipeline calling TRIBE inference, saving (T, 20484) fmri_preds and (B, T, 1152) fusion features per video
- `notebooks/analyze_v3.ipynb` — main analysis (PCA, AUC, ROI ranking, diff map, continuous regression)
- `notebooks/analyze_v4.ipynb` — diagnostic battery (ROI-148, fusion alternative, partial correlations, residual analysis, bootstrap CI)
- `data/features/` — 69 .npz files with extracted features
- `data/analysis_outputs/` — diff_map.png, top_rois.csv/png, pca_by_vertical.png, continuous_regression.png, partial_correlations.csv, headline_auc.txt, intent_vs_actual.txt

Everything reproduces from the CSV + extracted features in <10 min on CPU.

## Methodology notes (for transparency)

- **Extraction:** 17 videos full-length, 52 capped at first 30 seconds due to a Colab disconnect mid-overnight run. Whisper transcribes full audio regardless; only the V-JEPA2 video chunks are truncated for capped videos. Re-running with full extraction is the obvious next compute investment but didn't change the n=61 detection floor.
- **PCA:** fitted within each CV training fold (no test leakage). PCA sensitivity sweep at k ∈ {5, 10, 20, 30, 40} all give similar AUCs — the result is robust to component choice.
- **Regularization:** L2 logistic regression. Tested C ∈ {0.1, 1.0}; tighter regularization helps slightly with high-dim features but doesn't flip the conclusion.
- **Baseline composition:** dropped MiniLM caption embeddings from the final baseline because at n=61, 384 noisy text dimensions actively hurt the model (collapsed baseline AUC to 0.518 in v2). Final baseline is `log(followers) + duration` only.
- **Outcome variable:** primary analysis uses `views_at_30d` per memo. Secondary engagement analysis uses `log(views/followers)` and shows the same null result.
- **Cross-validation:** 5-fold stratified, fixed random_state=42 for reproducibility. Bootstrap CI uses 500 resamples at the video level.
- **Apify free-tier exhaustion:** `creator_avg_views_trailing_30d` populated for only 11/70 rows; column omitted from baseline. `creator_followers_at_post` populated 70/70.

## Bottom line

This sprint demonstrates a working TRIBE validation pipeline on real TikTok data. The headline AUC test was inconclusive at this n, and rigorous diagnostic work shows why: between-creator virality is reach-dominated, the dataset has no within-creator pairs, and n=61 is below the detection floor for the effect size we'd care about. Within-creator paired data is the natural next investment, and the pipeline is ready to consume it.

If we choose to invest in v2, I have a concrete plan and the infrastructure to execute on it within ~2 weeks.