BASE_DIR="$(pwd)"
echo $BASE_DIR

DATA_CONFIG_PATH="${BASE_DIR}/configs/data_config.json"
INTERMEDIATE_CONFIG_PATH="${BASE_DIR}/configs/intermediate_config.json"
OUTPUT_DIR="${BASE_DIR}/outputs/train"

bird_teacher_sql2sr_path="$OUTPUT_DIR/bird_teacher_sql2sr.jsonl"
spider_teacher_sql2sr_path="$OUTPUT_DIR/spider_teacher_sql2sr.jsonl"
python ./src/train/sql2sr_for_teacher.py --data_config_path $DATA_CONFIG_PATH --intermediate_config_path $INTERMEDIATE_CONFIG_PATH --bird_teacher_sql2sr_path $bird_teacher_sql2sr_path --spider_teacher_sql2sr_path $spider_teacher_sql2sr_path

bird_converted_sql_path="$OUTPUT_DIR/bird_teacher_converted_sql.jsonl"
spider_converted_sql_path="$OUTPUT_DIR/spider_teacher_converted_sql.jsonl"
python ./src/train/sr2sql_convertion.py --data_config_path $DATA_CONFIG_PATH --intermediate_config_path $INTERMEDIATE_CONFIG_PATH --bird_converted_sql_path $bird_converted_sql_path --spider_converted_sql_path $spider_converted_sql_path

bird_validated_sr_path="$OUTPUT_DIR/bird_teacher_validated_sr.jsonl"
spider_validated_sr_path="$OUTPUT_DIR/spider_teacher_validated_sr.jsonl"
python ./src/train/sr_validation.py --data_config_path $DATA_CONFIG_PATH --intermediate_config_path $INTERMEDIATE_CONFIG_PATH --bird_validated_sr_path $bird_validated_sr_path --spider_validated_sr_path $spider_validated_sr_path

python ./src/train/prepare_data_for_bam.py --data_config_path $DATA_CONFIG_PATH --intermediate_config_path $INTERMEDIATE_CONFIG_PATH --bam_train_data_name "bam_train_data"