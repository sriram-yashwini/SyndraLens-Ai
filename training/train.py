
import os
import sys

# Dynamically resolve script directory and project root to fix _boot import errors
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import torch
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model

from _boot import load_config
from syndralens.schema import TASK_INSTRUCTION


def main():
    cfg = load_config()
    data_dir = cfg["data"].get("processed_dir", "data/processed_v2")
    
    # Normalize Windows paths for HuggingFace datasets
    train_path = os.path.abspath(os.path.join(data_dir, "train.jsonl")).replace("\\", "/")
    val_path = os.path.abspath(os.path.join(data_dir, "val.jsonl")).replace("\\", "/")

    if not os.path.exists(train_path):
        alt_dir = "data/processed_v2" if "v2" not in data_dir else "data/processed"
        train_path = os.path.abspath(os.path.join(alt_dir, "train.jsonl")).replace("\\", "/")
        val_path = os.path.abspath(os.path.join(alt_dir, "val.jsonl")).replace("\\", "/")

    print(f"Loading train dataset from: {train_path}")
    print(f"Loading val dataset from: {val_path}")

    dataset = load_dataset(
        "json",
        data_files={"train": train_path, "validation": val_path}
    )

    base_model_name = cfg["model"].get("base_model", "Qwen/Qwen2.5-0.5B-Instruct")
    output_dir = cfg["model"].get("adapter_dir", "models/syndralens-lora-v3")

    print(f"Loading Base Model on CPU: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    
    tokenizer.truncation_side = "right"
    tokenizer.padding_side = "right"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize_function(example):
        messages = [
            {"role": "system", "content": TASK_INSTRUCTION},
            {
                "role": "user",
                "content": (
                    f"Clinical text (extract only supported facts):\n{example['text']}\n"
                    "Return exactly one complete JSON object. Do not omit required fields."
                ),
            },
            {"role": "assistant", "content": example["target"]},
        ]
        full_text = tokenizer.apply_chat_template(messages, tokenize=False)
        return tokenizer(
            full_text,
            truncation=True,
            max_length=1024,
            padding=False,
        )

    print("Tokenizing datasets for CPU training...")
    tokenized_dataset = dataset.map(
        tokenize_function,
        remove_columns=dataset["train"].column_names,
    )

    # Force explicit CPU Float32 execution
    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        dtype=torch.float32,
        device_map=None,
        trust_remote_code=True,
    )

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Native CPU TrainingArguments
    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=8,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=50,
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        learning_rate=2e-4,
        num_train_epochs=3,
        logging_steps=10,
        fp16=False,
        bf16=False,
        use_cpu=True,
        report_to="none",
    )

    # Native Causal LM Data Collator (Standard PyTorch operations, no CUDA/fused kernels)
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
        data_collator=data_collator,
    )

    print("Starting CPU training loop...")
    trainer.train()

    print(f"Saving best adapter checkpoint to {output_dir}")
    trainer.model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)


if __name__ == "__main__":
    main()