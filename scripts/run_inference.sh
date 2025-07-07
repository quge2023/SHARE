BASE_DIR="$(pwd)"
echo $BASE_DIR

DATA_CONFIG_PATH="${BASE_DIR}/configs/data_config.json"
INPUT_PATH="${BASE_DIR}/data/bird/dev/baseline_sql.json"
OUTPUT_DIR="${BASE_DIR}/outputs/infer"
MODEL_DIR="${BASE_DIR}/model"

BAM_PATH="${MODEL_DIR}/bam"
SAM_PATH="${MODEL_DIR}/sam"
LOM_PATH="${MODEL_DIR}/lom"

python ./src/infer/run.py \
    --data_config_path $DATA_CONFIG_PATH \
    --output_dir $OUTPUT_DIR \
    --bam_model_path $BAM_PATH \
    --sam_model_path $SAM_PATH \
    --lom_model_path $LOM_PATH \
    --input_sql_path $INPUT_PATH \
