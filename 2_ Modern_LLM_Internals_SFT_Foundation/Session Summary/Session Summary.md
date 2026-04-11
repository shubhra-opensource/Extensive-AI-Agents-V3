# Session summary

## Old AI to LLMs

Earlier models used neural nets and backprop but struggled with long text, task-specific setups, scaling, and labeled data. Transformers fixed that and underpin today’s LLMs.

## CNN ideas in Transformers

Positional encoding gives location; embeddings and multi-head attention act like feature channels; residual Add+Norm is the skip-connection idea.

## Transformer flow (short)

Tokens → embeddings → positional encoding → attention (multi-head) → Add+Norm → feed-forward → stack layers → softmax for next-token probabilities. Inputs can be text, images, audio, code, etc.

## Attention

Looks at all positions, weights importance dynamically, and helps resolve ambiguity (e.g. “bank”, “tiger”).

## Tokenization

Text is split into tokens (balance between words and characters). Vocab is often ~50k–200k; English often uses fewer tokens than many other languages.

## What LLMs do

Predict the next token using all prior tokens as context.

## Limits

Context length is finite; memory and compute grow with input size. Input tokens are cheaper than output tokens (each output step needs prediction and sampling).

## Scaling

More parameters, data, and compute generally improve performance. Chinchilla: training tokens ≈ 20 × parameters. Small-model curves can predict large-model behavior.

## Pretraining vs fine-tuning

Pretraining (causal LM): broad capability on huge data. Fine-tuning (SFT): instruction-following and task fit. Rough analogy: pretraining ≈ general capacity; fine-tuning ≈ behavior and use.

## Cost

Pretraining dominates cost (~98%); fine-tuning is a small fraction (~2%) but drives most practical usefulness.

## Mental model

Tokenize → embed → Transformer layers → predict next token → repeat to generate.

