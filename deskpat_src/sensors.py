import os
import sys
import socket
import platform

# ── Sensor Registry System ──────────────────────────────────
# Dictionary mapping sensor name keys to Python helper functions
SENSORS = {}

def sensor(name):
    """Decorator to register a custom system/OS telemetry sensor."""
    def decorator(func):
        SENSORS[name] = func
        return func
    return decorator

# ── Default Registered Sensors ──────────────────────────────

@sensor("username")
def get_username():
    """Get active operating system username."""
    import getpass
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER", os.environ.get("USERNAME", "Developer"))

@sensor("hostname")
def get_hostname():
    """Get active local computer hostname."""
    return socket.gethostname()

@sensor("os")
def get_os():
    """Get active operating system name and version release details."""
    return f"{platform.system()} {platform.release()}"

@sensor("local_ip")
def get_local_ip():
    """Get local network IP address by performing a socket lookup."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

@sensor("uptime")
def get_uptime():
    """Get system uptime in hours and minutes."""
    try:
        total_seconds = 0.0
        if os.name == "nt":
            import ctypes
            uptime_ms = ctypes.windll.kernel32.GetTickCount64()
            total_seconds = uptime_ms / 1000.0
        elif sys.platform == "darwin":
            import subprocess
            import re
            import time
            res = subprocess.run(['sysctl', '-n', 'kern.boottime'], capture_output=True, text=True)
            match = re.search(r'sec = (\d+)', res.stdout)
            if match:
                boot_time = int(match.group(1))
                total_seconds = time.time() - boot_time
        else:
            if os.path.exists('/proc/uptime'):
                with open('/proc/uptime', 'r') as f:
                    total_seconds = float(f.readline().split()[0])
                    
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return {
            "hours": int(hours),
            "minutes": int(minutes)
        }
    except Exception:
        return {"hours": 0, "minutes": 0}

@sensor("ram_used_gb")
def get_ram_used_gb():
    """Get active system physical RAM memory usage in gigabytes."""
    try:
        total, used, _ = _query_ram_stats()
        return used
    except Exception:
        return 0.0

@sensor("ram_total_gb")
def get_ram_total_gb():
    """Get total system physical RAM memory in gigabytes."""
    try:
        total, used, _ = _query_ram_stats()
        return total
    except Exception:
        return 0.0

@sensor("ram_usage_percent")
def get_ram_usage_percent():
    """Get current percentage memory load of the system RAM."""
    try:
        _, _, percent = _query_ram_stats()
        return percent
    except Exception:
        return 0

# ── Private Helper Functions ────────────────────────────────

def _query_ram_stats():
    """Query system physical memory statistics in a platform-agnostic way."""
    if os.name == "nt":
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_uint64),
                ('ullAvailPhys', ctypes.c_uint64),
                ('ullTotalPageFile', ctypes.c_uint64),
                ('ullAvailPageFile', ctypes.c_uint64),
                ('ullTotalVirtual', ctypes.c_uint64),
                ('ullAvailVirtual', ctypes.c_uint64),
                ('ullAvailExtendedVirtual', ctypes.c_uint64)
            ]
        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        
        total_ram = mem.ullTotalPhys / (1024**3)
        avail_ram = mem.ullAvailPhys / (1024**3)
        used_ram = total_ram - avail_ram
        ram_percent = mem.dwMemoryLoad
        return round(total_ram, 1), round(used_ram, 1), ram_percent

    elif sys.platform == "darwin":
        import subprocess
        import re
        try:
            # Query memory size
            total_bytes = int(subprocess.check_output(['sysctl', '-n', 'hw.memsize']).strip())
            total_ram = total_bytes / (1024**3)
            
            # Query pages
            page_size = 4096
            vm_lines = subprocess.check_output(['vm_stat']).decode('utf-8').split('\n')
            for line in vm_lines:
                if 'page size of' in line:
                    match = re.search(r'page size of (\d+) bytes', line)
                    if match:
                        page_size = int(match.group(1))
                        break
                        
            free_pages = 0
            speculative_pages = 0
            for line in vm_lines:
                if 'Pages free:' in line:
                    free_pages = int(line.split()[-1].replace('.', ''))
                elif 'Pages speculative:' in line:
                    speculative_pages = int(line.split()[-1].replace('.', ''))
                    
            free_bytes = (free_pages + speculative_pages) * page_size
            used_bytes = total_bytes - free_bytes
            used_ram = used_bytes / (1024**3)
            ram_percent = int((used_bytes / total_bytes) * 100) if total_bytes > 0 else 0
            return round(total_ram, 1), round(used_ram, 1), ram_percent
        except Exception:
            pass

    else:
        # Linux /proc/meminfo fallback
        try:
            mem_info = {}
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_info[parts[0].rstrip(':')] = int(parts[1])
            total_kb = mem_info.get('MemTotal', 0)
            free_kb = mem_info.get('MemFree', 0)
            buffers_kb = mem_info.get('Buffers', 0)
            cached_kb = mem_info.get('Cached', 0)
            avail_kb = mem_info.get('MemAvailable', free_kb + buffers_kb + cached_kb)
            used_kb = total_kb - avail_kb
            
            total_ram = total_kb / (1024**2)
            used_ram = used_kb / (1024**2)
            ram_percent = int((used_kb / total_kb) * 100) if total_kb > 0 else 0
            return round(total_ram, 1), round(used_ram, 1), ram_percent
        except Exception:
            pass

    return 0.0, 0.0, 0
