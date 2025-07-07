import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.prompts.for_train import system_prompt, sql2sr_user_prompt, assistant_prompt
from src.utils import get_column_table, get_column_table_spider, re_keywords, load_jsonl, save_data_to_fac, get_abs_path
import argparse

def get_bird_bam_train(data_json_path, table_json_path, validated_sr_jsonl_path):
    data_json = json.load(open(data_json_path, 'r'))
    table_json = json.load(open(table_json_path, 'r'))
    validated_sr_jsonl = load_jsonl(validated_sr_jsonl_path)
    
    message_list = []
    for idx, info in enumerate(validated_sr_jsonl):
        if info["flag"] == 0: continue
        content = data_json[idx]
        sql = content['SQL']
        schema = get_column_table(table_json, content, sql)
        schema = [f"{t}.{c}" for t,c in schema]
        sr = info['sr']
        user_prompt = sql2sr_user_prompt.format(schema = schema, sql = sql)
        final_assistant_prompt = assistant_prompt.format(sr = sr)
        message = {
            'instruction': user_prompt,
            'output': final_assistant_prompt,
            'system': system_prompt
        }
        message_list.append(message)
    return message_list

def get_spider_bam_train(data_json_path, table_json_path, validated_sr_jsonl_path):
    data_json = json.load(open(data_json_path, 'r'))
    table_json = json.load(open(table_json_path, 'r'))
    validated_sr_jsonl = load_jsonl(validated_sr_jsonl_path)
    
    message_list = []
    for idx, info in enumerate(validated_sr_jsonl):
        if info["flag"] == 0: continue
        content = data_json[idx]
        sql = content['query']
        tmp_schema = get_column_table_spider(table_json, content, sql)
        schema = [f"{t}.{c}" for t,c in tmp_schema]
        if '*' in sql:
            tmp_table = [t for t, c in tmp_schema]
            tmp_star = [f"{t}.*" for t in tmp_table]
            schema = tmp_star + schema
        sr = info['sr']
        user_prompt = sql2sr_user_prompt.format(schema = schema, sql = sql)
        final_assistant_prompt = assistant_prompt.format(sr = sr)
        message = {
            'instruction': user_prompt,
            'output': final_assistant_prompt,
            'system': system_prompt
        }
        message_list.append(message)
    return message_list

def generate_bam_train_data(data_config, intermediate_config, file_name):
    bird_data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    bird_table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    bird_validated_sr_path = intermediate_config['bird_validated_sr']
    spider_data_path = get_abs_path(BASE_DIR, data_config['spider_train_data'])
    spider_table_path = get_abs_path(BASE_DIR, data_config['spider_tables'])
    spider_validated_sr_path = intermediate_config['spider_validated_sr']
    ft_data_dir = get_abs_path(BASE_DIR, data_config['ft_data_dir'])
    
    bird_data_list = get_bird_bam_train(bird_data_path, bird_table_path, bird_validated_sr_path)
    spider_data_list = get_spider_bam_train(spider_data_path, spider_table_path, spider_validated_sr_path)
    data_list = bird_data_list + spider_data_list
    save_data_to_fac(data_list, ft_data_dir, file_name)


def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    file_name = "bam_train_data"
    generate_bam_train_data(data_config, intermediate_config, file_name)

def parse_args():
    parser = argparse.ArgumentParser(description="Training data of BAM.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--bam_train_data_name", type=str, required=True, help="File name of the data.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)
    
    
    