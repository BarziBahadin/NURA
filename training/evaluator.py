import pickle
import logging
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

TEST_FRACTION = 0.20
RANDOM_SEED = 42


def _stratified_split(df, test_frac, seed):
    test_frames, train_frames = [], []
    for _cat, group in df.groupby('category'):
        n_test = max(1, int(len(group) * test_frac))
        test_sample = group.sample(n=n_test, random_state=seed)
        train_frames.append(group.drop(test_sample.index))
        test_frames.append(test_sample)
    return (
        pd.concat(train_frames).sample(frac=1, random_state=seed).reset_index(drop=True),
        pd.concat(test_frames).sample(frac=1, random_state=seed).reset_index(drop=True),
    )


def run_evaluation(training_csv, model_path: Path, vectorizer_path: Path, threshold: float = 0.70) -> dict:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
    from core.ml.local_model import LocalModelService

    df = pd.read_csv(training_csv)
    if df.empty:
        raise ValueError("training_pairs.csv is empty.")

    # Article-derived rows share the same answer across many paraphrases — testing
    # on them inflates accuracy because all paraphrases are trivially similar to
    # training examples. Evaluate on non-article data only for honest numbers.
    article_mask = df["request_id"].astype(str).str.startswith("article_")
    non_article_df = df[~article_mask]
    eval_df = non_article_df if len(non_article_df) >= 10 else df

    _train_df, test_df = _stratified_split(eval_df, TEST_FRACTION, RANDOM_SEED)

    print(f"\n{'='*60}")
    print(f"  Evaluation Report")
    print(f"{'='*60}")
    print(f"  Total pairs   : {len(df):,}  (article-derived excluded from eval: {article_mask.sum()})")
    print(f"  Test set      : {len(test_df):,}  ({TEST_FRACTION*100:.0f}% of non-article data)")
    print(f"  Threshold     : {threshold}")
    print(f"{'='*60}\n")

    model = LocalModelService(model_path=model_path, vectorizer_path=vectorizer_path)

    predictions = []
    by_category = defaultdict(lambda: {'total': 0, 'answered': 0, 'cat_correct': 0})

    for _, row in test_df.iterrows():
        result = model.generate(row['customer_question'], threshold=threshold)
        conf = result['confidence']
        pred_cat = result['category']
        true_cat = row['category']
        predictions.append((conf, pred_cat, true_cat))
        by_category[true_cat]['total'] += 1

    confidences = [p[0] for p in predictions]
    total = len(test_df)
    answered = cat_correct = 0

    for conf, pred_cat, true_cat in predictions:
        if conf >= threshold:
            answered += 1
            by_category[true_cat]['answered'] += 1
            if pred_cat == true_cat:
                cat_correct += 1
                by_category[true_cat]['cat_correct'] += 1

    hit_rate = answered / total
    cat_acc = cat_correct / answered if answered else 0.0
    avg_conf = float(np.mean(confidences))

    print(f"  Hit rate (local model answers) : {hit_rate:6.1%}  ({answered}/{total})")
    print(f"  Category accuracy              : {cat_acc:6.1%}  ({cat_correct}/{answered})")
    print(f"  Average confidence             : {avg_conf:.3f}")
    print()

    print(f"  {'Category':<30} {'Total':>6} {'Hit%':>6} {'CatAcc':>7}")
    print(f"  {'-'*55}")
    for cat, stats in sorted(by_category.items()):
        t = stats['total']
        hr = stats['answered'] / t if t else 0
        ca = stats['cat_correct'] / stats['answered'] if stats['answered'] else 0
        print(f"  {cat:<30} {t:>6} {hr:>6.1%} {ca:>7.1%}")
    print()

    # Suggest best threshold
    best_t, best_f1 = threshold, 0.0
    for candidate in np.arange(0.25, 0.80, 0.025):
        ans = sum(1 for c, _, __ in predictions if c >= candidate)
        correct = sum(1 for c, pc, tc in predictions if c >= candidate and pc == tc)
        rec = ans / total
        prec = correct / ans if ans else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        if f1 > best_f1:
            best_f1, best_t = f1, float(candidate)

    print(f"  Suggested threshold : {best_t:.3f}  (F1 = {best_f1:.3f})")
    print(f"\n{'='*60}\n")

    return {'hit_rate': hit_rate, 'cat_accuracy': cat_acc, 'avg_confidence': avg_conf, 'suggested_threshold': best_t}
