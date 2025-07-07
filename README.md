# SHARE: An SLM-based Hierarchical Action CorREction Assistant for Text-to-SQL

[![Data Link](https://img.shields.io/badge/BIRD-benchmark-green.svg)](https://bird-bench.github.io/)
[![Leaderboard](https://img.shields.io/badge/SPIDER-benchmark-pink.svg)](https://yale-lily.github.io/spider)
[![Python 3.10](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/release/python-31018/)
[![vllm 0.9.1](https://img.shields.io/badge/VLLM-0.9.1-purple.svg)](https://pypi.org/project/vllm/0.9.1/)
[![openai 1.93.0](https://img.shields.io/badge/OpenAI-1.93.0-orange.svg)](https://pypi.org/project/openai/1.93.0/)

This is the official repository for the paper ["SHARE: An SLM-based Hierarchical Action CorREction Assistant for Text-to-SQL"](https://arxiv.org/abs/2506.00391), which has been accepted to ACL Main 2025.

## Overview

<img src="./assets/main.png" align="middle" width="100%">


In this work, we propose an assistant-based framework where generator LLMs create initial outputs and implement self-correction guided by assistants. Our primary contribution, **SHARE** (**S**LM-based **H**ierarchical **A**ction Cor**RE**ction Assistant), orchestrates three specialized Small Language Models (SLMs), each under 8B parameters, in a sequential pipeline. Specifically, the Base Action Model (BAM) transforms raw SQL queries into action trajectories that capture reasoning paths; the Schema Augmentation Model (SAM) and the Logic Optimization Model (LOM) further perform orchestrated inference to rectify schema-related and logical errors, respectively, within action trajectories. SHARE improves error detection precision and correction efficacy while reducing computational overhead compared to conventional LLM approaches. Additionally, we also incorporate a novel hierarchical self-evolution strategy that enhances data efficiency during training.



## Environment Setup

• Use the following command to configure local environment:

   ```bash
    $ conda create -n share python=3.10
    $ conda activate share
    $ pip3 install -r requirements.txt
   ```

• Set environment variables for the Azure OpenAI API or modify your own OpenAI config in `./src/call_models/call_apis.py`:
   ```bash
   export OPENAI_API_BASE="YOUR_OPENAI_API_BASE"
   export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
   export ENGINE_ID="YOUR_ENGINE_ID"
   ```

• Set environment variable to specify which GPU devices are visible to your program:
   ```bash
   export CUDA_VISIBLE_DEVICES="[AVAILABLE_DEVICE_IDS]"
   ```

## Data Preparation
### Bird Dataset
The BIRD dataset used in the paper could be directly downloaded from the [BIRD Leaderboard](https://bird-bench.github.io/). After downloading and unzipping, please place the contents into the following directories: `./data/bird/train/` and `./data/bird/dev/`.

### Spider Dataset
The Spider dataset can be downloaded from the [Spider Leaderboard](https://yale-lily.github.io/spider). After downloading and extracting it, place the contents into: `./data/spider/`

### Column Meaning JSON 
The column_meaning.json file for each dataset is stored under the corresponding path in `./data/`. It is formatted as a Python dictionary, where each key follows the structure `{database_id}|{table_name}|{column_name}`. Each value contains key information about the corresponding column, including summaries of its values derived from the raw CSV files. This file can be directly used during training and inference.


For the expected file structure under each dataset directory, please refer to: `./configs/data_config.json`.

## Infer Results

To directly use the fine-tuned models in SHARE for inference, you can either load them via their model cards from [Models on HuggingFace](https://huggingface.co/gq2138/models), or download the models and place them in the `./model/` directory for local loading.

You could then execute the command line by following the instruction (You may need to adjust paths and parameters with your preference.):
```
$ sh ./scripts/run_inference.sh
```

In this script, as described in Section 3.5, we execute the SHARE workflow to generate refined action trajectories for each instance. These refined trajectories then serve as self-correction signals, enabling the language model to regenerate more accurate and contextually appropriate SQL queries. Outputs during inference are stored in `./outputs/infer/`. 

## Train From Scratch
To train the three models used in SHARE from scratch, you could either use the corresponding processed training data available on [HuggingFace Datasets](https://huggingface.co/gq2138/datasets), or generate the training data locally by running the provided data processing scripts. For example, to generate the training data for the BAM module, run:
```
$ sh ./scripts/get_bam_data.sh
```
All the generated data will be stored in `./ft_data/`. We adopt [LlamaFactory](https://github.com/hiyouga/LLaMA-Factory) as the primary framework for model training. An example training script is provided in `./scripts/example_train.sh`, which can be customized by modifying parameters and file paths to suit your specific needs.

## Evaluation
We follow the official evaluation methods proposed by the [BIRD](https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/bird) and [SPIDER](https://github.com/taoyds/spider). The corresponding evaluation scripts can be obtained from their official code repositories.
