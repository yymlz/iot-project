# run_baseline_test.py
import subprocess, time, os, signal

print("=== TinyTelemetry Baseline Local Test ===")

# 1. Start server process (logs output to file)
server_log = open("server_log.txt", "w")
server_proc = subprocess.Popen(
    ["python", os.path.join("..", "src", "server.py")],
    stdout=server_log,
    stderr=subprocess.STDOUT
)
print("Server started...")

# 2. Wait a moment for server to initialize
time.sleep(1)

# 3. Run client process (prints to console)
subprocess.run(["python", os.path.join("..", "src", "client.py")])

# 4. Allow a few seconds for final packets
time.sleep(2)

# 5. Terminate server process
server_proc.terminate()
server_proc.wait(timeout=2)
server_log.close()

print("\nBaseline local test complete!")
print("Check server_log.txt for received packet details.")
