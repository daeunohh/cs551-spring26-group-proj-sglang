#!/usr/bin/env bash

# 데이터셋 모드 (SGLang 내부 합성 데이터셋 포함)
DATASETS=("sharegpt" "random" "random-ids" "generated-shared-prefix")

# 테스트를 위해 요청 수를 30개로 대폭 수정
NUM_PROMPTS=4000
HOST="127.0.0.1"
PORT=30000
METRICS_URL="http://localhost:9400/metrics"
RATE=32
CONC=32

echo "======================================================"
echo "🧪 [TEST RUN] 30 Requests per Dataset"
echo "======================================================"

for DS in "${DATASETS[@]}"; do
    echo "------------------------------------------------------"
    echo "🔍 Testing Mode: $DS"
    echo "------------------------------------------------------"
    
    # 1. 성능 벤치마크 테스트
    # echo "[Step 1] Running bench_serve.sh..."
    # bash scripts/bench_serve.sh "$DS" "$NUM_PROMPTS" "$HOST" "$PORT" "$RATE" "$CONC"
    
    # if [ $? -ne 0 ]; then
    #     echo "❌ $DS 성능 테스트 실패! 포트나 설정을 확인하세요."
    #     exit 1
    # fi

    # sleep 5

    # 2. 에너지 측정 테스트
    echo "Running run_benchmark_with_energy.sh..."
    bash scripts/run_benchmark_with_energy.sh \
        "$DS" "$NUM_PROMPTS" "$HOST" "$PORT" "$METRICS_URL" "$RATE" "$CONC" 1 10
    
    if [ $? -ne 0 ]; then
        echo "❌ $DS 에너지 측정 실패! DCGM 포트(9400)를 확인하세요."
        exit 1
    fi

    echo "✅ $DS 완료! 다음 작업을 위해 30초 대기..."
    sleep 30
    echo "------------------------------------------------------"
done

echo "======================================================"
echo "🎉 모든 데이터셋 모드 테스트 완료!"
echo "======================================================"

