---

## 1. Sequence Learning
- **Sequence learning** models ordered data where the position and context of each element matter.
- Examples include text, speech, sensor readings, financial time series, and biological sequences.
- In text, changing word order can change meaning, so a model should not treat a sentence as an unordered collection of words.
- Recurrent neural networks process a sequence one step at a time and carry information forward through a hidden state.
- In this project, an LSTM classifies news headlines into four AG News topics.

---

## 2. Text-Classification Task
- **Dataset:** `fancyzhx/ag_news` from Hugging Face Datasets.
- **Input:** News text from the `text` field.
- **Target:** An integer label from 0 to 3.
- **Classes:**

| Label | Class |
|---:|---|
| 0 | World |
| 1 | Sports |
| 2 | Business |
| 3 | Sci/Tech |

- The complete dataset contains 120,000 training and 7,600 test examples.
- The notebook uses only the first 5,000 training and 1,000 test examples for faster execution.
- Using a small, non-random prefix may reduce coverage and produce an unrepresentative sample.

---

## 3. Text Preprocessing
- Neural networks operate on numbers, so raw text must be tokenized and numericalized.
- The tokenizer:
  1. Converts text to lowercase.
  2. Uses the regular expression `[a-z0-9]+` to keep alphanumeric tokens.
  3. Returns a list of words and number sequences.

```python
def tokenizer(text):
    return re.findall(r"[a-z0-9]+", text.lower())
```

- Lowercasing reduces vocabulary size by treating `Bank` and `bank` as the same token.
- This simple regular expression removes punctuation and contractions; for example, `NASA's` becomes `nasa`, `s`.
- Simple tokenization is fast but loses some linguistic information.

---

## 4. Building a Vocabulary
- A **vocabulary** maps every known token to a unique integer ID.
- `Counter` counts token occurrences in the training corpus.
- `stoi` means **string-to-index** and maps words to IDs.
- `itos` means **index-to-string** and maps IDs back to words.
- The notebook creates a vocabulary of **65,017 tokens**.
- A vocabulary must be built from training data only; using test text would cause data leakage.
- The notebook includes every observed training word. In larger projects, a minimum-frequency threshold can remove rare words and reduce memory use.

---

## 5. Special Tokens
- `<unk>` represents a token that is not present in the training vocabulary.
- `<pad>` fills unused positions so sequences in a batch have equal length.
- The notebook places them first:

```python
itos = ['<unk>', '<pad>'] + list(counter.keys())
UNK_IDX = stoi['<unk>']
PAD_IDX = stoi['<pad>']
```

- `stoi.get(token, UNK_IDX)` safely maps unseen words to `<unk>`.
- Special tokens need stable IDs because preprocessing, embeddings, and batching all refer to them.

---

## 6. Numericalization
- **Numericalization** converts a tokenized sentence into a sequence of vocabulary IDs.

```text
"team wins final" → [184, 921, 376]
```

- The actual IDs depend on how the vocabulary was constructed.
- The result is stored as an integer tensor because embedding layers expect token indices, not floating-point input.
- An empty token sequence should be handled explicitly in production, for example by inserting `<unk>`.

---

## 7. Batching and Padding
- Headlines have different lengths, but tensors in one batch must have the same dimensions.
- `pad_sequence(..., batch_first=True, padding_value=PAD_IDX)` pads each sequence to the longest sequence in its batch.
- With `batch_first=True`, the text tensor has shape:

```text
(batch_size, maximum_sequence_length_in_batch)
```

- The label tensor has shape `(batch_size,)`.
- Dynamic batch padding wastes less computation than padding every headline to one dataset-wide maximum.
- The training DataLoader uses `shuffle=True`; evaluation uses `shuffle=False`.
- The notebook uses a batch size of 32.

---

## 8. Word Embeddings
- An **embedding layer** maps each discrete token ID to a learned dense vector.
- Notebook configuration: `nn.Embedding(vocab_size, 64, padding_idx=PAD_IDX)`.
- Each token is represented by a 64-dimensional vector.
- Similar words can develop similar vectors during training because their embeddings receive similar gradient updates.
- `padding_idx=PAD_IDX` keeps the padding vector fixed, normally as zeros, and prevents it from being updated.
- This prevents `<pad>` from learning semantic meaning, but it does **not** make the LSTM automatically ignore padded time steps.

---

## 9. Recurrent Neural Networks
- An **RNN** updates a hidden state at every sequence step using the current input and previous hidden state.
- The hidden state acts as a compressed memory of earlier tokens.
- Standard RNNs can struggle with long-term dependencies because gradients may vanish or explode across many time steps.
- LSTMs add gates and a separate cell state to control what information is stored, forgotten, and exposed.

---

## 10. Long Short-Term Memory (LSTM)
- An LSTM maintains:
  - **Hidden state (`h_t`):** Short-term representation exposed at the current step.
  - **Cell state (`c_t`):** Longer-term memory flowing through the sequence.
- Its main gates are:
  - **Forget gate:** Decides what old cell-state information to discard.
  - **Input gate:** Decides what new information to store.
  - **Output gate:** Decides what part of memory becomes the hidden state.
- Simplified equations:

```text
f_t = sigmoid(W_f [h_(t-1), x_t] + b_f)
i_t = sigmoid(W_i [h_(t-1), x_t] + b_i)
g_t = tanh(W_g [h_(t-1), x_t] + b_g)
c_t = f_t ⊙ c_(t-1) + i_t ⊙ g_t
o_t = sigmoid(W_o [h_(t-1), x_t] + b_o)
h_t = o_t ⊙ tanh(c_t)
```

- `sigmoid` produces values from 0 to 1, allowing gates to behave like soft switches.
- `⊙` means element-wise multiplication.

---

## 11. LSTM Input and Output Shapes
- Notebook configuration: `nn.LSTM(embed_dim=64, hidden_dim=128, batch_first=True)`.
- Given embedded input shaped `(batch, sequence_length, 64)`, the LSTM returns:
  - `output`: `(batch, sequence_length, 128)` – hidden state from every time step.
  - `hidden`: `(num_layers, batch, 128)` – final hidden state for every layer.
  - `cell`: `(num_layers, batch, 128)` – final cell state for every layer.
- For a one-layer, one-direction LSTM, `hidden[-1]` has shape `(batch, 128)`.
- A linear layer maps it to four class logits:

```python
logits = self.fc(hidden[-1])  # (batch, 4)
```

- `output[:, -1, :]` and `hidden[-1]` are closely related for an unpadded, one-direction, one-layer sequence, but padding and multi-layer/bidirectional setups require more care.

---

## 12. Why Use the Final Hidden State?
- Text classification needs one fixed-size representation for the whole sentence.
- `output` contains a representation for every time step, while `hidden[-1]` provides the last layer's final sequence representation.
- The final hidden state can summarize information gathered while reading the headline.
- The classifier converts this 128-dimensional summary into four logits.
- Alternative pooling strategies include:
  - Mean or max pooling over valid `output` positions.
  - Attention-weighted pooling.
  - Concatenating final forward and backward states from a bidirectional LSTM.

---

## 13. Important Padding Issue in the Notebook
- The batch collator pads headlines but does not return their original lengths.
- Although padding embeddings are zero, the LSTM still processes every padded time step.
- Therefore, `hidden[-1]` may describe the state **after padding**, not immediately after the last real word.
- Shorter sequences receive more padded recurrent steps, which can weaken or distort their representation.
- This is a likely contributor to the notebook's low accuracy.
- The standard solution is to return lengths from `collate_batch()` and use a packed sequence:

```python
packed = nn.utils.rnn.pack_padded_sequence(
    embedded,
    lengths.cpu(),
    batch_first=True,
    enforce_sorted=False,
)
_, (hidden, cell) = self.lstm(packed)
logits = self.fc(hidden[-1])
```

- Packing makes the LSTM stop each example at its true length and avoids recurrent computation over padding.

---

## 14. Classification Head and Cross-Entropy Loss
- `nn.Linear(hidden_dim, num_classes)` transforms the sequence representation into four logits.
- The model does not need an explicit softmax layer during training.
- `nn.CrossEntropyLoss()` combines log-softmax and negative log-likelihood internally.
- It expects:
  - Raw logits shaped `(batch_size, num_classes)`.
  - Integer class labels shaped `(batch_size,)`.
- Applying softmax before `CrossEntropyLoss` is unnecessary and can make optimization numerically less stable.
- During prediction, `argmax(dim=1)` selects the index of the largest logit.

---

## 15. PyTorch Training Loop
- Training follows these steps for each mini-batch:
  1. Move texts and labels to the selected device.
  2. Clear old gradients with `optimizer.zero_grad()`.
  3. Run the forward pass to compute logits.
  4. Compute cross-entropy loss.
  5. Run `loss.backward()` to calculate gradients.
  6. Run `optimizer.step()` to update parameters.
- `model.train()` enables training behavior.
- The notebook uses Adam with learning rate `0.005` for three epochs.
- The model contains **4,260,932 trainable parameters**, most of which are in the large embedding table.

---

## 16. Evaluation and Inference
- `model.eval()` switches the model to evaluation mode.
- `torch.no_grad()` disables gradient calculation, which reduces memory usage and speeds up inference.
- Evaluation accuracy is:

```text
number of correct predictions / total number of examples
```

- Single-text inference performs the same preprocessing as training, adds a batch dimension with `unsqueeze(0)`, runs the model, and converts the predicted index to a class name.
- Training and inference must always share the same tokenizer, vocabulary, special-token IDs, and label order.

---

## 17. Recorded Results and Diagnosis
- Notebook results:

| Epoch | Training accuracy | Test-subset accuracy |
|---:|---:|---:|
| 1 | 29.8% | 25.4% |
| 2 | 30.3% | 25.5% |
| 3 | 30.8% | 26.9% |

- Custom-headline accuracy was **24.0%**.
- Random guessing across four balanced classes would be approximately **25%**, so the model learned very little.
- Likely causes include:
  - Processing padded positions before reading `hidden[-1]`.
  - Training on only 5,000 of 120,000 examples.
  - Using the first dataset rows instead of a shuffled or stratified sample.
  - A large 65,017-word vocabulary with many rare embeddings but little training data.
  - Only three training epochs.
  - A relatively high learning rate of `0.005`.
  - Simple tokenization and no pretrained word embeddings.
- Similar train and evaluation accuracy near chance suggests **underfitting**, not classical overfitting.

---

## 18. Improvements
- Use `pack_padded_sequence()` or mask-aware pooling so padding is ignored.
- Shuffle or stratify before selecting a subset, or train on the complete dataset.
- Add a minimum word frequency such as 2 or 5 to reduce vocabulary size.
- Use pretrained embeddings such as GloVe, or use a subword tokenizer.
- Try a lower learning rate and train for more epochs while monitoring validation loss.
- Add dropout for regularization when using a larger model or longer training.
- Try a bidirectional LSTM to capture both left-to-right and right-to-left context.
- Track macro-F1 and a confusion matrix in addition to accuracy.
- Keep a separate validation set for hyperparameter tuning; do not repeatedly tune against the test set.
- Compare against simple baselines such as TF-IDF with logistic regression and modern pretrained transformers.

---

## 19. Data and Modeling Checklist
- Vocabulary constructed from training data only?
- Unknown and padding tokens defined consistently?
- Empty inputs handled?
- Original sequence lengths preserved before padding?
- Padding ignored by the recurrent model or pooling step?
- Training data shuffled?
- Validation and test data kept separate?
- Labels aligned with class names?
- `model.train()` and `model.eval()` used correctly?
- Gradients disabled during evaluation?
- Accuracy compared with a majority-class or random baseline?
- Misclassified examples inspected for systematic patterns?

---

## One-line summary of all terms

| Term | Meaning |
|---|---|
| Sequence learning | Learning from ordered inputs where position and context matter |
| Text classification | Assigning a predefined category to a text sequence |
| Tokenization | Splitting raw text into smaller units called tokens |
| Vocabulary | Mapping between known tokens and integer IDs |
| `stoi` | String-to-index token mapping |
| `itos` | Index-to-string token mapping |
| `<unk>` | Token used for a word missing from the vocabulary |
| `<pad>` | Token used to equalize sequence lengths in a batch |
| Numericalization | Converting text tokens into integer IDs |
| Collate function | Function that combines individual dataset examples into one batch |
| Dynamic padding | Padding only to the longest sequence in the current batch |
| Embedding | Learned dense vector representing a token |
| `padding_idx` | Embedding index kept fixed so padding does not learn meaning |
| Hidden state | Recurrent representation passed between time steps |
| Cell state | LSTM's longer-term internal memory |
| Forget gate | Controls which previous cell-state information is removed |
| Input gate | Controls which new information enters the cell state |
| Output gate | Controls which cell-state information becomes the hidden state |
| `batch_first=True` | Uses tensor order `(batch, sequence, feature)` |
| Packed sequence | Representation that lets an RNN skip padded time steps |
| Logit | Raw class score produced before softmax |
| Linear layer | Affine transformation mapping features to class logits |
| Cross-entropy loss | Classification loss comparing logits with integer targets |
| Forward pass | Computing model outputs from inputs |
| Backpropagation | Computing gradients of the loss through the model |
| Optimizer | Algorithm that updates parameters using gradients |
| Adam | Adaptive gradient-based optimization algorithm |
| Epoch | One complete pass through the training data |
| Mini-batch | Small group of examples processed in one iteration |
| `model.train()` | Enables training-mode behavior |
| `model.eval()` | Enables evaluation-mode behavior |
| `torch.no_grad()` | Disables gradient tracking during evaluation or inference |
| Argmax | Index of the largest class score |
| Accuracy | Fraction of predictions that match their labels |
| Underfitting | Model fails to learn the training pattern sufficiently |
| Overfitting | Model fits training data but generalizes poorly to unseen data |
| Bidirectional LSTM | LSTM that reads a sequence in both forward and backward directions |
| Data leakage | Evaluation information improperly influences training or model choices |

---
