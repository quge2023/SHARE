import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.prompts.for_train import system_prompt, mask_schema_user_prompt, fill_in_schema_user_prompt, assistant_prompt
from src.call_models.vllm_infer import infer_batch
from src.utils import re_keywords, load_jsonl, save_jsonl, get_column_table, get_abs_path, save_data_to_fac
import argparse


def generate_schema_for_db(db_info):
    otn_list = db_info['table_names_original']
    otn_idx_list = [i for i in range(len(otn_list))]
    otn_idx_dic = dict(zip(otn_idx_list, otn_list))
    otn_ocn_dic = dict(zip(otn_idx_list, [[] for _ in range(len(otn_list))]))
    ocn_list = db_info['column_names_original'][1:]
    for t_idx, ocn in ocn_list:
        otn = otn_idx_dic[t_idx]
        otn = f"`{otn}`" if ' ' in otn else otn
        ocn = f"`{ocn}`" if ' ' in ocn else ocn
        tmp_s = f"{otn}.{ocn}"
        otn_ocn_dic[t_idx].append(tmp_s)
    
    schema_str = []
    for t_idx, schema in otn_ocn_dic.items():
        ss = """### Table: {otn}\n{cns}"""
        otn = otn_idx_dic[t_idx]
        table_ss = ss.format(otn = otn, cns = schema)
        schema_str.append(table_ss)
    
    final_schema = '\n\n'.join(schema_str)
    return final_schema

def generate_schema(table_json):
    schema_dic = {}
    for db_info in table_json:
        db_id = db_info['db_id']
        table_schema = generate_schema_for_db(db_info)
        schema_dic[db_id] = table_schema
    return schema_dic


def generate_mask_schema(baseline_sr_jsonl, validated_sr_jsonl):
    prompt_lists =  []
    for idx, info in enumerate(validated_sr_jsonl):
        if info["flag"] == 0: continue
        sr = re_keywords(baseline_sr_jsonl[idx]['response'], 'SR')
        user_prompt = mask_schema_user_prompt.format(sr=sr)
        prompt_lists.append({'idx': idx, 'prompt': user_prompt})
    return prompt_lists

def augment_schema(data_json_path, table_json_path, baseline_sql_json_path, baseline_sr_jsonl_path, validated_sr_path, model_path):
    data_json = json.load(open(data_json_path, 'r'))
    table_json = json.load(open(table_json_path, 'r'))
    baseline_sql_json = json.load(open(baseline_sql_json_path, 'r'))
    baseline_sr_jsonl = load_jsonl(baseline_sr_jsonl_path)
    validated_sr_jsonl = load_jsonl(validated_sr_path)
    
    mask_data_items = generate_mask_schema(baseline_sr_jsonl, validated_sr_jsonl)
    mask_prompts = [item['prompt'] for item in mask_data_items]
    mask_jsonl = infer_batch(model_path, mask_prompts, mask_data_items, system_prompt)
    
    schema_dic = generate_schema(table_json)
    data_list = []
    for idx, content in enumerate(mask_jsonl):
        data_info = data_json[idx]
        db_id = data_info['db_id']
        question = data_info['question']
        evidence = data_info['evidence']
        schema = schema_dic[db_id]
        baseline_sql = baseline_sql_json[str(idx)]
        highlighted_schema = get_column_table(table_json, data_info, baseline_sql)
        masked_sr = re_keywords(content['response'], 'SR')
        output_sr = validated_sr_jsonl[content['idx']]['sr']
        user_prompt = fill_in_schema_user_prompt.format(schema = schema, highlighted_schema=highlighted_schema, question=question, evidence=evidence, masked_sr=masked_sr)
        final_assistant_prompt = assistant_prompt.format(sr = output_sr)
        message = {
            "instruction": user_prompt,
            "output": final_assistant_prompt,
            "system": system_prompt
        }
        data_list.append(message)
    return data_list

def generate_sam_train_data(data_config, intermediate_config, bam_path, file_name):
    data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    table_path = get_abs_path(BASE_DIR, data_config['bird_train_tables'])
    baseline_sql_path = get_abs_path(BASE_DIR, data_config['bird_train_baseline'])
    ft_data_dir = get_abs_path(BASE_DIR, data_config['ft_data_dir'])
    baseline_sr_path = intermediate_config['bam_baseline_sql2sr']
    validated_sr_path = intermediate_config['bird_validated_sr']
    data_list = augment_schema(data_path, table_path, baseline_sql_path, baseline_sr_path, validated_sr_path, bam_path)
    save_data_to_fac(data_list, ft_data_dir, file_name)

def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    file_name = "sam_train_data"
    generate_sam_train_data(data_config, intermediate_config, args.bam_model_path, file_name)

def parse_args():
    parser = argparse.ArgumentParser(description="Training data of SAM.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--sam_train_data_name", type=str, required=True, help="File name of the data.")
    parser.add_argument("--bam_model_path", type=str, required=True, help="Path of BAM.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)