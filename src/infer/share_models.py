import sys
import os
BASE_DIR = os.getcwd()
sys.path.append(BASE_DIR)

import json
from src.prompts.for_infer import sql2sr_user_prompt, mask_schema_user_prompt, fill_in_schema_user_prompt, sr2sr_user_prompt, system_prompt
import argparse
from vllm import LLM, SamplingParams
import torch
from tqdm import tqdm
import jsonlines
import re

class BaseModel():
    def __init__(self, data_config_path, model_path):
        self.data_config = json.load(open(data_config_path, 'r'))
        self.table_json_path = os.path.join(BASE_DIR, self.data_config['dev_tables'])
        self.data_json_path = os.path.join(BASE_DIR, self.data_config['dev_data'])
        self.column_meaning_path = os.path.join(BASE_DIR, self.data_config['dev_column_meaning'])
        self.db_dir = os.path.join(BASE_DIR, self.data_config['dev_db_dir'])
        self.table_json = json.load(open(self.table_json_path, 'r'))
        self.data_json = json.load(open(self.data_json_path, 'r'))
        self.column_meaning_json = json.load(open(self.column_meaning_path, 'r'))
        self.model_path = model_path
   

    def _process_batch_data(self, data_list, batch_size=1):
        num_batches = len(data_list) // batch_size
        batches = []
        for i in range(num_batches - 1):
            start = i * batch_size
            end = (i + 1) * batch_size
            batches.append(data_list[start:end])
        last_start = (num_batches - 1) * batch_size
        batches.append(data_list[last_start:sys.maxsize])
        return batches
    
    def re_keywords(self, input, keyword):
        match = re.search(fr"```{keyword}(.*?)```", input, re.DOTALL)
        tmp = match.group(1).strip() if match else None
        if not tmp: tmp = ''
        return tmp
        
    def get_column_table(self, question_info, generated_sql):
        def find_table_for_column(table_column_list, column):
            res = []
            for table_column in table_column_list:
                if table_column[1] == column:
                    res.append(table_column)
            return res
        
        db_id = question_info['db_id']
        table_info = [content for content in self.table_json if content['db_id'] == db_id][0]
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

    def infer_batch(self, prompts, data_items, system_prompt=None,
                    max_token_length=8192, batch_size=100, limit=None):
                
        if not limit:
            prompts = prompts[limit:]
            data_items = data_items[limit:]
        
        print("First prompt example:", prompts[0], flush=True)
        print("Number of samples to infer:", len(prompts))

        
        prompt_batches = self._process_batch_data(prompts, batch_size=batch_size)
        data_batches = self._process_batch_data(data_items, batch_size=batch_size)

        llm = LLM(
        model=self.model_path,
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
                    if len(generated_text.strip()) <= 1:
                        invalid_response = True
                        break
                    else:
                        invalid_response = False
                if attempts > 10:
                    print("Exceeded max invalid output attempts.")
                    invalid_response = False

            batch_generated_texts = []
            for completion in completions:
                generated_text = completion.outputs[0].text
                if len(generated_text.strip()) <= 1:
                    generated_text = "[INVALID]"
                batch_generated_texts.append(generated_text)
            for item, gen_text in zip(items_in_batch, batch_generated_texts):
                item["response"] = gen_text
                all_data_with_responses.append(item)
            
        print("All batch inference completed.")
        return all_data_with_responses
    
    def load_jsonl(self, file_path):
        data = []
        with open(file_path, "r", encoding="utf-8") as file:
            for line in file:
                data.append(json.loads(line))
        return data

    def load_json(self, file_path):
        data = json.load(open(file_path, 'r'))
        return data 
    
    def save_jsonl(self, data, file_path):
        with open(file_path, "w", encoding="utf-8") as file:
            for entry in data:
                file.write(json.dumps(entry) + "\n")


class BAM(BaseModel):
    def __init__(self, data_config_path, model_path, input_json_path):
        super().__init__(data_config_path, model_path)
        self.input_sql_path = input_json_path
        self.generated_sqls = json.load(open(self.input_sql_path, 'r'))

    def sql2traj(self, save_path = None):
        infer_data, prompts = [], []
        for idx, info in enumerate(self.data_json):
            sql = self.generated_sqls[str(idx)].split('\t')[0].replace('\n', ' ')
            schema = self.get_column_table(info, sql)
            schema = [f"{t}.{c}" for t,c in schema]
            user_prompt = sql2sr_user_prompt.format(schema = schema, sql = sql)
            infer_data.append({
                'idx': idx,
                'prompt': user_prompt
            })
            prompts.append(user_prompt)
        traj_response = self.infer_batch(prompts, infer_data, system_prompt=system_prompt)
        if save_path:
            self.save_jsonl(traj_response, save_path)
        return traj_response
    
    def mask_traj(self, traj_list, save_path=None):
        infer_data, prompts = [], []
        for idx, info in enumerate(traj_list):
            sr = info['response']
            sr = self.re_keywords(sr, 'SR')
            user_prompt = mask_schema_user_prompt.format(sr=sr)
            infer_data.append({
                'idx': idx,
                'prompt': user_prompt
            })
            prompts.append(user_prompt)
        masked_traj_response = self.infer_batch(prompts, infer_data, system_prompt=system_prompt)
        if save_path:
            self.save_jsonl(masked_traj_response, save_path)
        return masked_traj_response

class SAM(BaseModel):
    def __init__(self, data_config_path, model_path, input_json_path):
        super().__init__(data_config_path, model_path)
        self.input_sql_path = input_json_path
        self.generated_sqls = json.load(open(self.input_sql_path, 'r'))
    
    def _generate_schema_for_db(self, db_info):
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

    def _generate_schema(self, table_json):
        schema_dic = {}
        for db_info in table_json:
            db_id = db_info['db_id']
            table_schema = self._generate_schema_for_db(db_info)
            schema_dic[db_id] = table_schema
        return schema_dic
    
    def _compare_schema(self, question_info, generated_sql):
        sql = question_info['SQL']
        gold_schema = self.get_column_table(question_info, sql)
        gold_schema = [f"{t}.{c}" for t, c in gold_schema]
        generated_schema = self.get_column_table(question_info, generated_sql)
        generated_schema = [f"{t}.{c}" for t, c in generated_schema]
        return gold_schema, generated_schema
    
    def get_all_schema(self, input_sqls):
        gold_schema_list, generated_schema_list = [], []
        for idx, info in enumerate(self.data_json):
            try:
                generated_sql = input_sqls[str(idx)]
            except:
                generated_sql = input_sqls[idx]['response']
            gold_schema, generated_schema = self._compare_schema(info, generated_sql)
            gold_schema_list.append(gold_schema)
            generated_schema_list.append(generated_schema)
        return gold_schema_list, generated_schema_list
    
    def _compute_ex(self, ground_truth, sl_res):
        total_question_num = len(ground_truth)
        correct_num = 0
        for idx, table_column in enumerate(ground_truth):
            correct_flag = True
            for otn_ocn in table_column:
                if otn_ocn not in sl_res[idx]:
                    correct_flag = False
            if correct_flag:
                correct_num += 1
        return correct_num / total_question_num

    def _compute_recall(self, ground_truth, sl_res):
        recall_list = []
        for idx, table_column in enumerate(ground_truth):
            correct = 0
            for ct_tuple in table_column:
                if ct_tuple in sl_res[idx]:
                    correct+= 1
            recall = correct / len(table_column) if len(table_column) != 0 else 0
            recall_list.append(recall)
        return sum(recall_list) / len(recall_list)

    def _compute_precision(self, ground_truth, sl_res):
        precision_list = []
        for idx, sl_value in enumerate(sl_res):
            count = 0
            for ct_tuple in sl_value:
                if ct_tuple in ground_truth[idx]:
                    count += 1
            precision = count / len(sl_value) if len(sl_value) != 0 else 1
            precision_list.append(precision)
        return sum(precision_list)/len(precision_list)


    def compute_metrics(self, ground_truth, sl_res):
        ex = self._compute_ex(ground_truth, sl_res)
        recall = self._compute_recall(ground_truth, sl_res)
        precision = self._compute_precision(ground_truth, sl_res)
        f1 = 2*precision*recall/(precision+recall)
        # f1 = 0
        print(f"ex: {ex}, recall: {recall}, precision: {precision}, f1: {f1}")
    
    def schema_augment(self, mask_traj_list, save_path=None):
        schema_dic = self._generate_schema(self.table_json)
        infer_data, prompts = [], []
        for idx, info in enumerate(self.data_json):
            db_id = info['db_id']
            question = info['question']
            evidence = info['evidence']
            schema = schema_dic[db_id]
            generated_sql = self.generated_sqls[str(idx)]
            highlighted_schema = self.get_column_table(info, generated_sql)
            masked_sr = mask_traj_list[idx]['response']
            masked_sr = self.re_keywords(masked_sr, 'SR')
            user_prompt = fill_in_schema_user_prompt.format(schema = schema, highlighted_schema=highlighted_schema,
                                                            question=question, evidence=evidence, masked_sr=masked_sr)
            infer_data.append({'idx': idx, 'prompt': user_prompt})
            prompts.append(user_prompt)
        augmented_schema_response = self.infer_batch(prompts, infer_data, system_prompt=system_prompt)
        if save_path:
            self.save_jsonl(augmented_schema_response, save_path)
        return augmented_schema_response
    
    def merge_schema_lists(self, ori_schema_list, augmented_schema_list):
        final_list = []
        schema_lists = [ori_schema_list, augmented_schema_list]
        list_len = [len(r) for r in schema_lists]
        assert len(set(list_len)) == 1
        
        for idx, sl_res in enumerate(schema_lists[0]):
            tmp_list = []
            for i, diff_schema in enumerate(schema_lists):
                tmp_list += diff_schema[idx]
            tmp_list = list(set(tmp_list))
            final_list.append(tmp_list)
        return final_list
    
    def get_augmented_schema(self, masked_traj_list, augmentation_response_path=None, final_schema_path = None):
        augmented_schema_list = self.schema_augment(masked_traj_list, save_path=augmentation_response_path)
        gold_list, before_list = self.get_all_schema(self.generated_sqls)
        _, after_list = self.get_all_schema(augmented_schema_list)
        final_schema_list = self.merge_schema_lists(before_list, after_list)
        self.compute_metrics(gold_list, before_list)
        self.compute_metrics(gold_list, final_schema_list)
        
        schema_dic = {}
        for idx, schema in enumerate(final_schema_list):
            schema_dic[str(idx)] = schema
        json.dump(schema_dic, open(final_schema_path, 'w'), indent=4)
        return schema_dic, augmented_schema_list

class LOM(BaseModel):
    def __init__(self, data_config_path, model_path, input_json_path):
        super().__init__(data_config_path, model_path)
        self.input_sql_path = input_json_path
        self.generated_sqls = json.load(open(self.input_sql_path, 'r'))
    
    def _get_column_meanings(self, question_info, schema):
        desc_prompt = ""
        db_id = question_info['db_id']
        for table, column in schema:
            try:
                meaning = self.column_meaning_json[f"{db_id}|{table}|{column}"]
                meaning = meaning[1:] if meaning[0] == '#' else meaning
                table = f"`{table}`" if ' ' in table else table
                column = f"`{column}`" if ' ' in column else column
                desc_prompt += f"# {table}.{column}: {meaning}"
                desc_prompt += '\n'
            except:
                continue
        return desc_prompt
    
    def _schema_s2t(self, schema_list):
        final_schema = []
        for schema in schema_list:
            table, column = schema.split('.')
            # table = f"`{table}`" if ' ' in table else table
            # column = f"`{column}`" if ' ' in column else column
            table = table.replace('`', '')
            column = column.replace('`', '')
            final_schema.append([table, column])
        return final_schema
    
    def modify_traj(self, augmented_schema, traj_list, save_path=None):
        infer_data, prompts = [], []
        for idx, info in enumerate(self.data_json):
            question = info['question']
            evidence = info['evidence']
            aug_schema = augmented_schema[str(idx)]
            processed_schema = self._schema_s2t(aug_schema)
            schema = [f"{t}.{c}" for t,c in processed_schema]
            gen_sr = self.re_keywords(traj_list[idx]['response'], 'SR')
            column_description = self._get_column_meanings(info, processed_schema)    
            user_prompt = sr2sr_user_prompt.format(schema = schema, column_description = column_description, question = question, evidence = evidence, sr = gen_sr)
            infer_data.append({
                'idx': idx,
                'prompt': user_prompt
            })
            prompts.append(user_prompt)
        traj_response = self.infer_batch(prompts, infer_data, system_prompt=system_prompt)
        if save_path:
            self.save_jsonl(traj_response, save_path)
        return traj_response
    
if __name__ == '__main__':
    data_config_path = '/home/qinbowen/just_malou/gq2138/share/configs/data_config.json'
    model_path = '/home/qinbowen/just_malou/gq2138/share/model/bam'
    prompt_path = '/home/qinbowen/just_malou/gq2138/share_tmp/res/prompts/tmp_infer/sql2sr.jsonl'
    input_json_path = '/home/qinbowen/just_malou/gq2138/share/data/bird/dev/baseline_sql.json'
    
    output_dir = '/home/qinbowen/just_malou/gq2138/share/outputs/infer'
    # bam = BAM(data_config_path, model_path, input_json_path)
    # traj_list = bam.sql2traj(save_path= os.path.join(output_dir, 'traj.jsonl'))
    # masked_traj_list = bam.mask_traj(traj_list, save_path=os.path.join(output_dir, 'masked_traj.jsonl'))
    
    # model_path = '/home/qinbowen/just_malou/gq2138/share/model/sam'
    # sam = SAM(data_config_path, model_path, input_json_path)
    # masked_traj_list = sam.load_jsonl(os.path.join(output_dir, 'masked_traj.jsonl'))
    # sam.get_augmented_schema(masked_traj_list, 
    #                          augmentation_response_path=os.path.join(output_dir, 'tmp_augmented_schema.jsonl'),
    #                          final_schema_path=os.path.join(output_dir, 'augmented_schema.json'))


    model_path = '/home/qinbowen/just_malou/gq2138/share/model/lom'
    lom = LOM(data_config_path, model_path, input_json_path)
    masked_traj_list = lom.load_jsonl(os.path.join(output_dir, 'intermediate_traj.jsonl'))
    augmented_schema = lom.load_json(os.path.join(output_dir, 'augmented_schema.json'))
    lom.modify_traj(augmented_schema, masked_traj_list, save_path=os.path.join(output_dir, 'final_traj.jsonl'))