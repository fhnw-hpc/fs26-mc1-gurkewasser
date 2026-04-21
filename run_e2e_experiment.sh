#!/bin/bash
set -e

E2E_DIR="e2e_data"
COMPOSE_FILE="docker-compose-e2e.yaml"

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

start_stack() {
    echo "[2/6] Starting Kafka cluster + application stack..."
    docker compose -f ${COMPOSE_FILE} up -d
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
    echo "[4/6] Running analysis..."
    python3 analyze_e2e.py
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
echo ""

EXPERIMENT=${1:-2}

case ${EXPERIMENT} in
    1)
        echo ">>> Running Quick Test (~60s)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 60 "Quick Test"
        stop_stack
        analyze
        ;;
    2)
        echo ">>> Running Standard E2E Test (~5min)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 300 "Standard Test"
        stop_stack
        analyze
        ;;
    3)
        echo ">>> Running Sustained Load Test (~10min)"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 600 "Sustained Load"
        stop_stack
        analyze
        ;;
    4)
        echo ">>> Running Stress Test (~5min with 3 consumers)"
        clean_data
        start_stack
        create_kafka_topics
        echo "Scaling data-processor to 3 instances..."
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3 --no-recreate kafka_generators kafka_sinks e2e_monitor 2>/dev/null || docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3
        wait_and_collect 300 "Stress Test (3 processors)"
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=1
        stop_stack
        analyze
        ;;
    5)
        echo ">>> Running Full Analysis (~15min)"
        echo ""
        echo "--- Experiment 1: Baseline (5min) ---"
        clean_data
        start_stack
        create_kafka_topics
        wait_and_collect 300 "Baseline"
        echo "Saving baseline data..."
        cp ${E2E_DIR}/e2e_simple_latency.csv ${E2E_DIR}/plots/exp1_simple_latency.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_alerts_latency.csv ${E2E_DIR}/plots/exp1_alerts_latency.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_throughput_simple.csv ${E2E_DIR}/plots/exp1_throughput_simple.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_throughput_alerts.csv ${E2E_DIR}/plots/exp1_throughput_alerts.csv 2>/dev/null || true

        echo ""
        echo "--- Experiment 2: Scaled consumers (5min) ---"
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=3
        wait_and_collect 300 "Scaled Consumers (3 processors)"

        echo "Saving scaled data..."
        cp ${E2E_DIR}/e2e_simple_latency.csv ${E2E_DIR}/plots/exp2_simple_latency.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_alerts_latency.csv ${E2E_DIR}/plots/exp2_alerts_latency.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_throughput_simple.csv ${E2E_DIR}/plots/exp2_throughput_simple.csv 2>/dev/null || true
        cp ${E2E_DIR}/e2e_throughput_alerts.csv ${E2E_DIR}/plots/exp2_throughput_alerts.csv 2>/dev/null || true

        echo ""
        echo "--- Experiment 3: Back to baseline for stability (5min) ---"
        docker compose -f ${COMPOSE_FILE} up -d --scale data-processor=1
        wait_and_collect 300 "Stability"

        stop_stack
        analyze
        ;;
    *)
        echo "Unknown experiment: ${EXPERIMENT}"
        echo "Usage: $0 [1|2|3|4|5]"
        exit 1
        ;;
esac

echo ""
echo "============================================================"
echo "  E2E experiment complete!"
echo "  Data: ${E2E_DIR}/"
echo "  Plots: ${E2E_DIR}/plots/"
echo "============================================================"