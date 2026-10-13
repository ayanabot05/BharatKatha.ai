"""Cloud Run only: train and adapt language-ID weights; never trains a video model."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unicodedata
import zipfile


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", text).split())


def short(text):
    words = text.split()
    return " ".join(words[:16]) if len(words) > 16 else text[:120]


def main():
    # Deliberately no local override: this user's laptop must not perform fitting.
    if not os.environ.get("CLOUD_RUN_JOB"):
        raise RuntimeError("Training is restricted to a Google Cloud Run job")
    destination = os.environ["OUTPUT_GCS_URI"]
    if not destination.startswith("gs://"):
        raise ValueError("OUTPUT_GCS_URI must use Cloud Storage")
    import numpy as np
    from google.cloud import storage
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import SGDClassifier
    from sklearn.metrics import classification_report, f1_score
    from sklearn.model_selection import train_test_split
    import fetch_wili

    fetch_wili.main()
    labels = {"hin", "mar", "tel", "tam", "kan", "mal", "ben", "guj", "urd", "ori", "eng",
              "nep", "san", "asm", "ara", "fas", "fra", "spa"}
    archive = fetch_wili.ROOT / "wili-2018.zip"
    with zipfile.ZipFile(archive) as bundle:
        def read(name):
            member = next(n for n in bundle.namelist() if n.rsplit("/", 1)[-1] == name)
            return bundle.read(member).decode("utf-8").splitlines()
        def rows(split):
            texts, targets = read(f"x_{split}.txt"), read(f"y_{split}.txt")
            if len(texts) != len(targets):
                raise ValueError("Dataset text/label lengths differ")
            return [(normalized(x), y.strip()) for x, y in zip(texts, targets)
                    if y.strip() in labels and len(normalized(x)) >= 30]
        training, testing = rows("train"), rows("test")
    # Remove exact duplicate paragraphs; exclude test overlap before validation split.
    training = list(dict.fromkeys(training))
    seen = {x for x, _ in training}
    testing = list(dict.fromkeys((x, y) for x, y in testing if x not in seen))
    train, valid = train_test_split(training, test_size=.2, random_state=42,
                                   stratify=[y for _, y in training])
    vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 5), max_features=60000,
                                 sublinear_tf=True, dtype=np.float32)
    fit_x = vectorizer.fit_transform([x for x, _ in train])
    fit_y = np.array([y for _, y in train])
    model = SGDClassifier(loss="log_loss", alpha=1e-5, random_state=42,
                          max_iter=30, tol=1e-4, n_jobs=1)
    model.fit(fit_x, fit_y)
    baseline = copy.deepcopy(model)
    validation_x = vectorizer.transform([short(x) for x, _ in valid])
    validation_y = [y for _, y in valid]
    baseline_score = f1_score(validation_y, model.predict(validation_x), average="macro")
    checkpoints = [{"epoch": 0, "validation_short_macro_f1": baseline_score}]
    best, best_score, best_epoch = copy.deepcopy(model), baseline_score, 0
    short_x = vectorizer.transform([short(x) for x, _ in train])
    for epoch in range(1, 6):
        order = np.random.default_rng(42 + epoch).permutation(len(train))
        model.partial_fit(short_x[order], fit_y[order])
        score = f1_score(validation_y, model.predict(validation_x), average="macro")
        checkpoints.append({"epoch": epoch, "validation_short_macro_f1": score})
        if score > best_score:
            best, best_score, best_epoch = copy.deepcopy(model), score, epoch
    # Test is only examined after checkpoint selection; no test-based retraining.
    test_y = [y for _, y in testing]
    metrics = {}
    for size, texts in [("paragraph", [x for x, _ in testing]),
                        ("short", [short(x) for x, _ in testing])]:
        matrix = vectorizer.transform(texts)
        metrics[size] = {}
        for name, candidate in [("baseline", baseline), ("selected", best)]:
            pred = candidate.predict(matrix)
            metrics[size][name] = classification_report(test_y, pred, output_dict=True, zero_division=0)
    out = Path("/tmp/language-model")
    out.mkdir(exist_ok=True)
    artifact = {"format": "vidbharat-char-language-id-v1", "classes": best.classes_.tolist(),
                "vocabulary": {k: int(v) for k, v in vectorizer.vocabulary_.items()},
                "idf": vectorizer.idf_.tolist(), "coef": best.coef_.tolist(),
                "intercept": best.intercept_.tolist(), "ngram_range": [2, 5],
                "sublinear_tf": True, "lowercase": True, "norm": "l2"}
    (out / "weights.json").write_text(json.dumps(artifact), encoding="utf-8")
    report = {"training_location": "Google Cloud Run", "job": os.environ["CLOUD_RUN_JOB"],
              "execution": os.environ.get("CLOUD_RUN_EXECUTION"), "target": "language identification only",
              "generative_video_model_tuned": False, "production_approved": False,
              "split_counts": {"fit": len(train), "validation": len(valid), "test": len(testing)},
              "checkpoints": checkpoints, "selected_epoch": best_epoch, "test": metrics,
              "limitations": ["Wikipedia domain differs from narration", "No native-speaker evaluation",
                              "Exact deduplication only; near-duplicate leakage remains possible",
                              "Classifier confidence is not calibrated; do not hard-block production"],
              "weights_sha256": hashlib.sha256((out / "weights.json").read_bytes()).hexdigest()}
    (out / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    bucket_name, _, prefix = destination[5:].partition("/")
    bucket = storage.Client().bucket(bucket_name)
    for path in [out / "weights.json", out / "evaluation.json", fetch_wili.ROOT / "source_manifest.json"]:
        bucket.blob(f"{prefix.rstrip('/')}/{path.name}").upload_from_filename(str(path), if_generation_match=0)
    bucket.blob(f"{prefix.rstrip('/')}/wili-2018.zip").upload_from_filename(str(archive), if_generation_match=0)
    print(json.dumps({"status": "complete", "output": destination, "selected_epoch": best_epoch}), flush=True)


if __name__ == "__main__":
    main()
