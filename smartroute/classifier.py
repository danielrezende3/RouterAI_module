# TODO: Make it cpu or gpu agnostic
import asyncio

import numpy as np
import torch
import torch.nn as nn
from huggingface_hub import PyTorchModelHubMixin
from transformers import AutoConfig, AutoModel, AutoTokenizer


class MeanPooling(nn.Module):
    def __init__(self):
        super(MeanPooling, self).__init__()

    def forward(self, last_hidden_state, attention_mask):
        input_mask_expanded = (
            attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
        )
        sum_embeddings = torch.sum(last_hidden_state * input_mask_expanded, 1)
        sum_mask = input_mask_expanded.sum(1)
        sum_mask = torch.clamp(sum_mask, min=1e-9)
        mean_embeddings = sum_embeddings / sum_mask
        return mean_embeddings


class MulticlassHead(nn.Module):
    def __init__(self, input_size, num_classes):
        super(MulticlassHead, self).__init__()
        self.fc = nn.Linear(input_size, num_classes)

    def forward(self, x):
        return self.fc(x)


class CustomModel(nn.Module, PyTorchModelHubMixin):
    def __init__(self, target_sizes, task_type_map, weights_map, divisor_map):
        super(CustomModel, self).__init__()
        self.backbone = AutoModel.from_pretrained("microsoft/DeBERTa-v3-base")
        self.target_sizes = target_sizes.values()
        self.task_type_map = task_type_map
        self.weights_map = weights_map
        self.divisor_map = divisor_map

        # Create a head for each target size
        self.heads = [
            MulticlassHead(self.backbone.config.hidden_size, sz)
            for sz in self.target_sizes
        ]
        for i, head in enumerate(self.heads):
            self.add_module(f"head_{i}", head)

        self.pool = MeanPooling()

    def compute_results(self, preds, target, decimal=4):
        if target == "task_type":
            top2_indices = torch.topk(preds, k=2, dim=1).indices
            softmax_probs = torch.softmax(preds, dim=1)
            top2_probs = softmax_probs.gather(1, top2_indices)
            top2 = top2_indices.detach().cpu().tolist()
            top2_prob = top2_probs.detach().cpu().tolist()
            top2_strings = [
                [self.task_type_map[str(idx)] for idx in sample] for sample in top2
            ]
            top2_prob_rounded = [
                [round(value, 3) for value in sublist] for sublist in top2_prob
            ]
            for i, sublist in enumerate(top2_prob_rounded):
                if sublist[1] < 0.1:
                    top2_strings[i][1] = "NA"
            task_type_1 = [s[0] for s in top2_strings]
            task_type_2 = [s[1] for s in top2_strings]
            task_type_prob = [s[0] for s in top2_prob_rounded]
            return (task_type_1, task_type_2, task_type_prob)
        else:
            preds = torch.softmax(preds, dim=1)
            weights = np.array(self.weights_map[target])
            weighted_sum = np.sum(np.array(preds.detach().cpu()) * weights, axis=1)
            scores = weighted_sum / self.divisor_map[target]
            scores = [round(value, decimal) for value in scores]
            if target == "number_of_few_shots":
                scores = [x if x >= 0.05 else 0 for x in scores]
            return scores

    def process_logits(self, logits):
        result = {}
        # Round 1: "task_type"
        task_type_logits = logits[0]
        task_type_results = self.compute_results(task_type_logits, target="task_type")
        result["task_type_1"] = task_type_results[0]
        result["task_type_2"] = task_type_results[1]
        result["task_type_prob"] = task_type_results[2]

        # Rounds 2-8 for other scores
        targets = [
            "creativity_scope",
            "reasoning",
            "contextual_knowledge",
            "number_of_few_shots",
            "domain_knowledge",
            "no_label_reason",
            "constraint_ct",
        ]
        for i, target in enumerate(targets, start=1):
            result[target] = self.compute_results(logits[i], target=target)

        # Round 9: prompt_complexity_score (weighted sum of several scores)
        result["prompt_complexity_score"] = [
            round(
                0.35 * creativity
                + 0.25 * reasoning
                + 0.15 * constraint
                + 0.15 * domain_knowledge
                + 0.05 * contextual_knowledge
                + 0.05 * few_shots,
                5,
            )
            for creativity, reasoning, constraint, domain_knowledge, contextual_knowledge, few_shots in zip(
                result["creativity_scope"],
                result["reasoning"],
                result["constraint_ct"],
                result["domain_knowledge"],
                result["contextual_knowledge"],
                result["number_of_few_shots"],
            )
        ]
        return result

    def forward(self, batch):
        input_ids = batch["input_ids"]
        attention_mask = batch["attention_mask"]
        outputs = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        last_hidden_state = outputs.last_hidden_state
        mean_pooled_representation = self.pool(last_hidden_state, attention_mask)
        logits = [head(mean_pooled_representation) for head in self.heads]
        return self.process_logits(logits)


model_name = "nvidia/prompt-task-and-complexity-classifier"
config = AutoConfig.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = CustomModel(
    target_sizes=config.target_sizes,
    task_type_map=config.task_type_map,
    weights_map=config.weights_map,
    divisor_map=config.divisor_map,
).from_pretrained(model_name)
model.eval()


def classify_prompt(prompt: str) -> dict:
    """
    Tokenizes the prompt and returns the classifier's output dictionary.
    """
    inputs = tokenizer(
        [prompt],
        return_tensors="pt",
        add_special_tokens=True,
        max_length=512,
        padding="max_length",
        truncation=True,
    )
    with torch.no_grad():
        result = model(inputs)
    return result


def decide_tier(
    classification_result: dict,
    threshold_fast: float = 0.3,
    threshold_mid: float = 0.42,
) -> str:
    """
    Uses the classifier's `prompt_complexity_score` to decide on a tier model.

    Args:
        classification_result (dict): Output from the complexity classifier.
        threshold_fast (float): Upper threshold for using the fast tier.
        threshold_mid (float): Upper threshold for using the mid tier.

    Returns:
        str: One of "fast", "mid", or "reasoning".
    """
    # Assuming the result contains a list with one float score.
    score = classification_result.get("prompt_complexity_score", [0])[0]
    if score < threshold_fast:
        return "fast"
    elif score < threshold_mid:
        return "mid"
    else:
        return "reasoning"


semaphore = asyncio.Semaphore(3)


async def async_classify_prompt(prompt: str) -> dict:
    # Acquire the semaphore before proceeding.
    async with semaphore:
        # Offload the blocking classifier call to a thread.
        return await asyncio.to_thread(classify_prompt, prompt)
