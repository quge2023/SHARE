import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

from src.utils import get_column_table, get_column_table_spider, re_keywords, generate_pk_fk, save_jsonl, load_jsonl, get_abs_path
import json
from src.prompts.for_train import sr2sql_check, spider_sr2sql_check
from src.call_models.call_apis import api_infer
import argparse


def get_bird_sr2sql_prompt(bird_data_json_path, bird_table_json_path, bird_sql2sr_jsonl_path):
    bird_data_json = json.load(open(bird_data_json_path, 'r'))
    bird_table_json = json.load(open(bird_table_json_path, 'r'))
    bird_sql2sr_jsonl = load_jsonl(bird_sql2sr_jsonl_path)
    prompt_list = []
    for idx, content in enumerate(bird_sql2sr_jsonl):
        info = bird_data_json[idx]
        question = info['question']
        evidence = info['evidence']
        sql = info['SQL']
        schema = get_column_table(bird_table_json, info, sql)
        schema = [f"{t}.{c}" for t,c in schema]
        _,fk_dict = generate_pk_fk(info, bird_table_json)
        sr_response = content['response']
        sr = re_keywords(sr_response, 'SR')
        prompt = sr2sql_check.format(question = question, schema = schema,
                                    evidence = evidence, SR=sr, fk_dic=fk_dict)
        prompt_list.append({
            'idx': idx,
            'prompt': prompt
        })
    return prompt_list

def get_spider_sr2sql_prompt(spider_data_json_path, spider_table_json_path, spider_sql2sr_jsonl_path):
    spider_data_json = json.load(open(spider_data_json_path, 'r'))
    spider_table_json = json.load(open(spider_table_json_path, 'r'))
    spider_sql2sr_jsonl = load_jsonl(spider_sql2sr_jsonl_path)
    prompt_list = []
    for idx, content in enumerate(spider_sql2sr_jsonl):
        info = spider_data_json[idx]
        question = info['question']
        evidence = ""
        sql = info['query']
        schema = get_column_table_spider(spider_table_json, info, sql)
        schema = [f"{t}.{c}" for t,c in schema]
        _,fk_dict = generate_pk_fk(info, spider_table_json)
        sr_response = content['response']
        sr = re_keywords(sr_response, 'SR')
        prompt = spider_sr2sql_check.format(question = question, schema = schema,
                                    evidence = evidence, SR=sr, fk_dic=fk_dict)
        prompt_list.append({
            'idx': idx,
            'prompt': prompt
        })
    return prompt_list

def infer_teacher_data(data_config, intermediate_config):
    bird_data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    bird_table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    spider_data_path = get_abs_path(BASE_DIR, data_config['spider_train_data'])
    spider_table_path = get_abs_path(BASE_DIR, data_config['spider_tables'])
    bird_sql2sr_path = intermediate_config['bird_teacher_sql2sr']
    spider_sql2sr_path = intermediate_config['spider_teacher_sql2sr']
    bird_prompt_list = get_bird_sr2sql_prompt(bird_data_path, bird_table_path, bird_sql2sr_path)
    spider_prompt_list = get_spider_sr2sql_prompt(spider_data_path, spider_table_path, spider_sql2sr_path)
    bird_converted_sql = api_infer(bird_prompt_list)
    spider_converted_sql = api_infer(spider_prompt_list)
    save_jsonl(bird_converted_sql, intermediate_config['bird_converted_sql'])
    save_jsonl(spider_converted_sql, intermediate_config['spider_converted_sql'])
    print("SR convertion Done.")

def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    intermediate_config['bird_converted_sql'] = args.bird_converted_sql_path
    intermediate_config['spider_converted_sql'] = args.spider_converted_sql_path
    infer_teacher_data(data_config, intermediate_config)
    json.dump(intermediate_config, open(args.intermediate_config_path, 'w'), indent=4)

def parse_args():
    parser = argparse.ArgumentParser(description="Generate Converted SQL from the SR.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--bird_converted_sql_path", type=str, required=True, help="Path to save the bird converted SQL.")
    parser.add_argument("--spider_converted_sql_path", type=str, required=True, help="Path to save the spider converted SQL.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
    