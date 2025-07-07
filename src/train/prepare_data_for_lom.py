import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.prompts.for_train import system_prompt, error_perturbation_prompt, sr2sr_user_prompt, assistant_prompt
from src.call_models.vllm_infer import infer_batch
from src.train.sr_validation import evaluate_sql
from src.utils import get_column_table, get_column_meanings, re_keywords, check_schema, load_jsonl, save_jsonl, get_abs_path, save_data_to_fac
import argparse


def read_sqls(data_json, baseline_sql_json, db_dir):
    clean_sqls, clean_gold_sqls = [], []
    db_path_list = []
    for idx_key, baseline_sql in list(baseline_sql_json.items()):
        idx = int(idx_key)
        clean_sqls.append(baseline_sql)
        info = data_json[idx]
        gold_sql = info['SQL']
        clean_gold_sqls.append(gold_sql)
        db_id = info['db_id']
        db_path = os.path.join(db_dir, db_id, db_id + '.sqlite' )
        db_path_list.append(db_path)
    return clean_sqls, clean_gold_sqls, db_path_list

def get_distribution(data_json, table_json, baseline_sql_json, validated_sr_jsonl, db_dir):
    baseline_sqls, gold_sqls, db_paths = read_sqls(data_json, baseline_sql_json, db_dir)
    baseline_sql_exec = evaluate_sql(baseline_sqls, gold_sqls, db_paths)
    
    pos_idx, neg_idx = [], []
    for idx, info in enumerate(baseline_sql_exec):
        if validated_sr_jsonl[idx]['flag'] == 0: continue
        baseline_sql = baseline_sql_json[str(idx)]
        data_info = data_json[idx]
        schema_flag = check_schema(table_json, data_info, baseline_sql)
        if schema_flag == True and info['exec_flag'] == 0:
            pos_idx.append(idx)
        if schema_flag == True and info['exec_flag'] == 1:
            neg_idx.append(idx)
    print(f"The pos count is {len(pos_idx)}, the neg count is {len(neg_idx)}.")
    pos_idx = sorted(pos_idx)
    neg_idx = sorted(neg_idx)
    return pos_idx, neg_idx

def generate_perturbation_prompt(data_json, table_json, column_meaning_json, baseline_sr_jsonl, neg_idx):
    infer_data = []
    for idx in neg_idx:
        info = data_json[idx]
        question = info['question']
        evidence = info['evidence']
        baseline_sr = re_keywords(baseline_sr_jsonl[idx]['response'], "SR")
        schema = get_column_table(table_json, info, baseline_sr)
        schema = [f"{t}.{c}" for t,c in schema]
        column_description = get_column_meanings(info, table_json, baseline_sr, column_meaning_json)
        user_prompt = error_perturbation_prompt.format(schema = schema, column_description=column_description, question=question, evidence=evidence, sr=baseline_sr)
        infer_data.append({'idx': idx, 'prompt': user_prompt})
    return infer_data

def error_perturb(data_json_path, table_json_path, column_meaning_path, baseline_sql_path, db_dir, 
                  baseline_sr_path, validated_sr_path, model_path):
    # Top-p and temperature can be adjust during inference to generate more diverse outputs. 
    data_json = json.load(open(data_json_path, 'r'))
    table_json = json.load(open(table_json_path, 'r'))
    column_meaning_json = json.load(open(column_meaning_path, 'r'))
    baseline_sql_json = json.load(open(baseline_sql_path, 'r'))
    baseline_sr_jsonl = load_jsonl(baseline_sr_path)
    validated_sr_jsonl = load_jsonl(validated_sr_path)
    
    pos_idx, neg_idx = get_distribution(data_json, table_json, baseline_sql_json, validated_sr_jsonl, db_dir)
    infer_data_items = generate_perturbation_prompt(data_json, table_json, column_meaning_json, baseline_sr_jsonl, neg_idx)
    infer_prompts = [item['prompt'] for item in infer_data_items]
    perturbed_jsonl = infer_batch(model_path, infer_prompts, infer_data_items, system_prompt)
    perturbed_sr_dict = dict(zip([i['idx'] for i in perturbed_jsonl], [i['response'] for i in perturbed_jsonl]))
    
    data_list = []
    idx_list = sorted(pos_idx + neg_idx)
    for idx in idx_list:
        info = data_json[idx]
        question = info['question']
        evidence = info['evidence']
        baseline_sql = baseline_sql_json[str(idx)]
        schema = get_column_table(table_json, info, baseline_sql)
        schema = [f"{t}.{c}" for t,c in schema]
        gold_sr = validated_sr_jsonl[idx]['sr']
        if idx in pos_idx: input_sr = re_keywords(baseline_sr_jsonl[idx]['response'], 'SR')
        if idx in neg_idx: input_sr = re_keywords(perturbed_sr_dict[idx], 'SR')
        column_description = get_column_meanings(info, table_json, baseline_sql, column_meaning_json)    
        user_prompt = sr2sr_user_prompt.format(schema = schema, column_description = column_description, question = question, evidence = evidence, sr = input_sr)
        final_assistant_prompt = assistant_prompt.format(sr = gold_sr)
        message = {
            'instruction': user_prompt,
            'output': final_assistant_prompt,
            'system': system_prompt
        }
        data_list.append(message)
    return data_list

def generate_lom_train_data(data_config, intermediate_config, bam_path, file_name):
    data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    baseline_sql_path = get_abs_path(BASE_DIR, data_config['bird_train_baseline'])
    column_meaning_path = get_abs_path(BASE_DIR, data_config['bird_train_column_meaning'])
    ft_data_dir = get_abs_path(BASE_DIR, data_config['ft_data_dir'])
    db_dir = get_abs_path(BASE_DIR, data_config['bird_train_db_dir'])
    baseline_sr_path = intermediate_config['bam_baseline_sql2sr']
    validated_sr_path = intermediate_config['bird_validated_sr']
    data_list = error_perturb(data_path, table_path, column_meaning_path, baseline_sql_path, db_dir,
                              baseline_sr_path, validated_sr_path, bam_path)
    save_data_to_fac(data_list, ft_data_dir, file_name)

def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    file_name = "lom_train_data"
    generate_lom_train_data(data_config, intermediate_config, args.bam_model_path, file_name)

def parse_args():
    parser = argparse.ArgumentParser(description="Training data of LOM.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--lom_train_data_name", type=str, required=True, help="File name of the data.")
    parser.add_argument("--bam_model_path", type=str, required=True, help="Path of BAM.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    main(args)
    