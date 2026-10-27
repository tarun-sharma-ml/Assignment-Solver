"""LoRA fine-tune on a free Colab/Kaggle GPU with Unsloth, then export a GGUF for Ollama.

Run it from the notebook in notebooks/finetune_colab.ipynb (it needs a GPU, so it is
not meant to run on your laptop). Unsloth's API moves quickly; if a call fails, check
https://docs.unsloth.ai for the current names.
"""
from __future__ import annotations

import argparse

from ..generate.prompt import training_messages
from .build_dataset import load_dataset


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/processed/train.jsonl")
    ap.add_argument("--base-model", default="unsloth/Qwen2.5-3B-Instruct-bnb-4bit")
    ap.add_argument("--out-dir", default="gguf_out")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--max-seq", type=int, default=4096)
    args = ap.parse_args()

    from datasets import Dataset  # imported late: only available on the training machine
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel, is_bfloat16_supported

    model, tok = FastLanguageModel.from_pretrained(args.base_model, max_seq_length=args.max_seq, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model,
        r=args.rank,
        lora_alpha=args.rank * 2,
        lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    rows = load_dataset(args.dataset)
    texts = [tok.apply_chat_template(training_messages(r), tokenize=False) for r in rows]
    ds = Dataset.from_dict({"text": texts})
    print(f"{len(ds)} training examples")

    trainer = SFTTrainer(
        model=model,
        tokenizer=tok,
        train_dataset=ds,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=args.max_seq,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            num_train_epochs=args.epochs,
            learning_rate=args.lr,
            warmup_ratio=0.05,
            logging_steps=1,
            optim="adamw_8bit",
            fp16=not is_bfloat16_supported(),
            bf16=is_bfloat16_supported(),
            seed=3407,
            output_dir="checkpoints",
            report_to="none",
        ),
    )
    trainer.train()
    model.save_pretrained_gguf(args.out_dir, tok, quantization_method="q4_k_m")
    print(f"Done. Download the .gguf from ./{args.out_dir}")


if __name__ == "__main__":
    main()
