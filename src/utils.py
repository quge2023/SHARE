import os
import json
import re


def get_abs_path(base_dir, sub_path):
    return os.path.join(base_dir, sub_path) if sub_path else base_dir


def new_directory(path):
    if path and not os.path.exists(path):
        os.makedirs(path)

def load_jsonl(file_path):
    data = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            data.append(json.loads(line))
    return data

def save_jsonl(data, file_path):
    with open(file_path, "w", encoding="utf-8") as file:
        for entry in data:
            file.write(json.dumps(entry) + "\n")

def save_data_to_fac(data, save_dir,file_name):
    data_save_path = os.path.join(save_dir, f"{file_name}.json")
    json.dump(data, open(data_save_path, 'w'), indent=4)
    info_path = os.path.join(save_dir, 'dataset_info.json')
    if not os.path.exists(info_path):
        data_info = {}
    else:
        data_info = json.load(open(info_path, 'r'))

    data_info[file_name] = {
        'file_name': f"{file_name}.json",
        "columns": {
                    "prompt": "instruction",
                    "response": "output",
                    "system": "system"
                    }
        }
    json.dump(data_info, open(info_path, 'w'), indent=4)

def re_keywords(input, keyword):
    match = re.search(fr"```{keyword}(.*?)```", input, re.DOTALL)
    tmp = match.group(1).strip() if match else None
    if not tmp: tmp = ''
    return tmp

def generate_pk_fk(question_info, table_json):
    db_id = question_info['db_id']
    table = [content for content in table_json if content['db_id'] == db_id][0]
    pk_dict = {}
    fk_dict = {}
    table_names_original = table['table_names_original']
    column_names_original = table['column_names_original']
    primary_keys = table['primary_keys']
    foreign_keys = table['foreign_keys']
    
    for _,pk_idx in enumerate(primary_keys):
        if type(pk_idx) == int:
            pk_dict[str(table_names_original[column_names_original[pk_idx][0]])] = [column_names_original[pk_idx][-1]]
        else:
            pk_dict[str(table_names_original[column_names_original[pk_idx[0]][0]])] = [column_names_original[idx][-1] for idx in pk_idx]
    
    for cur_fk in foreign_keys:
        src_col_idx, tgt_col_idx = cur_fk
        src_col_name = str(table_names_original[column_names_original[src_col_idx][0]]) + '.' + str(column_names_original[src_col_idx][-1])
        tgt_col_name = str(table_names_original[column_names_original[tgt_col_idx][0]]) + '.' + str(column_names_original[tgt_col_idx][-1])
        fk_dict[src_col_name] = tgt_col_name
    return pk_dict, fk_dict

def find_table_for_column(table_column_list, column):
    res = []
    for table_column in table_column_list:
        if table_column[1] == column:
            res.append(table_column)
    return res
    
def get_column_table(table_json, question_info, generated_sql):
    db_id = question_info['db_id']
    table_info = [content for content in table_json if content['db_id'] == db_id][0]
    table_names_list = table_info["table_names_original"]
    column_names_list = [[table_names_list[int(content[0])], content[1]] for content in table_info['column_names_original'][1:]]
    pure_column_name_list = [i[1] for i in column_names_list]
    filtered_tables = []
    filtered_columns = []
    final_columns = []
    for table in table_names_list:
        if table in generated_sql:
            filtered_tables.append(table)
    for column in pure_column_name_list:
        if column in generated_sql:
            filtered_columns.append(column)

    filtered_tables = list(set(filtered_tables))
    filtered_columns = list(set(filtered_columns))
    for columns in filtered_columns:
        tuples = find_table_for_column(column_names_list, columns)
        for tuple in tuples:
            if tuple[0] in filtered_tables:
                final_columns.append(tuple)
    return final_columns

def find_table_for_column_spider(table_column_list, column):
    res = []
    for table_column in table_column_list:
        if table_column[1] == column:
            res.append(table_column)
    return res

def get_column_table_spider(table_json, question_info, generated_sql):
    db_id = question_info['db_id']
    table_info = [content for content in table_json if content['db_id'] == db_id][0]
    table_names_list = table_info["table_names_original"]
    column_names_list = [[table_names_list[int(content[0])], content[1]] for content in table_info['column_names_original'][1:]]
    pure_column_name_list = [i[1] for i in column_names_list]
    filtered_tables = []
    filtered_columns = []
    final_columns = []
    for table in table_names_list:
        if table in generated_sql:
            filtered_tables.append(table)
    for column in pure_column_name_list:
        if column in generated_sql:
            filtered_columns.append(column)

    filtered_tables = list(set(filtered_tables))
    filtered_columns = list(set(filtered_columns))
    for columns in filtered_columns:
        tuples = find_table_for_column_spider(column_names_list, columns)
        for tuple in tuples:
            if tuple[0] in filtered_tables:
                final_columns.append(tuple)
    if '*' in generated_sql:
        stars = [[t, '*'] for t in filtered_tables]
        final_columns = stars + final_columns
    return final_columns

def check_schema(table_json, question_info, content):
    gold_sql = question_info['SQL']
    gold_schema = get_column_table(table_json,question_info, gold_sql)
    generated_schema = get_column_table(table_json, question_info, content)
    check_flag = True
    for schema in gold_schema:
        if schema not in generated_schema: 
            check_flag = False
            break
    return check_flag


def get_column_meanings(question_info, table_json, generated_sql, column_meaning_json):
    # spider and bird use the same one, we don't include * in column descriptions
    desc_prompt = ""
    db_id = question_info['db_id']
    related_columns = get_column_table(table_json, question_info, generated_sql)
    for table, column in related_columns:
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
