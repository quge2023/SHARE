sql2sr_shots = """question = "How many movies directed by Francis Ford Coppola have a popularity of more than 1,000? Please also show the critic of these movies."
schema = [movies.movie_title, ratings.critic, movies.director_name, movies.movie_popularity, ratings.movie_id, movies.movie_id']
evidence = "Francis Ford Coppola refers to director_name; popularity of more than 1,000 refers to movie_popularity >1000" 
SQL = "SELECT T2.movie_title, T1.critic FROM ratings AS T1 INNER JOIN movies AS T2 ON T1.movie_id = T2.movie_id WHERE T2.director_name = 'Francis Ford Coppola' AND T2.movie_popularity > 1000""
```SR
df1 = df.where(element = movies.director_name, filter = 'Francis Ford Coppola')
df2 = df1.where(element = movies.movie_popularity, filter = '> 1000')
res = df2.select(movies.movie_title, ratings.critic)"
```
    
question = "For all the movies which were produced by cruel and unusual films, which one has the most popularity?"
schema = [movie.title, `production company`.company_id, movie_company.company_id, movie_company.movie_id, movie.movie_id, `production company`.company_name, movie.popularity]
evidence = "produced by cruel and unusual films refers to company_name = 'Cruel and Unusual Films'; most popularity refers to max(popularity)"
SQL = "SELECT T3.title FROM production_company AS T1 INNER JOIN movie_company AS T2 ON T1.company_id = T2.company_id INNER JOIN movie AS T3 ON T2.movie_id = T3.movie_id WHERE T1.company_name = 'Cruel and Unusual Films' ORDER BY T3.popularity DESC LIMIT 1"
```SR
df1 = df.where(element = `production company`.company_name, filter = 'Cruel and Unusual Films')
df2 = df1.orderby(by = movie.popularity, desc).limit(1)
res = df2.select(movie.title)"
```
    
question = "Among the professors who have more than 3 research assistants, how many of them are male?"
schema = [prof.gender, RA.student_id, RA.prof_id, prof.prof_id]
evidence = "research assistant refers to the student who serves for research where the abbreviation is RA; more than 3 research assistant refers to COUNT(student_id) > 3;"
SQL = "SELECT COUNT(*) FROM ( SELECT T2.prof_id FROM RA AS T1 INNER JOIN prof AS T2 ON T1.prof_id = T2.prof_id WHERE T2.gender = 'Male' GROUP BY T1.prof_id HAVING COUNT(T1.student_id) > 3 )"
```SR
df1 = df.groupby(prof.prof_id).having(element = count(RA.student_id), filter = '> 3')
df2 = df1.where(element = 'prof.gender', filter = 'Male')
res = df2.count()
```

question = "What is the first name of clients who have the highest priority?"
schema = [client.first, client.client_id, callcenterlogs.`rand client`,callcenterlogs.priority]
evidence = "first name refers to first; highest priority refers to priority = 2"
SQL = "SELECT T1.first FROM client AS T1 INNER JOIN callcenterlogs AS T2 ON T1.client_id = T2.`rand client` WHERE T2.priority = ( SELECT MAX(priority) FROM callcenterlogs )"
```SR
df1 = df.where(element = callcenterlogs.priority, filter = max(callcenterlogs.priority))
res = df1.select(client.first)
```

question = "What percentage of businesses in the northwest US have forecasted annual sales of above 300,000?"
schema = [SalesPerson.SalesQuota, SalesPerson.BusinessEntityID, SalesPerson.TerritoryID, SalesTerritory.TerritoryID, SalesTerritory.CountryRegionCode, SalesTerritory.Name]
evidence = "northwest refers to Name = 'Northwest'; US refers to CountryRegionCode = 'US'; forecasted annual sales of above 300,000 refers to SalesQuota >300000; Percentage = Divide(Count(TerritoryID(SalesQuota >300000)),Count(TerritoryID))*100"
SQL = "SELECT CAST(SUM(CASE WHEN T1.SalesQuota > 300000 THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(T1.BusinessEntityID) FROM SalesPerson AS T1 INNER JOIN SalesTerritory AS T2 ON T1.TerritoryID = T2.TerritoryID WHERE T2.CountryRegionCode = 'US' AND T2.Name = 'Northwest'"
```SR
df1 = df.where(element = SalesTerritory.CountryRegionCode, filter = 'US').where(element = SalesTerritory.Name, filter = 'Northwest')
df2 = df1.where(element = SalesPerson.SalesQuota, filter = '> 300000')
res = df.select(cast(df2.count(), real) * 100 / df1.count())
```

question = "How many more followers in percentage are there for the repository used by solution ID 18 than solution ID19?"
schema = [Repo.`Forks Number`, Solution.Id, Repo.Id, Solution.RepoId]
evidence = "followers refers to Forks; percentage = divide(SUBTRACT(Forks(Solution.ID = 18), Forks(Solution.ID = 19)), Forks(Solution.ID = 19))*100%"
SQL = "SELECT CAST((SUM(CASE WHEN T2.Id = 18 THEN T1.Forks ELSE 0 END) - SUM(CASE WHEN T2.Id = 19 THEN T1.Forks ELSE 0 END)) AS REAL) * 100 / SUM(CASE WHEN T2.Id = 19 THEN T1.Forks ELSE 0 END) FROM Repo AS T1 INNER JOIN Solution AS T2 ON T1.Id = T2.RepoId"
```SR
df1 = df.where(element = Solution.Id, filter = 18))
tmp_res1 = df1.select(Repo.`Forks Number`).sum()
    
df1 = df.where(element = Solution.Id, filter = 19))
tmp_res2 = df1.select(Repo.Forks).sum()"
    
res = df.select(cast((tmp_res1 - tmp_res2),real) * 100 / tmp_res2)"
```
    
question = "What is the difference between the number of children's films and action films?"
schema = [category.name, film_category.category_id, category.category_id]
evidence = ""
SQL = "SELECT SUM(IIF(T2.name = 'Children', 1, 0)) - SUM(IIF(T2.name = 'Action', 1, 0)) AS diff FROM film_category AS T1 INNER JOIN category AS T2 ON T1.category_id = T2.category_id"
```SR
df1 = df.where(element = category.name, filter = 'Children')
df2 = df.where(element = category.name, filter = 'Action')
res = df.select(df1.count() - df2.count())
```"""

spider_sql2sr_shots = """question = "How many movies directed by Francis Ford Coppola have a popularity of more than 1,000? Please also show the critic of these movies."
schema = [movies.movie_title, ratings.critic, movies.director_name, movies.movie_popularity, ratings.movie_id, movies.movie_id']
evidence = "Francis Ford Coppola refers to director_name; popularity of more than 1,000 refers to movie_popularity >1000" 
SQL = "SELECT T2.movie_title, T1.critic FROM ratings AS T1 INNER JOIN movies AS T2 ON T1.movie_id = T2.movie_id WHERE T2.director_name = 'Francis Ford Coppola' AND T2.movie_popularity > 1000""
```SR
df1 = df.where(element = movies.director_name, filter = 'Francis Ford Coppola')
df2 = df1.where(element = movies.movie_popularity, filter = '> 1000')
res = df2.select(movies.movie_title, ratings.critic)"
```
    
question = "For all the movies which were produced by cruel and unusual films, which one has the most popularity?"
schema = [movie.title, `production company`.company_id, movie_company.company_id, movie_company.movie_id, movie.movie_id, `production company`.company_name, movie.popularity]
evidence = "produced by cruel and unusual films refers to company_name = 'Cruel and Unusual Films'; most popularity refers to max(popularity)"
SQL = "SELECT T3.title FROM production_company AS T1 INNER JOIN movie_company AS T2 ON T1.company_id = T2.company_id INNER JOIN movie AS T3 ON T2.movie_id = T3.movie_id WHERE T1.company_name = 'Cruel and Unusual Films' ORDER BY T3.popularity DESC LIMIT 1"
```SR
df1 = df.where(element = `production company`.company_name, filter = 'Cruel and Unusual Films')
df2 = df1.orderby(by = movie.popularity, desc).limit(1)
res = df2.select(movie.title)"
```

question = "Among the professors who have more than 3 research assistants, how many of them are male?"
schema = [prof.gender, RA.student_id, RA.prof_id, prof.prof_id]
evidence = "research assistant refers to the student who serves for research where the abbreviation is RA; more than 3 research assistant refers to COUNT(student_id) > 3;"
SQL = "SELECT COUNT(*) FROM ( SELECT T2.prof_id FROM RA AS T1 INNER JOIN prof AS T2 ON T1.prof_id = T2.prof_id WHERE T2.gender = 'Male' GROUP BY T1.prof_id HAVING COUNT(T1.student_id) > 3 )"
```SR
df1 = df.groupby(prof.prof_id).having(element = count(RA.student_id), filter = '> 3')
df2 = df1.where(element = 'prof.gender', filter = 'Male')
res = df2.count()
```

question = "Find the id of courses which are registered or attended by student whose id is 121?"
schema = [student_course_registrations.course_id, student_course_registrations.student_id, student_course_attendance.course_id, student_course_attendance.student_id]
evidence = ""
SQL = "SELECT course_id FROM student_course_registrations WHERE student_id = 121 UNION SELECT course_id FROM student_course_attendance WHERE student_id = 121"
```SR
df1 = df.where(student_course_registrations.student_id, filter = 121)
tmp_res1 = df1.select(student_course_registrations.course_id)

df2 = df.where(student_course_attendance.student_id, filter = 121)
tmp_res2 = df2.select(student_course_attendance.course_id)

res = tmp_res1.union(tmp_res2)
```

question = "What are the names of all tracks that are on the movies playlist but not in the music playlist?"
schema = [tracks.name, tracks.id, playlist_tracks.track_id, playlist_tracks.playlist_id, playlists.id, playlists.name]
evidence = ""
SQL = "SELECT T1.name FROM tracks AS T1 JOIN playlist_tracks AS T2 ON T1.id  =  T2.track_id JOIN playlists AS T3 ON T2.playlist_id  =  T3.id WHERE T3.name  =  'Movies' EXCEPT SELECT T1.name FROM tracks AS T1 JOIN playlist_tracks AS T2 ON T1.id  =  T2.track_id JOIN playlists AS T3 ON T2.playlist_id  =  T3.id WHERE T3.name  =  'Music'"
```SR
df1 = df.where(playlists.name, filter = 'Movies')
tmp_res1 = df1.select(tracks.name)

df2 = df.where(playlists.name, filter = 'Music')
tmp_res2 = df2.select(tracks.name)

res = tmp_res1.except(tmp_res2)
```

question = "Which directors had a movie both in the year 1999 and 2000?"
schema = [movie.director, movie.Year]
evidence = ""
SQL = "SELECT director FROM movie WHERE YEAR  =  2000 INTERSECT SELECT director FROM movie WHERE YEAR  =  1999"
```SR
df1 = df.where(movie.YEAR, filter = 2000)
tmp_res1 = df1.select(movie.director)

df2 = df.where(movie.YEAR, filter = 1999)
tmp_res2 = df2.select(movie.director)

res = tmp_res1.intersect(tmp_res2)
```"""


sql2sr = """"You are a text-to-SQL expert. SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. Given the database schema, question, evidence and SQL, your task is convert the SQL to SR which reflect the accurate logic in the SQL. 
I'll provide several example to you to help you understand the syntax of the SR and the convertion logic. SR ignore 'join' action. Do not generate 'join' action.

```Examples
{shots}
```

Now convert the following SQL to valid SR based on the database schema, question and evidence.
question = "{question}"
schema = "{schema}"
evidence = "{evidence}"
SQL = "{sql}"
```SR
[Your Answer]
```
"""

sr2sql_check = """# Understand the pandas-like SR first. Then convert the SR in to executable SQL based on the database schema, question, evidence, and the imported keywords you could use in SQL generation. 
# Notice the order of the action in SR may not same as the executable SQL. Make sure the generated SQL is executable and can answer the question accurately. 

from CLAUSE_KEYWORDS import select, from, where, group by, order by, union, limit, having, distinct, as, between, like, all, on, partition by
from JOIN_KEYWORDS import inner join, left join
from WHERE_OPERATIONS import is, not, null, none, in, =, >, <, >=, <=, !=, <>
from DATE_OPERATIONS import now, curdate, strftime
from UNIT_OPERATIONS import -, +, *, /
from COND_OPERATIONS import and, or, case, iif
from SQL_OPERATIONS import avg, count, max, min, round, abs, sum, length, cast, substr, cast, instr
from ORDER_OPERATIONS import desc, asc

```Database Schema
schema = {schema}
foreign_keys = {fk_dic}
```

question = "{question}"
evidence = "{evidence}"
```SR
{SR}
```

Now convert the SR to the valid SQL:
```sqlite
[Your Answer]
```"""

spider_sr2sql_check = """# Understand the pandas-like SR first. Then convert the SR in to executable SQL based on the database schema, question, evidence, and the imported keywords you could use in SQL generation. 
# Notice the order of the action in SR may not same as the executable SQL. Make sure the generated SQL is executable and can answer the question accurately. 

from CLAUSE_KEYWORDS import from, where, group by, having, order, limit
from JOIN_KEYWORDS import inner join, on, as
from WHERE_OPERATIONS import not, between, =, >, <, >=, <=, !=, in, like, is, exists
from UNIT_OPERATIONS import -, +, *, /
from AGG_OPERATIONS import  max, min, count, sum, avg
from COND_OPERATIONS import and, or
from SQL_OPERATIONS import intersect, union, except
from ORDER_OPERATIONS import desc, asc

```Database Schema
schema = {schema}
foreign_keys = {fk_dic}
```

question = "{question}"
evidence = "{evidence}"
```SR
{SR}
```

Now convert the SR to the valid SQL:
```sqlite
[Your Answer]
```"""

sql_compare = """You are a SQL expert. Given the gold SQL and generated SQL, compare this two SQL to check whether they have the same logic and will get the same execuation result. Output yes if your answer is yes. Otherwise output no. Directly give me your final judgement. DO NOT include extra analysis. 
gold_sql = "{gold_sql}"
generated_sql = "{generated_sql}"
```output
[Your Answer]
```"""


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

assistant_prompt = """```SR
{sr}
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

fill_in_schema_assistant_prompt = """```SR
{sr}
```"""


error_perturbation_prompt = """SR is a piece of pandas-like code, which is a intermediate representation between the natural language and SQL. I will provide you:
1. Schema: A python list and each element is a `table_name`.`column_name` string. It indicates that the table and column you could use in the SR.
2. Column description: For each column in the schema, a column description is given to describe the column meaning, column type and example values in this column.
3. Question: the natural language answer you need to answer in the text-to-SQL process
4. Evidence: the oracle knowledge to help you generate the SR
5. SR: gold SR that show the correct logic of the text-to-SQL process in the context of the schema, question and evidence. 

Your task is to modify the SR and imitate reasonable errors that might occur in text-to-SQL, generating an erroneous SR. It can be implemented by one or several types of error perturbation. The type of error perturbation as references: 1) Add: Inserts an additional action into the original action trajectory. 2)  Delete: Removes an existing action from the trajectory. 3) Substitute: Replaces an existing action with a different action type or modifies the parameters of the existing action.

I'll also provide you some examples:
Example1:
schema = ['movies.director_name', 'movies.movie_title']
```column description
# movies.director_name: In the 'movies' table of the 'movie_platform' database, the 'director_name' column (type: text) stores the full names of movie directors, which can include individual or multiple directors for a single movie, as seen in examples like 'Anton Holden', 'Svetlana Dramlic', 'Olaf Encke, Claudia Romero'.
# movies.movie_title: The 'movie_title' column in the 'movies' table of the 'movie_platform' database stores the name of the movie as text, with examples including 'Silkscreen', 'Sisimiut', and 'Portrait of Teresa'.
```
question = "Who is the director of the movie Sex, Drink and Bloodshed?"
evidence = "Sex, Drink and Bloodshed refers to movie title = 'Sex, Drink and Bloodshed';"
```gold SR
df1 = df.where(element = movies.movie_title, filter = 'Sex, Drink and Bloodshed')
res = df1.select(movies.director_name)
```
Output1:
```SR
df1 = df.where(element = movies.movie_title, filter = 'sex, drink and bloodshed')
res = df1.select(movies.director_id)
```

Example2:
schema = ['movie_crew.job', 'movie.movie_id', 'movie_crew.movie_id', 'person.person_id', 'movie_crew.person_id', 'movie.revenue', 'person.person_name']
```column description
# movie_crew.job: The 'job' column in the 'movie_crew' table (db id: movies_4) stores text descriptions of various crew members' roles within a movie production, acknowledging that multiple individuals can share the same job title. Example roles include 'Stand In', 'Consulting Producer', and 'Simulation & Effects Production Assistant'.
# movie.movie_id: The unique integer identifier for each movie in the 'movie' table.
# movie_crew.movie_id: The 'movie id' column (integer) in the 'movie_crew' table (db id: movies_4) references the unique identifier of a movie in the 'movie' table, indicating the specific movie a crew member worked on.
# person.person_id: The 'person id' is an integer serving as the unique identifier for individuals in the 'person' table of the 'movies_4' database.
# movie_crew.person_id: The 'person id' column in the 'movie_crew' table (db id: movies_4) is an integer that uniquely identifies a crew member, linking to their 'person_id' in the 'person' table.
# movie.revenue: The 'revenue' column in the 'movie' table (db id: movies_4) records the movie's earnings as an integer, reflecting its financial success.
# person.person_name: The 'person name' column in the 'person' table of the 'movies_4' database stores text entries representing individual names, with examples like 'Matthew Ferguson', 'Joe Guzman', and 'Reilly Dolman'.
```
question = "What is the average revenue of the movie in which Dariusz Wolski works as the director of photography?"
evidence = "director of photography refers to job = 'Director of Photography'; average revenue = divide(sum(revenue), count(movie_id))"
```gold SR
df1 = df.where(element = person.person_name, filter = 'Dariusz Wolski')
df2 = df1.where(element = movie_crew.job, filter = 'Director of Photography')
res = df2.select(cast(df2.sum(movie.revenue), real) / df2.count(movie.movie_id))
```
Output2:
```SR
df1 = df.where(element = person.person_name, filter = 'Dariusz Wolski')
res = df1.select(df1.avg(movie.revenue) / df1.count(movie.movie_id))
```

Example3:
schema = ['Person.person_id', 'Credit.person_id', 'Credit.role', 'Person.name', 'Person.birthdate']
```column description
# Person.person_id: The 'person id' column in the 'Person' table of the 'law_episode' database is a text field serving as a unique identifier for each person, with examples like 'nm0406320', 'nm0346718', 'nm0149920'.
# Credit.person_id: The 'person id' column in the 'Credit' table of the 'law_episode' database stores text identifiers unique to individuals associated with credit information, exemplified by values like 'nm0508139', 'nm3093316', 'nm0514445'.
# Credit.role: In the 'Credit' table of the 'law_episode' database, the 'role' column, of type text, specifies the recognition a person receives: for actors, it's the character's name they portrayed (e.g., 'Officer Blackledge'), and for non-actors, it's their production role (e.g., 'post-production supervisor').
# Person.name: In the 'Person' table of the 'law_episode' database, the 'name' column stores text data representing individual names, such as 'Al DeChristo', 'Isa Thomas', and 'Gustave Johnson'.
# Person.birthdate: The 'birth date' column in the 'Person' table of the 'law_episode' database stores the date of birth of individuals as a 'date' type. If the value is null, the birthdate is unknown. Examples include '1963-04-27', '1947-04-26', '1964-04-07'.
```
question = "Who is the youngest person to ever play a "clerk" role in the series?"
evidence = "who refers to name; the youngest person refers to max(birthdate); a "clerk" role refers to role = 'Clerk'"
```gold SR
df1 = df.where(element = Credit.role, filter = 'Clerk')
df2 = df1.where(element = Person.birthdate, filter = 'is not null')
res = df2.orderby(by = Person.birthdate, desc).limit(1).select(Person.name)
```
Output3:
```SR
df1 = df.where(element = Credit.role, filter = 'Clerk')
res = df1.orderby(by = Person.birthdate).select(Person.person_id)
```

Example4:
schema = ['country.origin', 'data.ID', 'production.ID', 'data.mpg', 'country.country', 'production.country']
```column description
# country.origin: The 'origin' column in the 'country' table of the 'cars' database is an integer that serves as the unique identifier for the origin country.
# data.ID: Unique integer identifier for each car in the 'data' table of the 'cars' database.
# production.ID: The 'ID' column in the 'production' table of the 'cars' database is an integer representing the unique identifier of each car.
# data.mpg: In the 'cars' database, within the 'data' table, the 'mileage per gallon' column, of type real, records the car's fuel efficiency in miles per gallon, indicating that a higher value signifies greater fuel efficiency.
# country.country: The 'country' column in the 'country' table of the 'cars' database stores text values indicating the origin country of the car, with possible values being 'Europe', 'Japan', or 'USA'.
# production.country: The 'country' column in the 'production' table of the 'cars' database stores integer IDs representing the country of origin for each car, mapping to regions such as Japan to Asia and the USA to North America.
```
question = "Which country produced the car with the lowest mileage per gallon?"
evidence = "the lowest mileage per gallon refers to min(mpg)"
```gold SR
df1 = df.orderby(by = data.mpg, asc).limit(1)
res = df1.select(country.country)
```
Output4:
```SR
df1 = df.orderby(by = data.mpg, asc).limit(1).groupby(country.country)
res = df1.select(country.country, data.mpg)
```

Now generating the SR that contains error for the following text-to-SQL instances:
schema = {schema}
```column description
{column_description}
```
question = "{question}"
evidence = "{evidence}"
```gold SR
{sr}
``

Fill in the following template using your answer.
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


