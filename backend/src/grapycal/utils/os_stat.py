import os
import psutil
from grapycal.extension_api.utils import has_lib_checker


class OSStat:
    def __init__(self):
        self.process = psutil.Process(os.getpid())

    def get_os_stat(self):
        ram_total = psutil.virtual_memory().total
        ram_this = self.process.memory_info().rss
        ram_used = psutil.virtual_memory().used

        cpu_this = self.process.cpu_percent() / psutil.cpu_count()
        cpu_used = psutil.cpu_percent()

        res = {
            "ram": {
                "total": ram_total,
                "this": ram_this,
                "used": ram_used,
                "other": ram_used - ram_this,  # "other" means "other process"
                "remain": ram_total - ram_used,
            },
            "cpu": {
                "total": 100,
                "this": cpu_this,
                "used": cpu_used,
                "other": cpu_used - cpu_this,  # "other" means "other process"
                "remain": 100 - cpu_used,
            },
        }

        if has_lib_checker.has_lib("torch"):
            import torch

            if torch.cuda.is_available():
                gpu_this = torch.cuda.memory_allocated()
                gpu_used = torch.cuda.mem_get_info()[1] - torch.cuda.mem_get_info()[0]
                gpu_total = torch.cuda.get_device_properties(0).total_memory

                res["gpu_mem"] = {
                    "total": gpu_total,
                    "this": gpu_this,
                    "used": gpu_used,
                    "other": gpu_used - gpu_this,  # "other" means "other process"
                    "remain": gpu_total - gpu_used,
                }

        return res
