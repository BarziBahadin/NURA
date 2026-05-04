#!/usr/bin/env python3
"""
NURA Training CLI
Usage:
  python -m training.cli process-data   # process raw chat logs → training_pairs.csv
  python -m training.cli train-model    # train ML model on training_pairs.csv
  python -m training.cli evaluate       # evaluate model on held-out test set
  python -m training.cli run-pipeline   # process + train + evaluate in one step
  python -m training.cli list-snapshots
  python -m training.cli rollback [snapshot-name]
"""
import json
import logging
import click
import pandas as pd

from training.config import (
    TRAINING_CSV, LOCAL_MODEL_PATH, VECTORIZER_PATH,
    SNAPSHOTS_DIR, MIN_CONFIDENCE_LOCAL, INCLUDE_APPROVED_GAPS,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


@click.group()
def cli():
    """NURA ML Training CLI"""
    pass


@cli.command('process-data')
@click.option('--chat-csv', default=None, help='Path to base chat.csv')
@click.option('--requests-csv', default=None, help='Path to base requests.csv')
@click.option(
    '--include-gaps/--no-include-gaps',
    default=INCLUDE_APPROVED_GAPS,
    help='Include approved Knowledge Gap Queue answers from Postgres.',
)
@click.option('--gap-limit', default=1000, type=int, help='Max approved gaps to import')
@click.option(
    '--include-articles/--no-include-articles',
    default=False,
    help='Include article KB pairs in ML training (off by default — articles are covered by the rules engine and RAG).',
)
def process_data(chat_csv, requests_csv, include_gaps, gap_limit, include_articles):
    """Process data sources and generate training_pairs.csv"""
    from training.processor import (
        extract_from_chat_logs,
        load_approved_gap_pairs,
        load_articles_as_pairs,
        load_manual_training_pairs,
    )

    frames = []

    # Chat logs (optional — skip if not provided)
    if chat_csv and requests_csv:
        click.echo(f"Loading chat logs from {chat_csv}...")
        messages_df = pd.read_csv(chat_csv)
        requests_df = pd.read_csv(requests_csv)
        chat_df = extract_from_chat_logs(messages_df, requests_df)
        click.echo(f"  → {len(chat_df)} pairs from chat logs")
        if not chat_df.empty:
            frames.append(chat_df)
    else:
        click.echo("No chat logs provided — skipping chat log extraction.")

    # Articles: covered by rules engine + RAG at runtime; skip ML training by default
    if include_articles:
        click.echo("Loading articles knowledge base for ML training...")
        article_pairs = load_articles_as_pairs()
        click.echo(f"  → {len(article_pairs)} pairs from articles")
        if article_pairs:
            frames.append(pd.DataFrame(article_pairs))
    else:
        click.echo("Articles skipped (handled by rules engine + RAG — use --include-articles to override).")

    click.echo("Loading manual curated training pairs...")
    manual_pairs = load_manual_training_pairs()
    click.echo(f"  → {len(manual_pairs)} manual pairs")
    if manual_pairs:
        frames.append(pd.DataFrame(manual_pairs))

    if include_gaps:
        click.echo("Loading approved knowledge gaps...")
        gap_pairs = load_approved_gap_pairs(limit=gap_limit)
        click.echo(f"  → {len(gap_pairs)} pairs from approved reviews")
        if gap_pairs:
            frames.append(pd.DataFrame(gap_pairs))

    if not frames:
        click.echo("ERROR: No training data found.")
        return

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=['customer_question', 'agent_response'])

    TRAINING_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(TRAINING_CSV, index=False, encoding='utf-8')

    click.echo(f"\nTotal pairs: {len(combined)}")
    click.echo("Breakdown by category:")
    for cat, count in combined['category'].value_counts().items():
        click.echo(f"  {cat:<30} {count}")
    click.echo(f"\nSaved → {TRAINING_CSV}")


@cli.command('export-approved-gaps')
@click.option('--limit', default=1000, type=int, help='Max approved gaps to import')
def export_approved_gaps(limit):
    """Append approved Knowledge Gap Queue answers to training_pairs.csv"""
    from training.processor import load_approved_gap_pairs

    gap_pairs = load_approved_gap_pairs(limit=limit)
    if not gap_pairs:
        click.echo("No approved knowledge gaps found.")
        return

    gap_df = pd.DataFrame(gap_pairs)
    if TRAINING_CSV.exists():
        existing = pd.read_csv(TRAINING_CSV)
        combined = pd.concat([existing, gap_df], ignore_index=True)
    else:
        combined = gap_df

    combined = combined.drop_duplicates(subset=['customer_question', 'agent_response'])
    TRAINING_CSV.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(TRAINING_CSV, index=False, encoding='utf-8')
    click.echo(f"Added approved gaps. Total pairs: {len(combined)}")
    click.echo(f"Saved → {TRAINING_CSV}")


@cli.command('train-model')
def train_model():
    """Train ML model on training_pairs.csv"""
    from training.trainer import ModelTrainer

    if not TRAINING_CSV.exists():
        click.echo("ERROR: training_pairs.csv not found. Run process-data first.")
        return

    df = pd.read_csv(TRAINING_CSV)
    if df.empty:
        click.echo("ERROR: No training data.")
        return

    click.echo(f"Training on {len(df)} pairs ({df['category'].nunique()} categories)...")
    trainer = ModelTrainer(df)
    trainer.train()
    trainer.save()
    click.echo("Done.")


@cli.command()
@click.option('--threshold', default=None, type=float, help='Confidence threshold to evaluate')
def evaluate(threshold):
    """Evaluate model on a held-out test set"""
    if not TRAINING_CSV.exists():
        click.echo("ERROR: training_pairs.csv not found. Run process-data first.")
        return
    if not LOCAL_MODEL_PATH.exists():
        click.echo("ERROR: model not found. Run train-model first.")
        return

    from training.evaluator import run_evaluation
    t = threshold if threshold is not None else MIN_CONFIDENCE_LOCAL
    run_evaluation(TRAINING_CSV, LOCAL_MODEL_PATH, VECTORIZER_PATH, threshold=t)


@cli.command('list-snapshots')
def list_snapshots():
    """List all saved model snapshots"""
    if not SNAPSHOTS_DIR.exists() or not any(SNAPSHOTS_DIR.iterdir()):
        click.echo("No snapshots found. Run train-model first.")
        return

    snaps = sorted(SNAPSHOTS_DIR.iterdir(), key=lambda p: p.name, reverse=True)
    click.echo(f"{'#':<4} {'Snapshot':<18} {'Samples':>8} {'Cats':>5}  {'Date'}")
    click.echo('-' * 55)
    for i, snap in enumerate(snaps):
        meta_path = snap / "metadata.json"
        if not meta_path.exists():
            continue
        m = json.loads(meta_path.read_text())
        label = " ← active" if i == 0 else ""
        click.echo(
            f"{i:<4} {snap.name:<18} {m.get('n_samples','?'):>8} "
            f"{m.get('n_categories','?'):>5}  {str(m.get('training_date','?'))[:19]}{label}"
        )


@cli.command()
@click.argument('snapshot', required=False)
def rollback(snapshot):
    """Roll back to a previous model snapshot"""
    import shutil

    if not SNAPSHOTS_DIR.exists():
        click.echo("No snapshots directory found.")
        return

    snaps = sorted(SNAPSHOTS_DIR.iterdir(), key=lambda p: p.name, reverse=True)
    if not snaps:
        click.echo("No snapshots found.")
        return

    if snapshot:
        target = SNAPSHOTS_DIR / snapshot
        if not target.exists():
            click.echo(f"Snapshot '{snapshot}' not found.")
            return
    else:
        if len(snaps) < 2:
            click.echo("Only one snapshot — nothing to roll back to.")
            return
        target = snaps[1]

    click.echo(f"Rolling back to: {target.name}")
    shutil.copy2(target / "local_model.pkl", LOCAL_MODEL_PATH)
    shutil.copy2(target / "vectorizer.pkl", VECTORIZER_PATH)
    m = json.loads((target / "metadata.json").read_text())
    click.echo(f"  Samples: {m.get('n_samples','?')}  |  Trained: {str(m.get('training_date','?'))[:19]}")
    click.echo("Rollback complete. Restart the API to load the restored model.")


@cli.command('run-pipeline')
@click.pass_context
@click.option('--chat-csv', default=None)
@click.option('--requests-csv', default=None)
@click.option('--include-gaps/--no-include-gaps', default=INCLUDE_APPROVED_GAPS)
@click.option('--gap-limit', default=1000, type=int)
@click.option('--include-articles/--no-include-articles', default=False)
def run_pipeline(ctx, chat_csv, requests_csv, include_gaps, gap_limit, include_articles):
    """Full pipeline: process → train → evaluate"""
    click.echo("=== NURA Training Pipeline ===\n")
    ctx.invoke(
        process_data,
        chat_csv=chat_csv,
        requests_csv=requests_csv,
        include_gaps=include_gaps,
        gap_limit=gap_limit,
        include_articles=include_articles,
    )
    click.echo()
    ctx.invoke(train_model)
    click.echo()
    ctx.invoke(evaluate)
    click.echo("\n=== Pipeline complete ===")
    click.echo("Restart the API to load the new model: docker compose restart nura-api")


if __name__ == "__main__":
    cli()
