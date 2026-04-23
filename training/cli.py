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
    SNAPSHOTS_DIR, MIN_CONFIDENCE_LOCAL, ARTICLES_JSON,
)

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


@click.group()
def cli():
    """NURA ML Training CLI"""
    pass


@cli.command('process-data')
@click.option('--chat-csv', default=None, help='Path to base chat.csv')
@click.option('--requests-csv', default=None, help='Path to base requests.csv')
def process_data(chat_csv, requests_csv):
    """Process data sources and generate training_pairs.csv"""
    from training.processor import extract_from_chat_logs, load_articles_as_pairs

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
        click.echo("No chat logs provided — using articles only.")

    # Articles
    click.echo("Loading articles knowledge base...")
    article_pairs = load_articles_as_pairs()
    click.echo(f"  → {len(article_pairs)} pairs from articles")
    if article_pairs:
        frames.append(pd.DataFrame(article_pairs))

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
def run_pipeline(ctx, chat_csv, requests_csv):
    """Full pipeline: process → train → evaluate"""
    click.echo("=== NURA Training Pipeline ===\n")
    ctx.invoke(process_data, chat_csv=chat_csv, requests_csv=requests_csv)
    click.echo()
    ctx.invoke(train_model)
    click.echo()
    ctx.invoke(evaluate)
    click.echo("\n=== Pipeline complete ===")
    click.echo("Restart the API to load the new model: docker compose restart nura-api")


if __name__ == "__main__":
    cli()
