import tempfile
import unittest
from pathlib import Path

import torch

from backend.model.architecture.decoder import MedhaDecoderLM
from backend.model.config import ModelConfig
from backend.training.dataset import load_texts, make_causal_examples


class CoreTests(unittest.TestCase):
    def test_decoder_forward_shape(self):
        config = ModelConfig(vocab_size=64, embedding_dim=32, num_heads=4,
                             hidden_dim=64, num_layers=2, max_length=16, dropout=0.0)
        model = MedhaDecoderLM(config)
        logits = model(torch.randint(0, config.vocab_size, (2, 8)))
        self.assertEqual(tuple(logits.shape), (2, 8, config.vocab_size))

    def test_decoder_rejects_context_overflow(self):
        config = ModelConfig(vocab_size=32, embedding_dim=16, num_heads=4,
                             hidden_dim=32, num_layers=1, max_length=4, dropout=0.0)
        model = MedhaDecoderLM(config)
        with self.assertRaises(ValueError):
            model(torch.ones((1, 5), dtype=torch.long))

    def test_causal_examples_support_overlap(self):
        examples = make_causal_examples(list(range(12)), block_size=4, stride=2)
        self.assertEqual(examples[0], ([0, 1, 2, 3], [1, 2, 3, 4]))
        self.assertEqual(examples[1], ([2, 3, 4, 5], [3, 4, 5, 6]))

    def test_dataset_excludes_generated_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.md").write_text("train me", encoding="utf-8")
            (root / "models").mkdir()
            (root / "models" / "bad.md").write_text("do not train", encoding="utf-8")
            self.assertEqual(load_texts(root), ["train me"])

    def test_agent_loop_requires_verification_when_requested(self):
        from backend.brain.agent_loop import run_loop
        result = run_loop(
            "open and verify",
            ["open", "verify"],
            lambda step: f"done:{step}",
            verify=lambda step, observation: step == "open",
        )
        self.assertFalse(result.completed)
        self.assertEqual(result.failed_step, 1)

    def test_agent_loop_retries_failed_verification_once(self):
        from backend.brain.agent_loop import run_loop
        attempts = {"n": 0}

        def execute(step):
            attempts["n"] += 1
            return "bad" if attempts["n"] == 1 else "good"

        result = run_loop(
            "test", ["step"], execute, verify=lambda s, o: o == "good"
        )
        self.assertTrue(result.completed)
        self.assertEqual(attempts["n"], 2)


if __name__ == "__main__":
    unittest.main()
