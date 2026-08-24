## 1. Fine-Tuning
- **Fine-tuning** adapts a pretrained model to a specific downstream task using labeled examples.
- **Pretraining provides:** language structure, grammar, semantics, token representations, and general knowledge.
- **Fine-tuning provides:** task-specific labels, decision boundaries, domain behavior, and output format.
- It usually needs less data and compute than training a model from scratch.
- In this project, fine-tuning teaches models to route customer messages to one of 11 support agents.

---

## 2. Support-Routing Task
- **Input:** A customer's support message from the `instruction` column.
- **Target:** One of 11 values from the `category` column.
- **Dataset:** `bitext/Bitext-customer-support-llm-chatbot-training-dataset`.
- **Goal:** Compare two routing strategies on the same held-out test set:
  1. An encoder-only model that predicts a class.
  2. A decoder-only model that generates the class name.

| Agent | Example intents |
|---|---|
| ACCOUNT | Create, delete, edit, or switch an account |
| CANCEL | Check a cancellation fee |
| CONTACT | Contact customer service or a human agent |
| DELIVERY | Ask about delivery options |
| FEEDBACK | Submit a complaint or review |
| INVOICE | Check or get an invoice |
| ORDER | Cancel, change, or place an order |
| PAYMENT | Check payment methods or report a payment issue |
| REFUND | Check a refund policy or track a refund |
| SHIPPING | Change or set up a shipping address |
| SUBSCRIPTION | Manage a newsletter subscription |

---

## 3. Shared Data Preparation
- Categories are converted to integer IDs using `label2id`; `id2label` converts them back to names.
- The dataset is split into **80% training, 10% validation, and 10% testing**.
- **Stratified splitting** preserves approximately the same class distribution in every split.
- `RANDOM_SEED = 0` makes the split reproducible.
- The notebook produced:
  - Training: **21,497 examples**
  - Validation: **2,687 examples**
  - Test: **2,688 examples**
- Both approaches reuse exactly the same splits, which makes their comparison fair.
- The test set must remain unseen until final evaluation to prevent data leakage.

---

## 4. Encoder-Only vs Decoder-Only Models
| Property | Encoder-only classifier | Decoder-only generator |
|---|---|---|
| Notebook model | DistilBERT | Qwen2.5-0.5B-Instruct |
| Learns | Input representation and class boundary | Next-token generation |
| Output | 11 logits | Generated category text |
| Decision | `argmax(logits)` | Decode and normalize generated tokens |
| Strength | Fast, deterministic classification | Flexible instruction-based output |
| Main weakness | Always chooses a known class | Can generate malformed or extra text |

---

## 5. Approach 1: Encoder-Only Classification
- Model: `distilbert/distilbert-base-uncased`.
- Loaded with `AutoModelForSequenceClassification` and `num_labels=11`.
- DistilBERT turns the input into contextual token representations and feeds its sequence representation to a classification head.
- The classification head outputs one **logit** for each support category.
- A logit is a raw, unnormalized class score; the class with the highest score is selected using `argmax`.
- The pretrained encoder transfers language understanding, but the new classification head begins with randomly initialized weights and must be trained.

---

## 6. Encoder Tokenization and Dynamic Padding
- `AutoTokenizer.from_pretrained()` loads the tokenizer that belongs to the model.
- The uncased DistilBERT tokenizer lowercases text and converts it to token IDs.
- The notebook observed a maximum input length of 32 tokens and used `ENC_MAX_LEN = 32`.
- **Truncation** prevents an input from exceeding the chosen maximum length.
- **Dynamic padding** with `DataCollatorWithPadding` pads only to the longest sequence in each batch.
- Dynamic padding is more compute-efficient than padding every example to a fixed global maximum.

```python
def tokenize_function(examples):
    return enc_tokenizer(
        examples["instruction"],
        truncation=True,
        max_length=ENC_MAX_LEN,
    )
```

---

## 7. Encoder Training Configuration
- **Learning rate:** `2e-5`, a common value for BERT-family fine-tuning.
- **Train/evaluation batch size:** 32.
- **Epochs:** 3.
- **Evaluation and checkpoint saving:** Once per epoch.
- **Optimizer:** Trainer uses AdamW by default.
- **Best checkpoint:** Reloaded using validation macro-F1.
- `model.train()` enables training behavior; `model.eval()` disables dropout for stable inference.
- `torch.no_grad()` disables gradient tracking during inference, reducing memory use and latency.

---

## 8. Approach 2: Decoder-Only Generation
- Model: `Qwen/Qwen2.5-0.5B-Instruct`.
- Loaded with `AutoModelForCausalLM` because the task is represented as next-token generation.
- The model receives a system instruction and the customer's message, then generates a category such as `REFUND`.
- `apply_chat_template()` formats system and user messages using the exact special-token structure expected by Qwen.
- `add_generation_prompt=True` adds the beginning of the assistant turn.
- The target category and EOS token are appended during training:

```text
system prompt + user message + assistant-start + CATEGORY + EOS
```

- The **EOS token** teaches the model to stop after producing the category.
- If a tokenizer has no padding token, its EOS token can be reused as the padding token when padding is correctly masked.

---

## 9. Prompt Design
- The system prompt clearly describes the task and lists all valid categories.
- It instructs the model to output exactly one category without explanation.
- A precise output contract makes generation easier to parse and evaluate.
- Training and inference must use the same chat-template structure; format mismatch can reduce performance.
- The decoder prompt is longer than the original message because it includes system instructions and chat-control tokens.
- Sampled formatted examples had:
  - Mean length: **106.7 tokens**
  - 95th percentile: **112 tokens**
  - Maximum: **117 tokens**
- Therefore, the notebook selected `DEC_MAX_LEN = 128`.

---

## 10. LoRA: Parameter-Efficient Fine-Tuning
- **LoRA (Low-Rank Adaptation)** freezes the original model and learns small low-rank update matrices inside selected layers.
- Instead of directly changing a large weight matrix `W`, LoRA learns an update approximately equal to `BA`, where the rank is much smaller than the original dimensions.
- Benefits:
  - Far fewer trainable parameters.
  - Lower optimizer and gradient memory.
  - Smaller task-specific checkpoints.
  - The same base model can support multiple adapters.
- Notebook configuration:
  - `r=16` – rank of the adapter matrices.
  - `lora_alpha=32` – scales the update; effective scale is `alpha/r = 2`.
  - `lora_dropout=0.05` – regularization.
  - `bias="none"` – bias parameters are not trained.
  - `target_modules="all-linear"` – apply LoRA to linear layers.
  - `task_type="CAUSAL_LM"` – configure adapters for causal language modeling.

---

## 11. Quantization and QLoRA
- **Quantization** stores model weights using fewer bits to reduce memory use.
- **QLoRA** combines a frozen 4-bit quantized base model with trainable LoRA adapters.
- The notebook uses `BitsAndBytesConfig` with:
  - `load_in_4bit=True`
  - `bnb_4bit_quant_type="nf4"`
  - `bnb_4bit_use_double_quant=True`
  - BF16 compute when supported; otherwise FP16.
- **NF4 (Normal Float 4)** is designed for normally distributed neural-network weights.
- **Double quantization** also quantizes quantization constants, saving additional memory.
- `prepare_model_for_kbit_training()` prepares the quantized model for stable adapter training.
- Quantization reduces memory, but can introduce a small approximation error and requires compatible hardware/software.

---

## 12. Decoder Training Configuration
- **Per-device training batch size:** 4.
- **Gradient accumulation steps:** 32.
- **Effective batch size:** `4 × 32 = 128` for one device.
- **Evaluation batch size:** 8.
- **Learning rate:** `2e-4`, higher than full-model fine-tuning because only adapters are trained.
- **Optimizer:** `paged_adamw_32bit`, designed to reduce memory pressure during QLoRA.
- **Epochs:** 3.
- **Warmup:** First 10% of training stabilizes early updates.
- **Scheduler:** Cosine learning-rate decay.
- **Gradient clipping:** `max_grad_norm=0.1` helps control exploding gradients.
- **Evaluation:** Every 10 steps; checkpoints saved every 30 steps.
- `use_cache=False` is used during training because key/value caching is intended for generation and can conflict with memory-saving training techniques.

---

## 13. Gradient Accumulation, Checkpointing, and Training State
- **Gradient accumulation** delays the optimizer update while gradients are collected over several mini-batches.
- It simulates a larger batch without storing the full effective batch in GPU memory at once.
- A **checkpoint** stores model/adaptor weights and training state so training or inference can continue later.
- The notebook reloaded Qwen's base model and the LoRA adapter from `checkpoint-90`.
- After reloading, the trainer's model reference must point to the reloaded model before evaluation.
- Saving `trainer.state.log_history` makes it possible to plot or inspect training after the session ends.

---

## 14. Decoder Inference and Output Normalization
- **Greedy decoding** (`do_sample=False`) always selects the most likely next token, making evaluation deterministic.
- `max_new_tokens=5` limits output because a category should be very short.
- Only newly generated tokens should be decoded; decoding the entire sequence would include the prompt.
- Generated text is normalized by:
  1. Converting to lowercase.
  2. Removing spaces, punctuation, and digits.
  3. Matching the result to a valid category.
- If no valid category is found, the cleaned output is retained and counted as an incorrect prediction.
- Output normalization prevents harmless formatting differences from being treated as errors, but it should not hide genuinely invalid generations.

---

## 15. Zero-Shot vs Fine-Tuned Performance
- **Zero-shot inference** uses a pretrained model without task-specific training.
- It measures how well the model follows the prompt using only knowledge learned before this project.
- Qwen's zero-shot results were:
  - Accuracy: **0.2839**
  - Macro-F1: **0.0276**
- After QLoRA fine-tuning, its results became:
  - Accuracy: **0.9985**
  - Macro-F1: **0.9982**
- The large improvement shows that general instruction-following ability does not automatically provide knowledge of a custom routing taxonomy.

---

## 16. Evaluation Metrics
- **Accuracy:** Proportion of all predictions that are correct.
- **Precision for a class:** Of the examples predicted as that class, how many were correct?
- **Recall for a class:** Of the true examples in that class, how many were found?
- **F1-score:** Harmonic mean of precision and recall.
- **Macro averaging:** Calculate a metric independently for each class and then take the unweighted mean.
- Macro-F1 gives every category equal importance, even when categories have different numbers of examples.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 × Precision × Recall / (Precision + Recall)
```

---

## 17. Confusion Matrix and Loss Curves
- A **confusion matrix** compares true labels (rows) with predicted labels (columns).
- Values on the main diagonal are correct predictions.
- Off-diagonal values reveal which agents the model confuses.
- A **training-loss curve** shows how error changes on the training data.
- A **validation-loss curve** estimates performance on unseen data during training.
- If training loss falls while validation loss rises, the model is likely overfitting.
- If both losses remain high, the model may be underfitting or need different hyperparameters.

---

## 18. Latency and GPU Memory Measurement
- Inference is measured with **batch size 1** to simulate individual routing requests.
- Warm-up calls run before timing so initial CUDA kernel setup does not distort results.
- **Average latency** is total timed inference duration divided by the number of examples.
- `torch.cuda.reset_peak_memory_stats()` resets the counter after warm-up.
- `torch.cuda.max_memory_allocated()` reports peak allocated GPU memory during evaluation.
- Measurements depend on hardware, software versions, model loading, and serving configuration; these results came from a Tesla T4 environment.

---

## 19. Final Model Comparison
| Metric | DistilBERT encoder | Qwen decoder + QLoRA |
|---|---:|---:|
| Precision | 0.999320 | 0.998411 |
| Recall | 0.999318 | 0.997947 |
| Macro-F1 | 0.999318 | 0.998175 |
| Accuracy | 0.999256 | 0.998512 |
| Peak GPU memory | 788.46 MB | 2078.70 MB |
| Latency | 4.81 ms/query | 286.39 ms/query |

- Both models are highly accurate on the in-distribution test set.
- DistilBERT has slightly better macro-F1 and is about **59× faster** in this measurement.
- DistilBERT also uses about **62% less peak GPU memory**.
- For a fixed 11-class routing task, the encoder is the better production choice because generation adds cost without improving quality.

---

## 20. Production Risks and Monitoring
- A closed-set classifier must always select one of its known categories, even for chit-chat or unrelated messages.
- Softmax confidence can be misleading for out-of-distribution inputs.
- A decoder may produce an invalid category, extra explanation, or unexpected formatting.
- Useful safeguards:
  - Add an `OUT_OF_SCOPE` or `CHITCHAT` class.
  - Route low-confidence requests to a general or human-support queue.
  - Track confidence or logit margins.
  - Review per-class precision and recall on human-labeled production samples.
  - Monitor class distribution drift and the rate of downstream re-routing or escalation.
- Very high test performance can reflect a clean or repetitive dataset; real customer messages should be used for further robustness testing.

---

## 21. Data Leakage and Fair Comparison Checklist
- Use one shared train/validation/test split for every approach.
- Fit model weights and adapters only on the training set.
- Use validation data for model selection and hyperparameter decisions.
- Use the test set only for the final comparison.
- Do not tune prompts or preprocessing repeatedly against test results.
- Apply identical label definitions and evaluation metrics to both models.
- Report latency and memory under the same hardware and batch-size conditions.

---

## One-line summary of all terms

| Term | Meaning |
|---|---|
| Fine-tuning | Adapting a pretrained model to a specific task using labeled data |
| Pretraining | Learning general representations from a large corpus before task-specific training |
| Encoder-only model | Reads the whole input and produces a representation for tasks such as classification |
| Decoder-only model | Predicts the next token and generates an output sequence |
| Sequence classification | Selecting one label for an entire input sequence |
| Causal language modeling | Predicting each next token from previous tokens |
| Logit | Raw, unnormalized score for a class or token |
| Argmax | Index of the largest score |
| Tokenization | Converting text into model-readable token IDs |
| Truncation | Cutting sequences that exceed a maximum token length |
| Dynamic padding | Padding each batch only to its longest sequence |
| Chat template | Model-specific formatting for system, user, and assistant turns |
| EOS token | Special token marking the end of a generated sequence |
| LoRA | Low-rank trainable adapters added to a frozen model |
| Rank (`r`) | Size of LoRA's low-dimensional update space |
| `lora_alpha` | Scaling factor applied to a LoRA update |
| Quantization | Representing weights with fewer bits to save memory |
| QLoRA | LoRA training on top of a frozen quantized base model |
| NF4 | A 4-bit number format designed for neural-network weights |
| Gradient accumulation | Combining gradients from several mini-batches before an optimizer step |
| Effective batch size | Per-device batch × accumulation steps × number of devices |
| AdamW | Optimizer that applies decoupled weight decay |
| Warmup | Gradually increasing learning rate at the start of training |
| Cosine decay | Learning-rate schedule that decreases following a cosine curve |
| Gradient clipping | Limiting gradient magnitude to improve training stability |
| SFT | Supervised fine-tuning on input-output examples |
| Checkpoint | Saved model/adaptor weights and training state |
| Greedy decoding | Selecting the highest-probability token at each generation step |
| Zero-shot | Performing a task without task-specific training examples |
| Accuracy | Fraction of all predictions that are correct |
| Precision | Fraction of predicted positives that are correct |
| Recall | Fraction of actual positives correctly found |
| Macro-F1 | Unweighted mean of per-class F1 scores |
| Confusion matrix | Table of true classes versus predicted classes |
| Overfitting | Improving on training data while worsening on unseen data |
| Latency | Time required to produce one prediction |
| Peak GPU memory | Highest GPU memory allocated during measurement |
| Out-of-distribution | Input that differs from the data used to train the model |
| Data leakage | Test or future information improperly influencing training or model selection |

---
