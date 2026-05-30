# LoRA: Low-Rank Adaptation of Large Language Models

## Abstract

An important paradigm of natural language processing consists of large-scale pre-training on general domain data and adaptation to particular tasks or domains. As we pre-train larger models, full fine-tuning, which retrains all model parameters, becomes less feasible. We propose Low-Rank Adaptation, or LoRA, which freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture, greatly reducing the number of trainable parameters for downstream tasks.

## Introduction

Many applications in natural language processing rely on adapting one large-scale, pre-trained language model to multiple downstream applications. Such adaptation is usually done via fine-tuning, which updates all the parameters of the pre-trained model. The major downside of fine-tuning is that the new model contains as many parameters as the original model.

LoRA addresses this by representing the weight updates with two much smaller matrices through low-rank decomposition. The key observation motivating LoRA is that the learned over-parametrized models in fact reside on a low intrinsic dimension. We hypothesize that the change in weights during model adaptation also has a low intrinsic rank.

## Method

For a pre-trained weight matrix W ∈ R^{d×k}, we constrain its update by representing the latter with a low-rank decomposition W + ΔW = W + BA, where B ∈ R^{d×r}, A ∈ R^{r×k}, and the rank r << min(d, k). During training, W is frozen and does not receive gradient updates, while A and B contain trainable parameters.

### Parameter-Efficient Responsibility Distribution

The low-rank constraint in LoRA has a profound implication for how learning is distributed across the model. Rather than distributing the learning signal uniformly across all d×k parameters of a weight matrix, LoRA forces the adaptation to be expressed through only r×(d+k) parameters. This compression forces the model to find the most efficient subspace for task adaptation.

The rank r acts as a bottleneck that concentrates the learning signal. Higher-impact directions in parameter space receive more of the limited representational budget. This is analogous to a form of implicit regularization where the model must identify which directions of change matter most for the downstream task. The low-rank structure ensures that the model cannot waste capacity on directions that contribute marginally to task performance.

This efficient distribution of learning responsibility across a compressed parameter space means that each trainable parameter in LoRA carries more semantic weight than a corresponding parameter in full fine-tuning. The gradient signal for each parameter is effectively amplified by the rank constraint.

## Results

LoRA achieves comparable or better performance than full fine-tuning on a variety of NLP benchmarks while reducing the number of trainable parameters by up to 10,000x and the GPU memory requirement by 3x. When applied to GPT-3 175B, LoRA reduces trainable parameters from 175 billion to 4.7 million (with r=4) while maintaining task performance.

## Advantages

1. A pre-trained model can be shared and used to build many small LoRA modules for different tasks. We can freeze the shared model and efficiently switch tasks by replacing the matrices A and B.

2. LoRA makes training more efficient and lowers the hardware barrier to entry by up to 3 times when using adaptive optimizers since we do not need to calculate the gradients or maintain the optimizer states for most parameters.

3. Our simple linear design allows us to merge the trainable matrices with the frozen weights when deployed, introducing no inference latency.

## Limitations

The rank r is a hyperparameter that must be chosen. Too low a rank may underfit certain tasks, while too high a rank reduces the efficiency gains. The optimal rank depends on the complexity of the task-specific adaptation needed.
