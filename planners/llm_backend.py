"""Text-generation backends: a real Hugging Face model, and a mock for testing.

Both expose:
    generate(messages, n, temperature, max_new_tokens, meta=None)
        -> (list of {"text": str, "tokens": int}, prompt_tokens: int)
`tokens` is the number of newly generated tokens, which is the unit we use to
measure compute.
"""
import json
import random
from pathlib import Path


class HFBackend:
    def __init__(self, model_name, load_4bit=False, chunk=16):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.chunk = chunk
        self.tok = AutoTokenizer.from_pretrained(model_name)
        self.tok.padding_side = "left"
        kwargs = {}
        if torch.cuda.is_available():
            kwargs["device_map"] = "auto"
            kwargs["torch_dtype"] = torch.float16
        if load_4bit:
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4")
        self.model = AutoModelForCausalLM.from_pretrained(model_name, **kwargs)
        self.model.eval()
        if self.tok.pad_token_id is None:
            self.tok.pad_token = self.tok.eos_token
        gen_eos = self.model.generation_config.eos_token_id
        gen_eos = gen_eos if isinstance(gen_eos, list) else [gen_eos]
        self.stop_ids = {i for i in gen_eos if i is not None}
        self.stop_ids.add(self.tok.pad_token_id)

    def _count(self, row):
        n = 0
        for t in row.tolist():
            if t in self.stop_ids:
                return n + 1            # count the stop token itself
            n += 1
        return n

    def generate(self, messages, n=1, temperature=0.0, max_new_tokens=300, meta=None):
        torch = self.torch
        prompt = self.tok.apply_chat_template(messages, tokenize=False,
                                              add_generation_prompt=True)
        enc = self.tok(prompt, return_tensors="pt", add_special_tokens=False).to(self.model.device)
        plen = enc["input_ids"].shape[1]
        results, remaining = [], n
        while remaining > 0:
            k = min(self.chunk, remaining)
            kw = dict(max_new_tokens=max_new_tokens, num_return_sequences=k,
                      pad_token_id=self.tok.pad_token_id)
            if temperature > 0:
                kw.update(do_sample=True, temperature=temperature, top_p=0.95)
            else:
                kw.update(do_sample=False, temperature=None, top_p=None, top_k=None)
                kw["num_return_sequences"] = 1
                k = 1
            with torch.no_grad():
                out = self.model.generate(**enc, **kw)
            new = out[:, plen:]
            texts = self.tok.batch_decode(new, skip_special_tokens=True)
            for text, row in zip(texts, new):
                results.append({"text": text, "tokens": self._count(row)})
            remaining -= k
        return results, plen


class MockBackend:
    """Pretends to be an LLM: returns the optimal plan, corrupted at random.

    Used to test the whole pipeline without a GPU. `error_rate` is the chance
    that a sample is corrupted (dropped step, swapped steps, or truncated).
    """

    def __init__(self, solutions_path, error_rate=0.6, seed=0):
        self.plans = {}
        for line in Path(solutions_path).read_text().splitlines():
            r = json.loads(line)
            if r["solved"]:
                self.plans[r["id"]] = r["plan"]
        self.error_rate = error_rate
        self.rng = random.Random(seed)

    def generate(self, messages, n=1, temperature=0.0, max_new_tokens=300, meta=None):
        plan = self.plans[meta["id"]]
        out = []
        for _ in range(n):
            p = list(plan)
            if self.rng.random() < self.error_rate and len(p) >= 2:
                kind = self.rng.choice(["drop", "swap", "truncate"])
                i = self.rng.randrange(len(p) - 1)
                if kind == "drop":
                    del p[i]
                elif kind == "swap":
                    p[i], p[i + 1] = p[i + 1], p[i]
                else:
                    p = p[:-1]
            text = "Plan:\n" + "\n".join(p)
            out.append({"text": text, "tokens": 6 * len(p)})
        return out, 400
