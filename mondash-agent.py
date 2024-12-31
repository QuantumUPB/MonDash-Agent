import asyncio
import aiohttp
import json
import os
import time

from qkd_benchmark.benchmarkdan import QKD_Benchmark

def parse_log_file(log_file_path):
    if not os.path.exists(log_file_path):
        return []

    log_entries = []
    with open(log_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                log_entries.append(line)
    return log_entries

async def periodic_aggregate_and_send(qkd_benchmark, aggregator_url, interval=10):
    """
    Periodically reads the log file to gather benchmark results, fetches path statuses,
    and sends a JSON payload to an external server.
    """
    while True:
        print(f"[INFO] Running benchmark at {time.strftime('%X')} ...")
        # This will create a new benchmark log file each time you instantiate
        # QKD_Benchmark (due to the timestamp in __init__).
        await qkd_benchmark.run_benchmark("w")

        print("[INFO] Benchmark execution finished.")
        print(f"[INFO] Aggregating results at {time.strftime('%X')} ...")

        # 1) Parse the latest log file from QKD_Benchmark
        keyrates = parse_log_file(qkd_benchmark.benchmark_log_file)

        async with aiohttp.ClientSession() as session:
            # 2) Collect the latest statuses
            status_map = {}
            for path in qkd_benchmark.paths:
                status = await qkd_benchmark.get_status_path(path, session)
                key = f"{path['source']['SAE']} -> {path['destination']['SAE']}"
                status_map[key] = status

            # Build the aggregated data as a dictionary (or any structure) 
            payload = {
                "timestamp": time.time(),
                "keyrates": keyrates,
                "path_statuses": status_map
            }

            # 3) Send to aggregator server
            try:
                async with session.post(aggregator_url, json=payload) as resp:
                    if resp.status == 200:
                        print("[INFO] Successfully sent aggregated data.")
                    else:
                        print("[WARN] Failed to send aggregated data, status:", resp.status)
            except Exception as e:
                print("[ERROR] Exception while sending data:", e)

        await asyncio.sleep(interval)

###############################################################################
# 3. Main entry point
###############################################################################
async def main():
    # --------------------------------------------------------------------------
    # 1) Load your static_data and topology_data
    # --------------------------------------------------------------------------
    with open('static_data.json', 'r') as f:
        static_data = json.load(f)
    with open('topology_data.json', 'r') as f:
        topology_data = json.load(f)

    # --------------------------------------------------------------------------
    # 2) Directories for certificates/experiments
    # --------------------------------------------------------------------------
    certificates_dir = "./certs"  
    experiment_dir = "./experiments"
    os.makedirs(certificates_dir, exist_ok=True)
    os.makedirs(experiment_dir, exist_ok=True)

    # --------------------------------------------------------------------------
    # 3) Instantiate QKD_Benchmark
    #
    #    Note: Because QKD_Benchmark sets self.benchmark_log_file using the
    #    current timestamp, it will generate a new log file each time you run
    #    this script. If you want to append to the same file, modify the class.
    # --------------------------------------------------------------------------
    qkd_benchmark = QKD_Benchmark(
        static_data=static_data,
        topology_data=topology_data,
        certificates_dir=certificates_dir,
        experiment_dir=experiment_dir,
        bidirectional=True
    )

    aggregator_url = "https://example.com/aggregator"  # Replace with real endpoint
    task_aggregate = asyncio.create_task(periodic_aggregate_and_send(qkd_benchmark, aggregator_url, interval=60))

    await asyncio.gather(task_aggregate)

if _name_ == '_main_':
    asyncio.run(main())