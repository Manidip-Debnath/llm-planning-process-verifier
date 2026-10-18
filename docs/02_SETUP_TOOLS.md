# Setup Guide

Your PC runs Windows. Fast Downward and VAL are easiest on Linux, so use one of these two routes:

- **Route A (recommended for planning tools): WSL2 Ubuntu** on your PC.
- **Route B: Google Colab / Kaggle**, which are already Linux and give you a free GPU.

Plan: run the planning tools (Fast Downward, VAL, label generation) in WSL2 or Colab, and run LLM training / sampling on Colab or Kaggle GPUs.

## 1. WSL2 (Windows only, one time)

In PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu
```

Restart if asked, then open "Ubuntu" from the Start menu and create a user. Your Desktop is reachable from WSL at `/mnt/c/Users/manid/Desktop`.

## 2. Python environment

Inside WSL (or Colab):

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git cmake g++ make
cd /mnt/c/Users/manid/Desktop/AI_Planning_PRM_Project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For heavy work, copy the repo to the Linux filesystem (`~/`) because file access under `/mnt/c` is slow.

## 3. Fast Downward (the solver)

```bash
cd ~
git clone https://github.com/aibasel/downward.git fast-downward
cd fast-downward
python3 build.py
```

Test it on a problem (optimal, A* with LM-cut):

```bash
./fast-downward.py domain.pddl problem.pddl --search "astar(lmcut())"
```

It writes the plan to a file named `sas_plan`. The reported plan cost is the optimal cost.

## 4. VAL (the plan validator)

```bash
cd ~
git clone https://github.com/KCL-Planning/VAL.git
cd VAL
mkdir build && cd build
cmake .. && make -j4
```

The `Validate` binary ends up under the build directory (check `build/` or `build/bin/`). Test:

```bash
Validate -v domain.pddl problem.pddl plan.txt
```

Plan file format, one action per line in parentheses:

```
(unstack a b)
(put-down a)
(pick-up c)
(stack c d)
```

Try a correct plan and a deliberately broken one. VAL's output names the first failing step.

If the build fails, note the error message; version differences are common. Fallback: your own Python STRIPS simulator (Phase 3.2) can validate plans for Blocksworld, and you can note the VAL limitation in the report.

## 5. PDDL generators (optional)

```bash
git clone https://github.com/AI-Planning/pddl-generators.git
```

Each domain folder has its own README with usage. For Blocksworld, writing your own small Python generator is simpler (see the guide, Phase 1.3). Cite the repo if you use it.

## 6. Colab / Kaggle for LLM work

- **Colab:** Runtime > Change runtime type > T4 GPU.
- **Kaggle:** create a notebook, set the accelerator to GPU T4 x2, enable Internet.
- Install in a notebook cell:

```python
!pip install -q transformers peft trl datasets accelerate bitsandbytes
```

- Keep the notebook entry points in `notebooks/` and have them import code from the repo (clone the repo inside the notebook).
- Free sessions disconnect. Save checkpoints and outputs to Google Drive (Colab) or the Kaggle output folder often.

## 7. Models

- Planner: `Qwen/Qwen2.5-3B-Instruct` (fall back to `Qwen/Qwen2.5-1.5B-Instruct` if memory is tight).
- Verifier base: `Qwen/Qwen2.5-0.5B` (or `-Instruct`).
- Use 4-bit loading (`bitsandbytes`) to fit a T4.

Check each model's license on its Hugging Face page and list it in the README's Citations section.

## 8. Quick environment check

```bash
python3 --version
git --version
./fast-downward.py --help | head -3
Validate 2>&1 | head -3
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python3 build.py` fails in Fast Downward | Make sure `cmake`, `g++`, `make` are installed; use Python 3.8+ |
| VAL won't build | Try a different VAL release or the Python simulator fallback |
| Out of GPU memory | 4-bit loading, shorter prompts, smaller batch, or the 1.5B planner |
| Colab disconnects | Save outputs to Drive every run; make scripts resumable |
| Slow file access in WSL | Work in `~/` not `/mnt/c/...` |
