# Direct Preference Optimization: Your Language Model is Secretly a Reward Model

## Abstract

While large-scale unsupervised language models learn broad world knowledge and some reasoning skills, achieving precise control of their behavior is difficult due to the completely unsupervised nature of their training. Existing methods for gaining such steerability collect human labels of the relative quality of model generations, train a reward model on these preferences, and then fine-tune the language model with reinforcement learning to maximize the estimated reward without drifting too far from the reference model.

## Introduction

Large language models demonstrate remarkable capabilities but controlling their behavior remains challenging. Reinforcement learning from human feedback (RLHF) has emerged as the primary method for aligning language models with human preferences, but the pipeline is complex, involving multiple models and training stages.

## Method

Direct Preference Optimization (DPO) implicitly optimizes the same objective as existing RLHF algorithms (reward maximization with a KL-divergence constraint) but is simple to implement and straightforward to train. Intuitively, the DPO update increases the relative log probability of preferred to dispreferred responses, but it incorporates a dynamic, per-example importance weight that prevents the model degeneration that naive probability ratio objectives suffer from.

### Reward Shaping and Distributional Alignment

The core insight of DPO is that the optimal policy under a KL-constrained reward maximization objective can be expressed in closed form as a function of the reward model and reference policy. This means that instead of first learning a reward model and then optimizing against it, we can directly optimize the policy using preference data.

The reward signal in DPO is shaped by the preference pairs. Each pair (preferred response, dispreferred response) provides a comparative signal about which behaviors are desirable. The model learns to assign higher probability to preferred responses relative to dispreferred ones, effectively learning a reward function implicitly through its own log probabilities.

This approach to reward shaping avoids many challenges of explicit reward modeling, including reward hacking (where the policy exploits inaccuracies in the reward model) and the instability of reinforcement learning optimization. By directly connecting preferences to policy updates, DPO ensures that the reward signal faithfully reflects human judgments.

### Distributing Responsibility Across Parameters

The DPO loss distributes the learning signal across the model's parameters in proportion to how much each parameter contributes to the probability gap between preferred and dispreferred completions. Parameters that have high influence on distinguishing preferred from dispreferred outputs receive stronger gradient signals. This automatic attribution of responsibility across the parameter space is a key advantage over RL-based methods where the reward signal must be propagated through a more complex computational graph.

## Results

DPO matches or exceeds the performance of existing RLHF methods on tasks including sentiment control, summarization, and dialogue. On the TL;DR summarization task, DPO achieves comparable quality to PPO-based RLHF while being significantly simpler to implement and more stable to train.

## Limitations

DPO assumes access to preference data that accurately reflects desired behavior. The quality of alignment is bounded by the quality and coverage of the preference dataset. Additionally, DPO requires paired comparisons and cannot easily incorporate scalar reward signals or online interaction.
