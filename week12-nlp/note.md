## 1. Named Entity Recognition (NER)
- **Named Entity Recognition** is an information-extraction task that finds named entities in unstructured text and assigns each one a category.
- Unlike document or sentence classification, NER is a **sequence-labeling** task: every token receives a label.
- The notebook uses NER as a foundation for customer-support automation, such as extracting people, organizations, and locations from tickets.
- Structured entities can support ticket routing, CRM updates, agent assistance, analytics, and personally identifiable information (PII) redaction.

---

## 2. CoNLL-2003 Dataset
- The project uses **CoNLL-2003**, a standard English NER benchmark built from newswire text.
- It is used as a proxy for customer-support tickets, so its vocabulary and writing style do not perfectly match the intended business domain.
- Each example contains aligned lists including:
  - `tokens`: the words and punctuation in a sentence.
  - `ner_tags`: the integer NER label assigned to each token.
  - `pos_tags`: part-of-speech labels.
  - `chunk_tags`: syntactic chunk labels.
- Only the tokens and NER tags are used to train this CRF model.

| Split | Sentences |
|---|---:|
| Training | 14,041 |
| Validation | 3,250 |
| Test | 3,453 |

---

## 3. IOB Tagging Scheme
- CoNLL-2003 uses the **IOB** scheme to represent entity types and boundaries.
- `B-` means the beginning of an entity, `I-` means a token inside the same entity, and `O` means the token is outside every named entity.
- The entity types are:
  - `PER`: person.
  - `ORG`: organization.
  - `LOC`: location.
  - `MISC`: miscellaneous entity, such as a nationality or event.

| Tag | Meaning | Example |
|---|---|---|
| `B-PER` | First token of a person | `Werner` in `Werner Zwingmann` |
| `I-PER` | Later token of a person | `Zwingmann` |
| `B-ORG` | First token of an organization | `European` in `European Union` |
| `I-ORG` | Later token of an organization | `Union` |
| `B-LOC` | First token of a location | `Germany` |
| `O` | Not part of an entity | `representative` |

- Separating `B-` and `I-` tags allows the model to distinguish adjacent entities and recover multi-token boundaries.

---

## 4. Sequence Labeling and Token Alignment
- In ordinary text classification, one label describes an entire input; in sequence labeling, the number of labels must match the number of tokens.
- Tokenization and labels therefore must remain aligned. A missing, merged, or incorrectly split token can shift all later labels.
- The notebook already receives word-level tokens from the dataset, so it does not need to perform subword-token alignment.
- For the sample sentence, `European` is tagged `B-ORG` and `Union` is tagged `I-ORG`, while surrounding words receive `O`.

---

## 5. Exploratory Data Analysis
- Training vocabulary: **23,623 unique tokens**.
- Average training sentence length: **14.50 tokens**.
- Minimum sentence length: **1 token**.
- Maximum sentence length: **113 tokens**.
- The sentence-length histogram helps reveal the common sequence sizes and the small number of unusually long examples.
- Frequent-token plots are dominated by punctuation and function words, which usually receive the `O` tag.
- Entity-frequency plots exclude `O` so differences among actual named-entity tags remain visible.

---

## 6. Class Imbalance
- Most tokens in the corpus are not entities and therefore carry the `O` label.
- Among entity labels, beginning tags are generally more common than inside tags because many entities contain only one token.
- This imbalance makes raw token accuracy misleading: a model can achieve high accuracy by predicting `O` frequently while missing important entities.
- Precision, recall, and F1-score should therefore be reported for the entity labels, with `O` excluded from the main classification report.

---

## 7. Rare Words and Out-of-Vocabulary Tokens
- The least-frequent tokens are singletons, including proper names, numeric values, and specialized terms.
- A word-level CRF cannot learn a reliable identity-based pattern from a token seen only once.
- For unseen or rare words, it must generalize from capitalization, character prefixes and suffixes, and neighboring tokens.
- Rare names, unusual casing, numbers, domain terminology, and spelling errors are consequently common sources of mistakes.
- Transformer models with subword tokenization can reuse representations for meaningful word pieces, giving them an advantage on unseen vocabulary.

---

## 8. Why Manual Feature Engineering Is Needed
- A CRF does not automatically learn contextual embeddings like BERT or RoBERTa.
- Instead, each token is converted into a dictionary of manually designed signals.
- Good NER features describe:
  - The token itself.
  - Its character shape.
  - Its immediate left and right context.
  - Whether it occurs at a sentence boundary.
- These signals help the model learn patterns such as title-cased words being likely names and all-uppercase tokens being possible organizations or locations.

---

## 9. Token-Level Features
For each token, `word2features()` creates the following features:

| Feature | Purpose |
|---|---|
| `bias` | Constant feature that lets the model learn an intercept |
| `word.lower()` | Case-normalized token identity |
| `word[-1:]`, `word[-2:]`, `word[-3:]` | Character suffixes |
| `word[:1]`, `word[:2]`, `word[:3]` | Character prefixes |
| `word.isupper()` | Detects all-uppercase words or acronyms |
| `word.istitle()` | Detects title-case words, often useful for names |
| `word.isdigit()` | Detects purely numeric tokens |

- Prefixes and suffixes provide limited character-level generalization when the complete word is unseen.
- Lowercasing provides a stable lexical feature, while case flags preserve capitalization information separately.

---

## 10. Context and Boundary Features
- Entity meaning depends strongly on nearby words. For example, the same place name may refer to a geographic location, sports team, or government.
- The feature extractor includes the previous and next token's lowercase form, title-case flag, and uppercase flag.
- `BOS=True` marks the first token in a sentence.
- `EOS=True` marks the last token in a sentence.
- These boundary features replace missing neighbors and allow the model to learn patterns specific to sentence starts and ends.
- The model uses only a one-token context window, so it cannot represent long-range or deep semantic relationships.

---

## 11. Feature and Label Conversion
- `sent2features()` applies `word2features()` to every token in a sentence.
- `sent2labels()` converts integer NER IDs into readable IOB labels.
- The same feature logic is applied independently to the training, validation, and test splits.
- The resulting structures are nested lists:

```text
X: sentences -> tokens -> feature dictionaries
y: sentences -> token labels
```

- Each feature sequence and label sequence must have identical lengths.

---

## 12. Conditional Random Fields (CRFs)
- A **Conditional Random Field** is a discriminative probabilistic model for structured prediction.
- Independent token classification predicts each tag separately; a CRF scores an entire sequence of tags conditioned on the input features.
- It learns both:
  - **State features:** relationships between input features and labels.
  - **Transition features:** relationships between consecutive labels.
- Transition learning helps preserve valid structures, such as an `I-ORG` usually continuing an organization rather than following an unrelated entity type.
- CRFs are well suited to NER because neighboring output labels are not independent.

---

## 13. CRF Training Configuration
- Library: `sklearn-crfsuite`.
- Optimization algorithm: **L-BFGS**.
- Maximum iterations: **100**.
- L1 regularization coefficient: `c1=0.1`.
- L2 regularization coefficient: `c2=0.1`.
- `all_possible_transitions=True` allows the CRF to consider every label-to-label transition, including transitions not observed in the training data.

| Setting | Role |
|---|---|
| L-BFGS | Efficiently optimizes the CRF objective |
| L1 regularization | Encourages sparse feature weights |
| L2 regularization | Discourages excessively large weights |
| Maximum iterations | Limits optimization time |
| All transitions | Learns weights for the complete transition space |

---

## 14. Evaluation Metrics
- **Precision:** Of the tokens predicted as a label, how many were correct?
- **Recall:** Of the tokens that truly have a label, how many did the model find?
- **F1-score:** Harmonic mean of precision and recall.
- **Support:** Number of true instances of a label in the test set.
- **Micro average:** Pools decisions across all evaluated labels, so frequent labels have more influence.
- **Macro average:** Computes each label's score independently and gives every label equal weight.
- **Weighted average:** Averages per-label scores according to their support.

```text
Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * Precision * Recall / (Precision + Recall)
```

---

## 15. Test Results
The report evaluates the eight entity labels and excludes `O`.

| Label | Precision | Recall | F1 | Support |
|---|---:|---:|---:|---:|
| `B-ORG` | 0.792 | 0.719 | 0.754 | 1,661 |
| `B-MISC` | 0.814 | 0.771 | 0.792 | 702 |
| `B-PER` | 0.834 | 0.839 | 0.836 | 1,617 |
| `I-PER` | 0.871 | 0.955 | 0.911 | 1,156 |
| `B-LOC` | 0.836 | 0.837 | 0.837 | 1,668 |
| `I-ORG` | 0.695 | 0.744 | 0.719 | 835 |
| `I-MISC` | 0.642 | 0.681 | 0.661 | 216 |
| `I-LOC` | 0.768 | 0.696 | 0.731 | 257 |
| **Micro average** | **0.808** | **0.806** | **0.807** | **8,112** |
| **Macro average** | **0.782** | **0.780** | **0.780** | **8,112** |
| **Weighted average** | **0.808** | **0.806** | **0.806** | **8,112** |

- `I-PER` is the strongest individual label with an F1-score of **0.911**.
- `B-PER` and `B-LOC` also perform well at about **0.84 F1**.
- `I-MISC` is the weakest label at **0.661 F1**, followed by inside-organization and inside-location tags.
- Lower scores on `I-` labels indicate that multi-token boundary detection remains difficult, especially for diverse organizations and miscellaneous entities.

---

## 16. Error Analysis
The displayed test errors reveal several recurring problems:

1. **Semantic ambiguity:** Country names can describe locations, teams, governments, or people in sports headlines. The model confuses labels for tokens such as `JAPAN` and `CHINA` because surface form and local casing are insufficient.
2. **Boundary errors:** In `Defender Hassan Abbas`, the model incorrectly begins a person entity at `Defender`, then marks `Hassan` as an inside token. This shifts the entity boundary.
3. **Rare or unseen names:** An unfamiliar name such as `Bitar` can be mistaken for an organization when lexical evidence is weak.
4. **Entity-type confusion:** Nationality terms such as `Uzbek` can be confused between `MISC` and `ORG` depending on context.

- Error analysis complements aggregate scores by showing whether failures come from type selection, boundary detection, rare vocabulary, or annotation ambiguity.

---

## 17. Strengths of the CRF Baseline
- Fast to train and inexpensive to run.
- Lightweight enough for conventional CPU deployment.
- Interpretable feature and transition weights.
- Explicitly models dependencies between adjacent output tags.
- Performs well when entity patterns, casing, and vocabulary resemble the training data.
- Provides a useful baseline before investing in a larger neural model.

---

## 18. Limitations and Domain Shift
- Manual features capture surface patterns but not deep contextual meaning.
- A one-token context window cannot resolve many long-range ambiguities.
- Exact word features are brittle when text contains unseen names, abbreviations, spelling mistakes, or inconsistent casing.
- CoNLL-2003 contains newswire rather than actual customer-support language.
- Performance on this benchmark therefore does not guarantee equivalent results on support tickets.
- Before production use, the system should be evaluated and retrained on representative, human-labeled support data.

---

## 19. Customer-Support Applications
- **Ticket routing:** Use extracted locations and organizations to send tickets to the appropriate region or enterprise-support queue.
- **CRM automation:** Extract people and organizations to suggest customer-record fields.
- **Agent assistance:** Highlight relevant entities so agents can understand a ticket more quickly.
- **Analytics:** Aggregate issues by customer, organization, or region.
- **PII workflows:** Detect names as one component of document review or redaction, with additional safeguards and entity types.
- Because extraction mistakes can corrupt records or misroute requests, initial deployment should keep a human in the loop.

---

## 20. Recommended Deployment Path
- Begin with an **agent-assist** workflow that highlights predicted entities for confirmation.
- Log corrections to build a domain-specific labeled dataset.
- Monitor precision, recall, and F1 by entity type rather than relying on overall token accuracy.
- Track boundary errors, unknown-token performance, spelling variation, and changes in production language.
- Retrain the baseline on real support tickets, then compare it fairly with a transformer model such as BERT or RoBERTa.
- Move to full automation only when production evaluation shows that error rates are acceptable for the downstream action.

---

## 21. CRF vs Transformer-Based NER
| Property | Feature-based CRF | Transformer model |
|---|---|---|
| Input representation | Hand-designed lexical and context features | Learned contextual embeddings |
| Context | Usually a small explicit window | Broad bidirectional context |
| Unknown words | Prefixes, suffixes, casing, and neighbors | Subword representations and context |
| Compute cost | Low | Higher |
| Interpretability | Relatively high | Lower |
| Domain adaptation | Requires feature/data updates | Fine-tuning on domain data |
| Best use | Lightweight baseline or stable narrow domain | Complex, varied, context-dependent language |

---

## One-line summary of all terms

| Term | Meaning |
|---|---|
| NLP | Techniques for analyzing and generating human language |
| NER | Finding text spans that refer to predefined entity types |
| Information extraction | Converting useful facts in unstructured text into structured data |
| Sequence labeling | Assigning one label to every item in an ordered sequence |
| Token | A basic text unit such as a word or punctuation mark |
| Tokenization | Splitting text into tokens |
| Token-label alignment | Keeping every token paired with its correct target label |
| IOB | Boundary scheme using beginning, inside, and outside tags |
| `B-` | Beginning of an entity |
| `I-` | Inside an entity after its beginning |
| `O` | Outside every named entity |
| PER | Person entity type |
| ORG | Organization entity type |
| LOC | Location entity type |
| MISC | Miscellaneous named-entity type |
| EDA | Exploratory analysis used to understand a dataset before modeling |
| Vocabulary | Set of unique tokens observed in a corpus |
| Class imbalance | Unequal frequency of target labels |
| OOV | A word not observed in the training vocabulary |
| Feature engineering | Manually designing model inputs from raw data |
| Orthographic feature | Signal based on spelling, capitalization, digits, or word shape |
| Prefix | Characters at the beginning of a word |
| Suffix | Characters at the end of a word |
| Context feature | Signal derived from nearby tokens |
| BOS | Beginning-of-sentence marker |
| EOS | End-of-sentence marker |
| CRF | Conditional Random Field for structured sequence prediction |
| State feature | Relationship between an input feature and an output label |
| Transition feature | Relationship between consecutive output labels |
| L-BFGS | Numerical optimization algorithm used to fit the CRF |
| L1 regularization | Penalty that encourages sparse weights |
| L2 regularization | Penalty that discourages large weights |
| Precision | Fraction of predicted instances that are correct |
| Recall | Fraction of true instances that are found |
| F1-score | Harmonic mean of precision and recall |
| Support | Number of true examples of a label |
| Micro average | Metric computed from pooled decisions across labels |
| Macro average | Unweighted mean of per-label metrics |
| Weighted average | Per-label metric mean weighted by label frequency |
| Boundary error | Predicting the wrong start or end of an entity span |
| Domain shift | Difference between training data and real deployment data |
| Subword tokenization | Splitting words into reusable smaller units |
| Transformer | Neural architecture that learns contextual representations with attention |
| Agent assist | Human-in-the-loop workflow where predictions support rather than replace an agent |

---
