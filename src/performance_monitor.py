import psutil
import time

class PerformanceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.start_cpu_time = self.process.cpu_times()
        self.start_memory = self.process.memory_info()
        self.start_time = time.time()
    
    def get_stats(self):
        cpu_times = self.process.cpu_times()
        memory = self.process.memory_info()
        elapsed = time.time() - self.start_time
        
        return {
            'cpu_percent': self.process.cpu_percent(interval=0.1),
            'memory_mb': memory.rss / 1024 / 1024,
            'cpu_time_ms': (cpu_times.user + cpu_times.system) * 1000,
            'elapsed_s': elapsed
        }