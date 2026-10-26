#!/usr/bin/env python3
"""Train the step-level verifier (LoRA on a small LM) from Phase 3 labels.

The model reads: problem + steps so far + the step to judge, and outputs two
logits: P(step is legal) and P(step makes progress). Labels come from the
simulator and the exact solver, so no human or LLM labeling is involved.
Needs a GPU (Colab T4 is fine for Qwen2.5-0.5B).

    python verifier/train_verifier.py --labeled data/labeled --problems data/blocksworld/problems \
        --model Qwen/Qwen2.5-0.5B-Instruct --out checkpoints/verifier --epochs 2

NeuralScorer (bottom of the file) is what rerank_eval.py and the search code use.
"""
import argparse
import json
import random
import time
from pathlib import Path

from common import read_jsonl, verifier_text, auroc

KEYS = ("legal", "progress")


def _load(model_name, num_labels=2):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(model_name)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=num_labels, torch_dtype=torch.float32)
    model.config.pad_token_id = tok.pad_token_id
    return tok, model


def _batches(items, bs):
    for i in range(0, len(items), bs):
        yield items[i:i + bs]


def evaluate(model, tok, rows, texts, bs, max_len, device):
    import torch
    order = sorted(range(len(rows)), key=lambda i: len(texts[i]))
    probs = [None] * len(rows)
    model.eval()
    with torch.no_grad():
        for idx in _batches(order, bs):
            enc = tok([texts[i] for i in idx], return_tensors="pt", padding=True,
                      truncation=True, max_length=max_len).to(device)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device == "cuda"):
                p = torch.sigmoid(model(**enc).logits.float()).cpu().tolist()
            for i, pi in zip(idx, p):
                probs[i] = pi
    out = {}
    for c, k in enumerate(KEYS):
        out[k] = auroc([bool(r[k]) for r in rows], [p[c] for p in probs])
    return out, probs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--labeled", type=Path, default=Path("data/labeled"))
    ap.add_argument("--problems", type=Path, default=Path("data/blocksworld/problems"))
    ap.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct")
    ap.add_argument("--out", type=Path, default=Path("checkpoints/verifier"))
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--max-len", type=int, default=384)
    ap.add_argument("--lora-r", type=int, default=16)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    train, val = read_jsonl(args.labeled / "train.jsonl"), read_jsonl(args.labeled / "val.jsonl")
    mk = lambda rows: [verifier_text(args.problems, r["id"], r["prefix"], r["action"]) for r in rows]
    t_train, t_val = mk(train), mk(val)

    tok, model = _load(args.model)
    cfg = LoraConfig(r=args.lora_r, lora_alpha=2 * args.lora_r, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
                     modules_to_save=["score"], task_type="SEQ_CLS")
    model = get_peft_model(model, cfg).to(device)
    model.print_trainable_parameters()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=args.lr, weight_decay=0.0)
    steps_total = args.epochs * ((len(train) + args.batch - 1) // args.batch)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / 20) * max(0.0, 1 - s / steps_total))
    scaler = torch.cuda.amp.GradScaler(enabled=device == "cuda")
    y_all = torch.tensor([[float(bool(r[k])) for k in KEYS] for r in train])

    best, t0, step = -1, time.time(), 0
    args.out.mkdir(parents=True, exist_ok=True)
    for ep in range(args.epochs):
        model.train()
        idx = list(range(len(train)))
        random.shuffle(idx)
        for b in _batches(idx, args.batch):
            enc = tok([t_train[i] for i in b], return_tensors="pt", padding=True,
                      truncation=True, max_length=args.max_len).to(device)
            with torch.autocast("cuda", dtype=torch.float16, enabled=device == "cuda"):
                logits = model(**enc).logits.float()
            loss = torch.nn.functional.binary_cross_entropy_with_logits(logits, y_all[b].to(device))
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(opt)
            scaler.update()
            sched.step()
            step += 1
            if step % 25 == 0:
                print(f"epoch {ep} step {step}/{steps_total} loss {loss.item():.4f} ({time.time() - t0:.0f}s)")
        auc, _ = evaluate(model, tok, val, t_val, 64, args.max_len, device)
        print(f"epoch {ep} val AUROC legal {auc['legal']:.3f} progress {auc['progress']:.3f}")
        score = auc["legal"] + auc["progress"]
        if score > best:
            best = score
            model.save_pretrained(args.out)
            tok.save_pretrained(args.out)
            (args.out / "base_model.txt").write_text(args.model)
            (args.out / "val_auroc.json").write_text(json.dumps(auc))
            print("saved best checkpoint")


class NeuralScorer:
    """predict([(problem_id, n_blocks, prefix, action)]) -> list of [P(legal), P(progress)]."""
    def __init__(self, ckpt, problems, batch=64, max_len=384):
        import torch
        from peft import PeftModel
        ckpt = Path(ckpt)
        self.tok, base = _load((ckpt / "base_model.txt").read_text().strip())
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = PeftModel.from_pretrained(base, ckpt).to(self.device).eval()
        self.problems, self.batch, self.max_len = problems, batch, max_len

    def predict(self, items):
        rows = [{"legal": 0, "progress": 0}] * len(items)
        texts = [verifier_text(self.problems, pid, p, a) for pid, _, p, a in items]
        _, probs = evaluate(self.model, self.tok, rows, texts, self.batch, self.max_len, self.device)
        return probs


if __name__ == "__main__":
    main()
