# Research Notes: RLHF Alignment of Large Language Models

## 1. Context
This repository documents my study of reinforcement learning from human feedback (RLHF) as preparation for a doctoral pathway. The project addresses the alignment of large language models (LLMs) with external feedback through reinforcement-learning-based methods, with particular attention to (i) the robustness of alignment procedures, (ii) multi-objective alignment across potentially conflicting feedback signals, and (iii) statistical perspectives on policy optimization. 

## 2. Learning Resources

Video/course material used alongside coursework and papers, grouped to match the repository map below.

**RL foundations**
- [RL Course by David Silver (DeepMind)](https://www.youtube.com/playlist?list=PLeJKOhW5z62XKURemUDc3N92Min9yaR12) — MDPs, dynamic programming, TD learning, policy gradients.
- [Stanford CS234: Reinforcement Learning](https://www.youtube.com/playlist?list=PLCH_MtKnU6rXoFJkxfUoeMzU9_CPwdjLq) — more rigorous/current pass, esp. function approximation and policy gradients.

**Deep learning / language models**
- [Andrej Karpathy — Neural Networks: Zero to Hero](https://www.youtube.com/playlist?list=PLAqhIrjkxbuWI23v9cThsA9GvCAUhRvKZ) — backprop through a from-scratch GPT.
- [Andrej Karpathy — Let's build GPT: from scratch, in code, spelled out](https://www.youtube.com/watch?v=Ts9151A9X94) — produces the base policy model an RLHF pipeline would fine-tune.
- [3Blue1Brown — Neural networks / attention series](https://www.youtube.com/playlist?list=PLZZWrBYkx7Otcjr3eCLZDCgfpqnxMY29s) — visual intuition for attention/transformers.

**Math foundations**
- [3Blue1Brown — Essence of Linear Algebra](https://www.youtube.com/playlist?list=PLZHQObOWTQDPD3MizzM2xVFitgF8hE_ab)
- [StatQuest with Josh Starmer](https://www.youtube.com/@statquest/playlists) — probability/statistics playlists underpinning the statistical-RL reading.

**RLHF algorithms (PPO / DPO / GRPO)**
- [Proximal Policy Optimization (PPO) for LLMs Explained Intuitively](https://www.youtube.com/watch?v=8jtAzxUwDj0)
- [Direct Preference Optimization (DPO) | Paper Explained](https://www.youtube.com/watch?v=TfybkCFQufc)
- [PPO & GRPO | Math Explained](https://www.youtube.com/watch?v=5ChE_UPNN78) — ties directly to the DeepSeekMath reference below.
- [CleanRL — PPO implementation reference](https://docs.cleanrl.dev/rl-algorithms/ppo/) — single-file implementation style used for prototypes.
- [Hugging Face — A Guide to RL Post-Training for LLMs: PPO, DPO, GRPO, and Beyond](https://huggingface.co/blog/karina-zadorozhny/guide-to-llm-post-training-algorithms) — written comparison of the three algorithms above.

## 5. Repository Map

Supporting coursework and project material with mini prototype:

```
docs/
├── projects/          PPO implementation notes and presentation (prior hands-on RL work)
├── courses/
│   ├── ai-introduction/   Search, logic, knowledge representation, KNN, Naive Bayes
│   └── deep-learning/     Neural network foundations
└── math/
    ├── algebra/           Linear algebra foundations
    └── probabilistics/    Probability foundations for statistical RL
src/
├── rl-foundations/    Bandits, tabular Q-learning, REINFORCE (mini prototypes)
└── deep-learning/     Backprop, MLP, from-scratch mini-GPT (mini prototypes)
```

## References

1. Schulman, J., Wolski, F., Dhariwal, P., Radford, A., & Klimov, O. (2017). Proximal Policy Optimization Algorithms. *arXiv:1707.06347*.
2. Rafailov, R., Sharma, A., Mitchell, E., Ermon, S., Manning, C. D., & Finn, C. (2023). Direct Preference Optimization: Your Language Model is Secretly a Reward Model. *arXiv:2305.18290*.
3. Shao, Z., Wang, P., Zhu, Q., Xu, R., Song, J., Zhang, M., Li, Y. K., Wu, Y., & Guo, D. (2024). DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models. *arXiv:2402.03300*.
