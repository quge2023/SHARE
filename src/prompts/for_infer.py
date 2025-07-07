system_prompt = """You are an expert about text-to-SQL and pandas code."""


sql2sr_user_prompt = """SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. I will provide you:
1. Schema: A python list and each element is a `table_name`.`column_name` string. It indicates that the table and column you could use in the SR.
2. SQL: The SQL that needed to be converted to SR
 
Your task is to generate valid SR which reflect the accurate logic in the SQL. Later, the SR will be converted to SQL.
Please pay attention that SR ignore 'join' action. Do not generate 'join' action.

schema = {schema}
sql = "{sql}"

Now generate the valid SR that display the reasoning process of generating SQL that can accurately answer the question:
```SR
[Your Answer]
```"""

mask_schema_user_prompt =  """SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. I will provide you a piece of SR that show the logic of the text-to-SQL process in the context of the schema, question and evidence.
Your task is to mask the schema (related tables and columns) in the SR and only keep the logic template. DO NOT modify the logic in the original SR, just do the mask.
Here are some examples to help you better understand the task:

Here is an example for you to understand the task
======================= Example ===========================================
```Input SR
df1 = df.where(element = Business_Hours.business_id, filter = 12)
df2 = df1.where(element = Days.day_of_week, filter = 'Monday')
res = df2.select(Business_Hours.opening_time)
```
``` SR
df1 = df.where(element = [MASK], filter = 12)
df2 = df1.where(element = [MASK], filter = 'Monday')
res = df2.select([MASK])
```
============================================================================

Now mask the schema in the following SR and fill your answer in the template,
```Input SR
{sr}
```
```SR
[Your Answer]
```"""


fill_in_schema_user_prompt = """SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. It shows the logical reasoning process of text-to-SQL. I'll provide you:
1. Schema: For each table, we will have a python list and each element is a `table_name`.`column_name` string to show all the schema in the database. It indicates that the table and column you could use in the SR.
2. Highlighted Schema: a subset of Schema. You can consider it as a guess about the schema that used in the ground-truth SQL in the context of this text-to-SQL process. However, it is not always correct. It may contain irrelavant schema which could lead to errors in the subsequent SQL generation or miss truely related schema. 
3. Question: the natural language answer you need to answer in the text-to-SQL process
4. Evidence: the oracle knowledge to help you generate the SR
5. Masked SR: An SR with the schema masked, leaving only the reasoning steps in text-to-SQL.
Your task is to refer to all the provided information and fill in the correct schema at the [MASK] positions in the masked SR. \
 The complete SR should accurately reflect the reasoning process that generates the SQL capable of correctly answering the question. 
DO NOT modify the logical template in the masked SR; you are only allowed to fill in the schema.

```Schema
{schema}
```
highlighted_schema = {highlighted_schema}
question = "{question}"
evidence = "{evidence}"
```Masked SR
{masked_sr}
```

Now, fill in the masked SR and give me the final SR:
```SR
[Your Answer]
```"""

sr2sr_user_prompt = """SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. An effective piece of SR should reflect the accurate logic in the text-to-SQL process and help the subsequent generation of the SQL that can answer the question accurately.
I will provide you:
1. Schema: A python list and each element is a `table_name`.`column_name` string. It indicates that the table and column you could use in the SR.
2. Column description: For each column in the schema, a column description is given to describe the column meaning, column type and example values in this column.
3. Question: the natural language answer you need to answer in the text-to-SQL process
4. Evidence: the oracle knowledge to help you generate the SR
5. SR: SR that show the logic of the text-to-SQL process in the context of the schema, question and evidence. It may contain errors which could lead to errors in the subsequent SQL generation.
 
Your task is to check the given SR and modify it when needed. The final goal is to generate valid SR which reflect the accurate logic in the text-to-SQL based on the schema, column description, question and evidence. Later, the modified SR will be converted to SQL.
Please pay attention that:
1. SR ignore 'join' action. Do not generate 'join' action.
2. In the generated SR, only select the thing that request in the question. Do not select any non-requested stuff. 
3. The filter condition in the 'where' function doesn't directly match the text in the question. To find the correct value for the 'where' function, you need to reference the example values or all possible values in column description.

schema = {schema}
```column description
{column_description}
```
question = "{question}"
evidence = "{evidence}"
```SR
{sr}
```

Now generate the valid SR that display the reasoning process of generating SQL that can accurately answer the question:
```SR
[Your Answer]
```"""


ft_sr_to_sql = """You are an expert of text-to-SQL. I will provide you:
1. Database schema: Includes schema and forerign_keys. Schema is a python list and each element is a `table_name`.`column_name` string. It indicates that the table and column you could use in the SR. foreign_keys is a dictionary that shows foreign key relationships among tables.
2. Column description: For each column in the schema, a column description is given to describe the column meaning, column type and example values in this column.
3. Question: the natural language answer you need to answer in the text-to-SQL process.
4. Evidence: the oracle knowledge to help you generate the SR.
5. SR: a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. It shows the possible reasoning process in this text-to-SQL process.

Your task is to convert the given SR to the valid SQL accordding to the database schema, column description, question and evidence. The SQL should be valid in syntax and can answer the question accurately.
To help you better understand SR, please pay attention that:
1. SR ignore 'join' action. Do not generate 'join' action. You need to generate correct join clause by yourself. Use 'INNER JOIN' in your generated SQL.
2. The filter condition in the 'where' function doesn't directly match the text in the question. To find the correct value for the 'where' function, you need to reference the example values or all possible values in column description.
3. In the generated SR, only select the thing that request in the question. Do not select any non-requested stuff.

schema = {schema}
foreign_keys = {fk_dic}
```column description
{column_description}
```
question = "{question}"
evidence = "{evidence}"
```SR
{sr}
```

Now generate the valid SQL:
```sqlite
[Your Answer]
```"""