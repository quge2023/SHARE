import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.utils import get_column_table, get_column_table_spider, save_jsonl, get_abs_path
from src.call_models.call_apis import api_infer
from src.prompts.for_train import sql2sr,sql2sr_shots, spider_sql2sr_shots
import argparse

def get_bird_sql2sr_prompt(bird_data_json_path, bird_table_json_path):
    bird_data_json = json.load(open(bird_data_json_path, 'r'))
    bird_table_json = json.load(open(bird_table_json_path, 'r'))
    prompt_list = []
    for idx, info in enumerate(bird_data_json):
        prompt_dict = {}
        question = info['question']
        evidence = info['evidence']
        sql = info['SQL']
        schema = get_column_table(bird_table_json, info, sql)
        schema = [f"{t}.{c}" for t,c in schema]
        prompt = sql2sr.format(shots = sql2sr_shots, question = question, schema = schema,
                                        evidence = evidence, sql = sql)
        prompt_dict['idx'] = idx
        prompt_dict['prompt'] = prompt
        prompt_list.append(prompt_dict)
    return prompt_list

def get_spider_sql2sr_prompt(spider_data_json_path, spider_table_json_path):
    spider_data_json = json.load(open(spider_data_json_path, 'r'))
    spider_table_json = json.load(open(spider_table_json_path, 'r'))
    prompt_list = []
    for idx, info in enumerate(spider_data_json):
        prompt_dict = {}
        question = info['question']
        evidence = ""
        sql = info['query']
        schema = get_column_table_spider(spider_table_json, info, sql)
        schema = [f"{t}.{c}" for t,c in schema]
        prompt = sql2sr.format(shots = spider_sql2sr_shots, question = question, schema = schema,
                                        evidence = evidence, sql = sql)
   
        prompt_dict['idx'] = idx
        prompt_dict['prompt'] = prompt
        prompt_list.append(prompt_dict)
    return prompt_list

def infer_teacher_data(data_config, intermediate_config):
    bird_data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    bird_table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    spider_data_path = get_abs_path(BASE_DIR, data_config['spider_train_data'])
    spider_table_path = get_abs_path(BASE_DIR, data_config['spider_tables'])
    bird_prompt_list = get_bird_sql2sr_prompt(bird_data_path, bird_table_path)
    spider_prompt_list = get_spider_sql2sr_prompt(spider_data_path, spider_table_path)
    bird_teacher_sql2sr = api_infer(bird_prompt_list)
    spider_teacher_sql2sr = api_infer(spider_prompt_list)
    save_jsonl(bird_teacher_sql2sr, intermediate_config['bird_teacher_sql2sr'])
    save_jsonl(spider_teacher_sql2sr, intermediate_config['spider_teacher_sql2sr'])
    print(f"Collect SR data from the teacher model successfully.")
    
def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    intermediate_config['bird_teacher_sql2sr'] = args.bird_teacher_sql2sr_path
    intermediate_config['spider_teacher_sql2sr'] = args.spider_teacher_sql2sr_path
    infer_teacher_data(data_config, intermediate_config)
    json.dump(intermediate_config, open(args.intermediate_config_path, 'w'), indent=4)

def parse_args():
    parser = argparse.ArgumentParser(description="Generate SR data from the teacher model.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--bird_teacher_sql2sr_path", type=str, required=True, help="Path to save the bird teacher SQL2SR data.")
    parser.add_argument("--spider_teacher_sql2sr_path", type=str, required=True, help="Path to save the spider teacher SQL2SR data.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
