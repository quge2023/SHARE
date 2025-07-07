export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7

BASE_DIR="$(pwd)"
echo $BASE_DIR

DATA_CONFIG_PATH="${BASE_DIR}/configs/data_config.json"
INTERMEDIATE_CONFIG_PATH="${BASE_DIR}/configs/intermediate_config.json"
OUTPUT_DIR="${BASE_DIR}/outputs/train"
BAM_MODEL_PATH="${BASE_DIR}/model/bam"

python ./src/train/prepare_data_for_sam.py --data_config_path $DATA_CONFIG_PATH --intermediate_config_path $INTERMEDIATE_CONFIG_PATH --bam_model_path $BAM_MODEL_PATH --sam_train_data_name "sam_train_data"