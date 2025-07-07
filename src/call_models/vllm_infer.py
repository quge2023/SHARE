
import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
import torch
import jsonlines
from tqdm import tqdm
from vllm import LLM, SamplingParams
import argparse
from src.utils import save_jsonl

MAX_INT = sys.maxsize
MAX_TRY = 10
INVALID_ANS = "[INVALID]"


def filter_output(response):
    if len(response.strip()) <= 1:
        return None
    return response


def process_batch_data(data_list, batch_size=1):
    num_batches = len(data_list) // batch_size
    batches = []
    for i in range(num_batches - 1):
        start = i * batch_size
        end = (i + 1) * batch_size
        batches.append(data_list[start:end])
    last_start = (num_batches - 1) * batch_size
    batches.append(data_list[last_start:MAX_INT])
    return batches


def append_response_to_file(data_items, generated_texts, output_file,idx):
    mode = 'a' if idx!=0 else 'w'
    with jsonlines.open(output_file, mode=mode) as writer:
        for item, gen_text in zip(data_items, generated_texts):
            item["response"] = gen_text
            writer.write(item)


def infer_batch(model_path, prompts, data_items, system_prompt = None,
                max_token_length=8192, batch_size=100, phase="", limit=None):
    
    if not limit:
        prompts = prompts[limit:]
        data_items = data_items[limit:]
        
    # prompts = prompts[:10]
    # data_items = data_items[:10]

    print("First prompt example:", prompts[0], flush=True)
    print("Number of samples to infer:", len(prompts))

    
    prompt_batches = process_batch_data(prompts, batch_size=batch_size)
    data_batches = process_batch_data(data_items, batch_size=batch_size)



    llm = LLM(
        model=model_path,
        tensor_parallel_size=4,
        trust_remote_code=True,
        gpu_memory_utilization=0.95,
        max_model_len=max_token_length,
    )

    tokenizer = llm.get_tokenizer()
    stop_tokens = ["</FINAL_ANSWER>", "<|EOT|>"]
    sampling_params = SamplingParams(
        temperature=0.0,
        top_p=1.0,
        max_tokens=3000,
        presence_penalty=0.0,
        frequency_penalty=0.0,
        stop=stop_tokens,
        stop_token_ids=[tokenizer.eos_token_id],
    )
    print("Sampling Params:", sampling_params)

    all_data_with_responses = []
    for idx, (prompts_in_batch, items_in_batch) in enumerate(
        tqdm(zip(prompt_batches, data_batches))
    ):
        print(f"Inferencing batch {idx}...", flush=True)
        if not isinstance(prompts_in_batch, list):
            prompts_in_batch = [prompts_in_batch]

        if not system_prompt:
            conversations = [
            tokenizer.apply_chat_template(
                [{"role": "user", "content": prompt}],
                tokenize=False,
                add_generation_prompt=True,
            )
            for prompt in prompts_in_batch
        ]
        else:
            conversations = [
                tokenizer.apply_chat_template(
                    [   {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}],
                    tokenize=False,
                    add_generation_prompt=True,
                )
                for prompt in prompts_in_batch
            ]
        
        invalid_response = True
        attempts = 0
        completions = None

        while invalid_response:
            attempts += 1
            with torch.no_grad():
                completions = llm.generate(conversations, sampling_params)
            for completion in completions:
                generated_text = completion.outputs[0].text
                if not filter_output(generated_text):
                    invalid_response = True
                    break
                else:
                    invalid_response = False
            if attempts > MAX_TRY:
                print("Exceeded max invalid output attempts.")
                invalid_response = False

        batch_generated_texts = []
        for completion in completions:
            generated_text = completion.outputs[0].text
            if not filter_output(generated_text):
                generated_text = INVALID_ANS
            batch_generated_texts.append(generated_text)
        for item, gen_text in zip(items_in_batch, batch_generated_texts):
            item["response"] = gen_text
            all_data_with_responses.append(item)
        
    print("All batch inference completed.")
    return all_data_with_responses

if __name__ == "__main__":
    model_path = '/home/qinbowen/just_malou/gq2138/share/model/lom'
    prompt_path = '/home/qinbowen/just_malou/gq2138/share_tmp/res/prompts/tmp_infer/sr2sr.jsonl'
    # output_path = '/home/qinbowen/just_malou/gq2138/share/res/outputs/tmp_infer/sr2sr.jsonl'
    output_path = '/home/qinbowen/just_malou/gq2138/share_tmp/res/outputs/tmp_infer/test.jsonl'
    
    os.environ["CUDA_VISIBLE_DEVICES"] = '4,5,6,7'
    
    system_prompt = "You are an expert about text-to-SQL and pandas code."
    
    data_items = []
    prompts = []
    with open(prompt_path, "r") as f:
        for idx, item in enumerate(jsonlines.Reader(f)):
            prompts.append(item["prompt"])
            data_items.append(item)
            
    infer_list = infer_batch(
        model_path, prompts, data_items, system_prompt = system_prompt
    )
    save_jsonl(infer_list, output_path)