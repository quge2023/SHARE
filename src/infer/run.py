import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
import argparse
import re
from src.infer.share_models import BAM, LOM, SAM
from src.utils import re_keywords, generate_pk_fk, save_jsonl, load_jsonl
from src.prompts.for_infer import ft_sr_to_sql
from src.call_models.call_apis import api_infer

def get_column_meanings(question_info, related_columns, column_meaning_json):
    desc_prompt = ""
    db_id = question_info['db_id']
    schema_list = [res.split('.') for res in related_columns]
    for table, column in schema_list:
        try:
            meaning = column_meaning_json[f"{db_id}|{table}|{column}"]
            meaning = meaning[1:] if meaning[0] == '#' else meaning
            table = f"`{table}`" if ' ' in table else table
            column = f"`{column}`" if ' ' in column else column
            desc_prompt += f"# {table}.{column}: {meaning}"
            desc_prompt += '\n'
        except:
            continue
    return desc_prompt

def schema_s2t(schema_list):
    final_schema = []
    for schema in schema_list:
        table, column = schema.split('.')
        table = f"`{table}`" if ' ' in table else table
        column = f"`{column}`" if ' ' in column else column
        final_schema.append([table, column])
    return final_schema

def postprocess_sql(sql_jsonl, data_json):
    final_sql = {}
    for idx, content in enumerate(sql_jsonl):
        ori_sql = content['response']
        match = re.search(r"```sqlite(.*?)```", ori_sql, re.DOTALL)
        sql = match.group(1).strip() if match else None
        if not sql:
            match = re.search(r"```sql(.*?)```", ori_sql, re.DOTALL)
            sql = match.group(1).strip() if match else None
        if not sql:
            match = re.search(r"```(.*?)```", ori_sql, re.DOTALL)
            sql = match.group(1).strip() if match else None
        if not sql:
            sql = ori_sql
            sql = sql.split('\n\nsqlite\n')[-1]
        
        sql = sql + '\t----- bird -----\t' + data_json[idx]['db_id']
        final_sql[idx] = sql
    
    return final_sql
    
def run_inference(bam, sam, lom, output_dir):
    original_traj_save_path = os.path.join(output_dir, 'original_traj.jsonl')
    masked_traj_save_path = os.path.join(output_dir, 'masked_traj.jsonl')
    original_traj_list = bam.sql2traj(save_path=original_traj_save_path)
    masked_traj_list = bam.mask_traj(original_traj_list, masked_traj_save_path)
    print(f"Original trajectory saved to {original_traj_save_path}")
    print(f"Masked trajectory saved to {masked_traj_save_path}")
    
    intermediate_traj_save_path = os.path.join(output_dir, 'intermediate_traj.jsonl')
    augmented_schema_path = os.path.join(output_dir, 'augmented_schema.json')
    augmented_schema, intermediate_traj_list = sam.get_augmented_schema(masked_traj_list, augmentation_response_path=intermediate_traj_save_path,
                                                        final_schema_path=augmented_schema_path)
    print(f"Intermediate trajectory saved to {intermediate_traj_save_path}")
    print(f"Augmented schema saved to {augmented_schema_path}")
    
    final_traj_save_path = os.path.join(output_dir, 'final_traj.jsonl')
    final_traj = lom.modify_traj(augmented_schema, intermediate_traj_list, save_path = final_traj_save_path)
    print(f"Final trajectory saved to {final_traj_save_path}")
    
    final_traj = load_jsonl('/home/qinbowen/just_malou/gq2138/share/outputs/infer/final_traj.jsonl')
    augmented_schema = json.load(open('/home/qinbowen/just_malou/gq2138/share/outputs/infer/augmented_schema.json', 'r'))
    prompt_list = []
    for idx, info in enumerate(bam.data_json):
        aug_schema = augmented_schema[str(idx)]
        processed_schema = schema_s2t(aug_schema)
        schema = [f"{t}.{c}" for t,c in processed_schema]
        _,fk_dict = generate_pk_fk(info, bam.table_json)
        column_description = get_column_meanings(info, aug_schema, bam.column_meaning_json)
        question = info['question']
        evidence = info['evidence']
        traj = re_keywords(final_traj[idx]['response'], 'SR')
        prompt = ft_sr_to_sql.format(schema = schema, fk_dic = fk_dict,
                                    column_description = column_description,
                                    question = question, evidence = evidence,
                                    sr = traj)
        prompt_list.append({'idx':idx, 'prompt':prompt})

    prompt_save_path = os.path.join(output_dir, 'prompts_for_generator.jsonl')
    save_jsonl(prompt_list, prompt_save_path)
    print(f"SQL generation prompts for generator saved to {prompt_save_path}")

    final_sql_list = api_infer(prompt_jsonl=prompt_list)
    processed_final_sql = postprocess_sql(final_sql_list, bam.data_json)
    final_sql_save_path = os.path.join(output_dir, 'final_sql.json')
    json.dump(processed_final_sql, open(final_sql_save_path, 'w'), indent=4)
    print(f"Final SQLs saved to {final_sql_save_path}")
    return final_sql_list

def parse_args():
    parser = argparse.ArgumentParser(description="Run inference for SHARE.")
    parser.add_argument('--data_config_path', type=str, required=True, help='Path to the data configuration file.')
    parser.add_argument('--bam_model_path', type=str, required=True, help='Path to the BAM model.')
    parser.add_argument('--sam_model_path', type=str, required=True, help='Path to the SAM model.')
    parser.add_argument('--lom_model_path', type=str, required=True, help='Path to the LOM model.')
    parser.add_argument('--input_sql_path', type=str, required=True, help='Path to the input SQL file.')
    parser.add_argument('--output_dir', type=str, required=True, help='Directory to save output files.')
    
    return parser.parse_args()

def main(opt):
    data_config_path = opt.data_config_path
    bam_path = opt.bam_model_path
    sam_path = opt.sam_model_path
    lom_path = opt.lom_model_path
    input_sql_path = opt.input_sql_path
    output_dir = opt.output_dir
    
    bam = BAM(data_config_path, bam_path, input_sql_path)
    sam = SAM(data_config_path, sam_path, input_sql_path)
    lom = LOM(data_config_path, lom_path, input_sql_path)

    final_sqls = run_inference(bam, sam, lom, output_dir)
    
if __name__ == "__main__":
    opt = parse_args()
    main(opt)
    
    