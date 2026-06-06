# Local ML repo deployment smoke-test pattern

Use this when deploying a remote machine-learning repo locally and the user asks for a working artifact, not just clone/install instructions.

## Pattern

1. Place external repos under the workspace GitHub area, not `$HOME` root, e.g. `~/.hermes/workspace/github/<owner>/<repo>`.
2. Clone or update from the declared remote and record the remote URL plus short commit hash.
3. Create an isolated environment with `uv venv` when available. If the created venv lacks `pip`, do not treat it as failure; install packages with `uv pip install --python .venv/bin/python ...`.
4. Read the repo's own quick-start/install notes and install the repo-declared runtime dependencies.
5. Verify imports and hardware backend explicitly, e.g. `torch.__version__` and `torch.backends.mps.is_available()` on Apple Silicon.
6. Run the repo's smallest real data-prep path, then a deliberately tiny training/inference/sampling path. Prefer smoke-test overrides that finish quickly over full training.
7. Read back generated artifacts (`checkpoint`, prepared data, output dirs) and report exact paths plus the command that produced them.

## nanoGPT-shaped example

For `karpathy/nanoGPT` on Apple Silicon:

```bash
cd ~/.hermes/workspace/github/karpathy/nanoGPT
uv venv --python python3.11 .venv
uv pip install --python .venv/bin/python torch numpy transformers datasets tiktoken wandb tqdm
.venv/bin/python data/shakespeare_char/prepare.py
.venv/bin/python train.py config/train_shakespeare_char.py \
  --device=mps --compile=False \
  --eval_iters=2 --eval_interval=2 --log_interval=1 \
  --block_size=32 --batch_size=4 \
  --n_layer=2 --n_head=2 --n_embd=64 \
  --max_iters=4 --lr_decay_iters=4 --dropout=0.0 \
  --out_dir=out-smoke-shakespeare-char --always_save_checkpoint=True
.venv/bin/python sample.py --out_dir=out-smoke-shakespeare-char \
  --device=mps --compile=False --max_new_tokens=80 --num_samples=1
```

Completion evidence should include: remote URL, short commit, venv created, dependency install success, backend availability, data preparation output, checkpoint path, and one real inference/sample output.
