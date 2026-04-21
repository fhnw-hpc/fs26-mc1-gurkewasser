#!/bin/bash
set -e

E2E_DIR="e2e_data"
COMPOSE_FILE="docker-compose-e2e.yaml"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "============================================================"
echo "  E2E Performance Analysis - Experiment Runner"
echo "============================================================"

clean_data() {
    echo "[1/6] Cleaning old data..."
    rm -f ${E2E_DIR}/*.csv
    rm -f data/*.csv
    rm -f ${E2E_DIR}/plots/*.png
    mkdir -p ${E2E_DIR}/plots
}

save_experiment() {
    local exp_name=$1
    local exp_dir="${E2E_DIR}/${exp_name}"
    echo "[save] Saving experiment data to ${exp_dir}/..."
    mkdir -p ${exp_dir}
    cp ${E2E_DIR}/e2e_simple_latency.csv ${exp_dir}/ 2>/dev/null || true
    cp ${E2E_DIR}/e2e_alerts_latency.csv ${exp_dir}/ 2>/dev/null || true
    cp ${E2E_DIR}/e2e_throughput_simple.csv ${exp_dir}/ 2>/dev/null || true
    cp ${E2E_DIR}/e2e_throughput_alerts.csv ${exp_dir}/ 2>/dev/null || true
}

clean_running_csvs() {
    echo "[clean] Removing CSV files from ${E2E_DIR}/ (stack is stopped)..."
    rm -f ${E2E_DIR}/e2e_simple_latency.csv
    rm -f ${E2E_DIR}/e2e_alerts_latency.csv
    rm -f ${E2E_DIR}/e2e_throughput_simple.csv
    rm -f ${E2E_DIR}/e2e_throughput_alerts.csv
    rm -f ${E2E_DIR}/e2e_stability_metrics.csv
}

start_stack() {
    echo "[2/6] Starting Kafka cluster + application stack..."
    docker compose -f ${COMPOSE_FILE} up -d "$@"
    echo "[2/6] Waiting 25s for services to initialize..."
    sleep 25
}

stop_stack() {
    echo "[5/6] Sending SIGTERM to containers for graceful shutdown..."
    docker compose -f ${COMPOSE_FILE} stop -t 10 2>/dev/null || true
    echo "[5/6] Removing containers..."
    docker compose -f ${COMPOSE_FILE} down
}

analyze() {
    local exp_dir=$1
    if [ -n "${exp_dir}" ]; then
        echo "[4/6] Running analysis on ${exp_dir}..."
        E2E_DATA_DIR="${exp_dir}" python3 analyze_e2e.py
    else
        echo "[4/6] Running analysis..."
        python3 analyze_e2e.py
    fi
}

create_kafka_topics() {
    echo "[3a/6] Ensuring topics exist..."
    docker compose -f ${COMPOSE_FILE} exec kafka1 kafka-topics --create --if-not-exists --bootstrap-server kafka1:9092 --topic room_temperature_mp --partitions 3 --replication-factor 3 2>/dev/null || true
    docker compose -f ${COMPOSE_FILE} exec kafka1 kafka-topics --create --if-not-exists --bootstrap-server kafka1:9092 --topic room_environment_mp --partitions 3 --replication-factor 3 2>/dev/null || true
    docker compose -f ${COMPOSE_FILE} exec kafka1 kafka-topics --create --if-not-exists --bootstrap-server kafka1:9092 --topic room_alerts_mp --partitions 3 --replication-factor 3 2>/dev/null || true
}

wait_and_collect() {
    local duration=$1
    local label=$2
    echo "[3b/6] Running E2E experiment: ${label} (${duration}s)..."
    echo "        Monitor logs: docker compose -f ${COMPOSE_FILE} logs -f e2e-monitor"
    sleep ${duration}
    echo "[3c/6] Collection period over."
}

echo ""
echo "Available experiments:"
echo "  1) Quick test      (~60s)  - Quick latency check"
echo "  2) Standard test   (~5min) - Standard E2E analysis"
echo "  3) Sustained load  (~10min)- Stability under sustained load"
echo "  4) Stress test     (~5min) - Multiple consumers for bottleneck detection"
echo "  5) Full analysis   (~15min)- Complete E2E analysis with all experiments"
echo "  6) Bottleneck test (~5min) - 3 generators + 1 processor (consumer starvation)"
echo ""

EXPERIMENT=${1:-2}

case ${EXPERIMENT} in
    1)
        RUN_DIR="exp1_quick_${TIMESTAMP}"
        echo ">>> Running Quick Test (~60s)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 60 "Quick Test"
        stop_stack
        save_experiment "${RUN_DIR}"
        analyze "${E2E_DIR}/${RUN_DIR}"
        ;;
    2)
        RUN_DIR="exp2_standard_${TIMESTAMP}"
        echo ">>> Running Standard E2E Test (~5min)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 300 "Standard Test"
        stop_stack
        save_experiment "${RUN_DIR}"
        analyze "${E2E_DIR}/${RUN_DIR}"
        ;;
    3)
        RUN_DIR="exp3_sustained_${TIMESTAMP}"
        echo ">>> Running Sustained Load Test (~10min)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 600 "Sustained Load"
        stop_stack
        save_experiment "${RUN_DIR}"
        analyze "${E2E_DIR}/${RUN_DIR}"
        ;;
    4)
        RUN_DIR="exp4_stress_${TIMESTAMP}"
        echo ">>> Running Stress Test (~5min with 3 consumers)"
        clean_data
        start_stack
        create_kafka_topics
        echo "Scaling data-processor to 3 instances..."
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3 --no-recreate kafka_generators kafka_sinks e2e_monitor 2>/dev/null || docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3
        wait_and_collect 300 "Stress Test (3 processors)"
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=1
        stop_stack
        save_experiment "${RUN_DIR}"
        analyze "${E2E_DIR}/${RUN_DIR}"
        ;;
    5)
        BASE_DIR="exp5_full_${TIMESTAMP}"
        echo ">>> Running Full Analysis (~15min)"
        echo ""
        echo "--- Experiment 1: Baseline (5min) ---"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 300 "Baseline"
        stop_stack
        save_experiment "${BASE_DIR}/exp1_baseline"

        echo ""
        echo "--- Experiment 2: Scaled consumers (5min) ---"
        clean_running_csvs
        start_stack
        create_kafka_topics
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3
        wait_and_collect 300 "Scaled Consumers (3 processors)"
        stop_stack
        save_experiment "${BASE_DIR}/exp2_scaled"

        echo ""
        echo "--- Experiment 3: Back to baseline for stability (5min) ---"
        clean_running_csvs
        start_stack
        create_kafka_topics
        wait_and_collect 300 "Stability"
        stop_stack
        save_experiment "${BASE_DIR}/exp3_stability"

        echo ""
        echo "--- Analyzing all 3 experiments ---"
        echo "[4/6] Running multi-experiment analysis..."
        python3 analyze_e2e.py --multi "${E2E_DIR}/${BASE_DIR}"
        ;;
    6)
        RUN_DIR="exp6_bottleneck_${TIMESTAMP}"
        echo ">>> Running Bottleneck Test (~5min, 3 generators + 1 processor)"
        clean_data
        start_stack --scale data-generator=3 --scale data-processor=1
        create_kafka_topics
        wait_and_collect 300 "Bottleneck Test (3 generators, 1 processor)"
        stop_stack
        save_experiment "${RUN_DIR}"
        analyze "${E2E_DIR}/${RUN_DIR}"
        ;;
    *)
        echo "Unknown experiment: ${EXPERIMENT}"
        echo "Usage: $0 [1|2|3|4|5|6]"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "  E2E experiment complete!"
echo "  Data: ${E2E_DIR}/"
echo "  Plots: ${E2E_DIR}/plots/"
echo "============================================================"