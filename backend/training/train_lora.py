"""
train_lora.py
──────────────
Fine-tunes google/flan-t5-base with a LoRA adapter on training_data_v2.json
(or any file matching that schema). Config mirrors your existing adapter
exactly (backend/app/models/flan_t5_interview_final_v5/adapter_config.json)
so question_service.py / evaluation_service.py can load whatever this
produces with zero code changes — just point FLAN_T5_ADAPTER_DIR at it.

Run this on YOUR machine, not in a sandboxed environment — it needs network
access to download google/flan-t5-base from Hugging Face (~250MB) the first
time it runs.

Usage:
    pip install torch transformers peft sentencepiece
    python train_lora.py --data training_data_v2.json --out ./flan_t5_interview_v6 --epochs 6

Expect roughly 15-45 minutes on a modern CPU for ~700 examples over a few
epochs; minutes on any CUDA GPU. Loss printed every 20 steps; a held-out
validation pass runs at the end of each epoch so you can see it actually
generalizing (not just memorizing) before you commit to the result.
"""

import argparse
import json
import os

import torch
from torch.utils.data import Dataset
from transformers import (
    T5ForConditionalGeneration,
    T5Tokenizer,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq,
)
from peft import LoraConfig, get_peft_model, TaskType

BASE_MODEL = "google/flan-t5-base"

# Matches backend/app/models/flan_t5_interview_final_v5/adapter_config.json
# exactly — same rank/alpha/dropout/target_modules — so the new adapter is
# a drop-in replacement, not a different architecture question_service.py
# would need updating to load.
LORA_CONFIG = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q", "v"],
    bias="none",
)

# Matches question_service.py's MAX_INPUT_LEN / MAX_TARGET_LEN — training
# and inference need to agree on these or generation quality degrades.
MAX_INPUT_LEN = 128
MAX_TARGET_LEN = 64


class QAPairDataset(Dataset):
    def __init__(self, examples, tokenizer):
        self.examples = examples
        self.tokenizer = tokenizer

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        model_inputs = self.tokenizer(
            ex["input_text"], max_length=MAX_INPUT_LEN, truncation=True,
        )
        labels = self.tokenizer(
            text_target=ex["target_text"], max_length=MAX_TARGET_LEN, truncation=True,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="training_data_v2.json (or similar)")
    ap.add_argument("--out", default="./flan_t5_interview_v6", help="where to save the LoRA adapter")
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--lr", type=float, default=3e-4)
    args = ap.parse_args()

    with open(args.data) as f:
        data = json.load(f)
    train_examples = data["train"]
    val_examples = data["validation"]
    print(f"Loaded {len(train_examples)} train / {len(val_examples)} validation examples")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    tokenizer = T5Tokenizer.from_pretrained(BASE_MODEL)
    base_model = T5ForConditionalGeneration.from_pretrained(BASE_MODEL)
    model = get_peft_model(base_model, LORA_CONFIG)
    model.print_trainable_parameters()
    model.to(device)

    train_ds = QAPairDataset(train_examples, tokenizer)
    val_ds = QAPairDataset(val_examples, tokenizer)
    collator = DataCollatorForSeq2Seq(tokenizer, model=model)

    training_args = Seq2SeqTrainingArguments(
        output_dir="./_train_checkpoints",
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="no",          # we save the final adapter explicitly below
        logging_steps=20,
        predict_with_generate=True,
        report_to=[],                 # no wandb/etc — keep this self-contained
        use_cpu=(device == "cpu"),
    )

    # transformers renamed the Seq2SeqTrainer/Trainer constructor's
    # `tokenizer=` kwarg to `processing_class=` partway through the 4.x
    # series. Your requirements.txt pins transformers==4.46.3; depending on
    # exactly which patch/minor you end up with when you install fresh,
    # either name may be expected — try the current name first and fall
    # back to the old one rather than hard-failing on a version mismatch.
    try:
        trainer = Seq2SeqTrainer(
            model=model, args=training_args, train_dataset=train_ds,
            eval_dataset=val_ds, data_collator=collator, processing_class=tokenizer,
        )
    except TypeError:
        trainer = Seq2SeqTrainer(
            model=model, args=training_args, train_dataset=train_ds,
            eval_dataset=val_ds, data_collator=collator, tokenizer=tokenizer,
        )

    trainer.train()

    os.makedirs(args.out, exist_ok=True)
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)

    # question_service.py / evaluation_service.py both read model_config.json
    # from the adapter directory — write the same shape the existing v5
    # adapter has, pointed at the right base model and this new folder.
    with open(os.path.join(args.out, "model_config.json"), "w") as f:
        json.dump({
            "base_model": BASE_MODEL,
            "lora_adapter": f"./{os.path.basename(args.out)}",
            "max_input_len": MAX_INPUT_LEN,
            "max_target_len": MAX_TARGET_LEN,
        }, f, indent=2)

    print(f"\nSaved LoRA adapter to {args.out}")
    print("Next steps:")
    print(f"  1. Copy the '{os.path.basename(args.out)}' folder into "
          f"backend/app/models/")
    print(f"  2. Set FLAN_T5_ADAPTER_DIR to its path (or rename it to match "
          f"question_service.py's default: flan_t5_interview_final_v5)")
    print(f"  3. Restart the Flask app and check /api/health / the model "
          f"warm-up logs to confirm it loaded")


if __name__ == "__main__":
    main()