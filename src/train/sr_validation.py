import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
import sqlite3
import multiprocessing as mp
from func_timeout import func_timeout, FunctionTimedOut,func_set_timeout
from src.utils import re_keywords, load_jsonl, save_jsonl, get_abs_path
from src.prompts.for_train import sql_compare
from src.call_models.call_apis import api_infer_single
import argparse
    
def execute_sql(predicted_sql,ground_truth, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(predicted_sql)
    predicted_res = cursor.fetchall()
    cursor.execute(ground_truth)
    ground_truth_res = cursor.fetchall()
    res = 0
    if set(predicted_res) == set(ground_truth_res):
        res = 1
    return res


def execute_model(predicted_sql,ground_truth, db_place, idx):
    try:
        res = func_timeout(30.0, execute_sql,
                                  args=(predicted_sql, ground_truth, db_place))
    except KeyboardInterrupt:
        sys.exit(0)
    except FunctionTimedOut:
        result = [(f'timeout',)]
        res = 0
    except Exception as e:
        result = [(f'error',)] 
    result = {'idx': idx, 'exec_flag': res}
    # print(result)
    return result


def run_sqls_parallel(sqls, db_places, exec_result, num_cpus=32):
    pool = mp.Pool(processes=num_cpus)

    def result_callback(result):
        exec_result.append(result)

    for i, sql_pair in enumerate(sqls):
        predicted_sql, ground_truth = sql_pair
        pool.apply_async(
            execute_model,
            args=(predicted_sql, ground_truth, db_places[i], i),
            callback=result_callback
        )

    pool.close()
    pool.join()


def read_sqls(data_json, converted_sql_jsonl, db_dir):
    clean_sqls, clean_gold_sqls = [], []
    db_path_list = []
    for idx, content in enumerate(converted_sql_jsonl):
        sql = re_keywords(content['response'], 'sqlite')
        if not sql: sql = re_keywords(content['response'], 'sql')
        if not sql: sql = ''
        clean_sqls.append(sql)
        info = data_json[idx]
        try:
            gold_sql = info['SQL']
        except:
            gold_sql = info['query']
        clean_gold_sqls.append(gold_sql)
        db_id = info['db_id']
        db_path = os.path.join(db_dir, db_id, db_id + '.sqlite' )
        db_path_list.append(db_path)
    return clean_sqls, clean_gold_sqls, db_path_list

def evaluate_sql(converted_sqls, gold_sqls, db_paths):
    query_pairs = list(zip(converted_sqls, gold_sqls))

    manager = mp.Manager()
    exec_result = manager.list()

    run_sqls_parallel(query_pairs, db_paths, exec_result)

    exec_result = list(exec_result)
    exec_result = sorted(exec_result, key=lambda x: x['idx'])
    print(exec_result)
    return exec_result

def hybrid_sr_validation(data_json_path, sr_jsonl_path, converted_sql_jsonl_path, db_dir):
    data_json = json.load(open(data_json_path, 'r'))
    sr_jsonl = load_jsonl(sr_jsonl_path)
    converted_sql_jsonl = load_jsonl(converted_sql_jsonl_path)
    
    flag_list = []
    converted_sqls, gold_sqls, db_paths = read_sqls(data_json, converted_sql_jsonl, db_dir)
    exec_result = evaluate_sql(converted_sqls, gold_sqls, db_paths)
    for idx, content in enumerate(exec_result):
        flag = content['exec_flag']
        if flag == 0:
            prompt = sql_compare.format(gold_sql = gold_sqls[idx], generated_sql = converted_sqls[idx])
            _, content, _ = api_infer_single(prompt, max_token_length=128)
            print(f"llm: {content}")
            if 'yes' in content.lower():
                flag = 1
        sr = re_keywords(sr_jsonl[idx]['response'], 'SR')
        flag_list.append({'idx': idx, 'sr': sr, 'flag': flag})
    return flag_list

def validate_sr(data_config, intermediate_config):
    bird_data_path = get_abs_path(BASE_DIR, data_config['bird_train_data'])
    spider_data_path = get_abs_path(BASE_DIR, data_config['spider_train_data'])
    bird_sql2sr_path = intermediate_config['bird_teacher_sql2sr']
    spider_sql2sr_path = intermediate_config['spider_teacher_sql2sr']
    bird_converted_sql_path = intermediate_config['bird_converted_sql']
    spider_converted_sql_path = intermediate_config['spider_converted_sql']
    bird_db_dir = get_abs_path(BASE_DIR, data_config['bird_train_db_dir'])
    spider_db_dir = get_abs_path(BASE_DIR, data_config['spider_db_dir'])
    
    bird_validated_sr = hybrid_sr_validation(bird_data_path, bird_sql2sr_path, bird_converted_sql_path, bird_db_dir)
    spider_validated_sr = hybrid_sr_validation(spider_data_path, spider_sql2sr_path, spider_converted_sql_path, spider_db_dir)
    save_jsonl(bird_validated_sr, intermediate_config['bird_validated_sr'])
    save_jsonl(spider_validated_sr, intermediate_config['spider_validated_sr'])
    print("SR validation Done.")
    

def main(args):
    data_config = json.load(open(args.data_config_path, 'r'))
    try:
        intermediate_config = json.load(open(args.intermediate_config_path, 'r'))
    except:
        intermediate_config = {}
    intermediate_config['bird_validated_sr'] = args.bird_validated_sr_path
    intermediate_config['spider_validated_sr'] = args.spider_validated_sr_path
    validate_sr(data_config, intermediate_config)
    json.dump(intermediate_config, open(args.intermediate_config_path, 'w'), indent=4)

def parse_args():
    parser = argparse.ArgumentParser(description="Validate SR generated by SQL.")
    parser.add_argument("--data_config_path", type=str, required=True, help="Path to the data configuration JSON file.")
    parser.add_argument("--intermediate_config_path", type=str, required=True, help="Path to the intermediate configuration JSON file.")
    parser.add_argument("--bird_validated_sr_path", type=str, required=True, help="Path to save the bird validated SR.")
    parser.add_argument("--spider_validated_sr_path", type=str, required=True, help="Path to save the spider validated SR.")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    main(args)