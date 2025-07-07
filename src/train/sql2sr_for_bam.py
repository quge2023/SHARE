import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.prompts.for_train import system_prompt, sql2sr_user_prompt, assistant_prompt
from src.call_models.vllm_infer import infer_batch
from src.utils import get_column_table, get_abs_path, save_jsonl
import argparse


def generate_bam_infer_data(data_json_path, table_json_path, baseline_sql_json_path):
    # Generate the prompt for bam to infer the SR of baseline SQL for training set.
    # The training data of SAM and LOM is derived from the corresponding inference result. 
    data_json = json.load(open(data_json_path, 'r'))
    table_json = json.load(open(table_json_path, 'r'))
    baseline_sql_json = json.load(open(baseline_sql_json_path, 'r'))
    prompt_list = []
    for idx, info in enumerate(data_json):
        sql = baseline_sql_json[str(idx)].split('\t')[0].replace('\n', ' ')
        schema = get_column_table(table_json, info, sql)
        schema = [f"{t}.{c}" for t, c in schema]
        user_prompt = sql2sr_user_prompt.format(schema=schema, sql=sql)
        prompt_list.append({'idx':idx, 'prompt': user_prompt})
    return prompt_list

def get_bam_train_data(data_config, intermediate_config, bam_path):
    data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    baseline_sql_path = get_abs_path(BASE_DIR, data_config['bird_train_baseline'])
    data_items = generate_bam_infer_data(data_path, table_path, baseline_sql_path)
    prompts = [item['prompt'] for item in data_items]
    infer_list = infer_batch(bam_path, prompts, data_items, system_prompt)
    save_jsonl(infer_list, intermediate_config['bam_baseline_sql2sr'])
    print(f"Infer baseline SQL to SR of train set using BAM successfully.")

def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    intermediate_config['bam_baseline_sql2sr'] = args.bam_baseline_sql2sr_path
    get_bam_train_data(data_config, intermediate_config, args.bam_model_path)
    json.dump(intermediate_config, open(args.intermediate_config_path, 'w'), indent=4)
    
def parse_args():
    parser = argparse.ArgumentParser(description="Generate baseline SQL to SR of train set using BAM.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--bam_baseline_sql2sr_path", type=str, required=True, help="Path to save the bam baseline SQL2SR data.")
    parser.add_argument("--bam_model_path", type=str, required=True, help="Path of BAM model.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)