import sys
import os
import subprocess
import argparse
import json
import requests

# ── ANSI Styling Definitions ────────────────────────────────
class Style:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    
    GREEN = "\033[92m"      # Primary Monitor
    CYN = "\033[96m"        # Secondary Monitor 1
    YELLOW = "\033[93m"     # Secondary Monitor 2
    MAGENTA = "\033[95m"    # Secondary Monitor 3
    RED = "\033[91m"        # Errors
    GRAY = "\033[90m"       # Muted text / borders
    
    PALETTE = [CYN, YELLOW, MAGENTA]

def enable_vt_processing():
    """Enable virtual terminal processing for ANSI colors on supported platforms."""
    if os.name != "nt":
        return
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        h_out = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(h_out, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)
    except Exception:
        pass


def check_python_dependencies():
    """Ensure Pillow is installed in the python environment."""
    try:
        from PIL import Image
    except ImportError:
        print(f"  {Style.YELLOW}Pillow (PIL) library not found. Installing via pip...{Style.RESET}")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pillow"], check=True)
            print(f"  {Style.GREEN}Pillow installed successfully.{Style.RESET}")
        except Exception as e:
            print(f"  {Style.RED}Error installing Pillow:{Style.RESET} {e}")
            sys.exit(1)

def check_npm_dependencies():
    """Ensure node_modules/puppeteer is installed in deskpat_src."""
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    node_modules = os.path.join(deskpat_src_dir, "node_modules")
    puppeteer_dir = os.path.join(node_modules, "puppeteer")
    if not os.path.exists(node_modules) or not os.path.exists(puppeteer_dir):
        print(f"  {Style.YELLOW}Puppeteer node modules not found. Running npm install...{Style.RESET}")
        try:
            # Check if npm is available
            subprocess.run(["npm", "--version"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            print(f"  {Style.RED}Error:{Style.RESET} Node.js / npm not found in PATH. Please install Node.js and try again.")
            sys.exit(1)
            
        try:
            subprocess.run(["npm", "install"], cwd=deskpat_src_dir, check=True)
            print(f"  {Style.GREEN}Puppeteer installed successfully.{Style.RESET}")
        except Exception as e:
            print(f"  {Style.RED}Error running npm install:{Style.RESET} {e}")
            sys.exit(1)


def get_monitor_data():
    """Query connected display monitor information across different operating systems."""
    monitors = []

    if os.name == "nt":
        try:
            import ctypes
            from ctypes import wintypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

            class MONITORINFOEXW(ctypes.Structure):
                _fields_ = [
                    ('cbSize', wintypes.DWORD),
                    ('rcMonitor', wintypes.RECT),
                    ('rcWork', wintypes.RECT),
                    ('dwFlags', wintypes.DWORD),
                    ('szDevice', wintypes.WCHAR * 32)
                ]

            class DEVMODEW(ctypes.Structure):
                _fields_ = [
                    ('dmDeviceName', wintypes.WCHAR * 32),
                    ('dmSpecVersion', wintypes.WORD),
                    ('dmDriverVersion', wintypes.WORD),
                    ('dmSize', wintypes.WORD),
                    ('dmDriverExtra', wintypes.WORD),
                    ('dmFields', wintypes.DWORD),
                    ('dmPosition', wintypes.POINT),
                    ('dmDisplayOrientation', wintypes.DWORD),
                    ('dmDisplayFixedOutput', wintypes.DWORD),
                    ('dmColor', ctypes.c_short),
                    ('dmDuplex', ctypes.c_short),
                    ('dmYResolution', ctypes.c_short),
                    ('dmTTOption', ctypes.c_short),
                    ('dmCollate', ctypes.c_short),
                    ('dmFormName', wintypes.WCHAR * 32),
                    ('dmLogPixels', wintypes.WORD),
                    ('dmBitsPerPel', wintypes.DWORD),
                    ('dmPelsWidth', wintypes.DWORD),
                    ('dmPelsHeight', wintypes.DWORD),
                    ('dmDisplayFlags', wintypes.DWORD),
                    ('dmDisplayFrequency', wintypes.DWORD),
                    ('dmICMMethod', wintypes.DWORD),
                    ('dmICMIntent', wintypes.DWORD),
                    ('dmMediaType', wintypes.DWORD),
                    ('dmDitherType', wintypes.DWORD),
                    ('dmReserved1', wintypes.DWORD),
                    ('dmReserved2', wintypes.DWORD),
                    ('dmPanningWidth', wintypes.DWORD),
                    ('dmPanningHeight', wintypes.DWORD),
                ]

            def monitor_enum_proc(h_monitor, hdc_monitor, lprc_monitor, lparam):
                info = MONITORINFOEXW()
                info.cbSize = ctypes.sizeof(MONITORINFOEXW)
                if ctypes.windll.user32.GetMonitorInfoW(h_monitor, ctypes.byref(info)):
                    # Get Monitor DPI
                    dpi_x = ctypes.c_uint(96)
                    dpi_y = ctypes.c_uint(96)
                    try:
                        ctypes.windll.shcore.GetDpiForMonitor(h_monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))
                        dpi = dpi_x.value
                    except Exception:
                        dpi = 96
                    
                    # Get Refresh Rate
                    refresh_rate = 0
                    devmode = DEVMODEW()
                    devmode.dmSize = ctypes.sizeof(DEVMODEW)
                    if ctypes.windll.user32.EnumDisplaySettingsW(info.szDevice, -1, ctypes.byref(devmode)):
                        refresh_rate = devmode.dmDisplayFrequency

                    rect = (info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom)
                    work = (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
                    
                    monitors.append({
                        'device': info.szDevice,
                        'primary': bool(info.dwFlags & 1),
                        'rect': rect,
                        'work': work,
                        'width': rect[2] - rect[0],
                        'height': rect[3] - rect[1],
                        'dpi': dpi,
                        'scale': round((dpi / 96.0) * 100),
                        'refresh_rate': refresh_rate
                    })
                return True

            MonitorEnumProcType = ctypes.WINFUNCTYPE(
                ctypes.c_bool,
                ctypes.c_void_p,
                ctypes.c_void_p,
                ctypes.POINTER(wintypes.RECT),
                ctypes.c_void_p
            )

            proc = MonitorEnumProcType(monitor_enum_proc)
            ctypes.windll.user32.EnumDisplayMonitors(None, None, proc, 0)
        except Exception:
            pass

    elif sys.platform == "darwin":
        try:
            import re
            output = subprocess.check_output(["system_profiler", "SPDisplaysDataType"], text=True)
            resolutions = re.findall(r"Resolution:\s*(\d+)\s*[xX]\s*(\d+)", output)
            for idx, (w_str, h_str) in enumerate(resolutions):
                width, height = int(w_str), int(h_str)
                monitors.append({
                    'device': f'Display{idx+1}',
                    'primary': idx == 0,
                    'rect': (idx * width, 0, (idx + 1) * width, height),
                    'work': (idx * width, 0, (idx + 1) * width, height - 40),
                    'width': width,
                    'height': height,
                    'dpi': 144 if 'Retina' in output else 72,
                    'scale': 200 if 'Retina' in output else 100,
                    'refresh_rate': 60
                })
        except Exception:
            pass

    elif os.name != "nt":
        try:
            import re
            output = subprocess.check_output(["xrandr"], text=True)
            for match in re.finditer(r"(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)", output):
                dev = match.group(1)
                primary = bool(match.group(2))
                w, h = int(match.group(3)), int(match.group(4))
                x, y = int(match.group(5)), int(match.group(6))
                monitors.append({
                    'device': dev,
                    'primary': primary,
                    'rect': (x, y, x + w, y + h),
                    'work': (x, y, x + w, y + h - 40),
                    'width': w,
                    'height': h,
                    'dpi': 96,
                    'scale': 100,
                    'refresh_rate': 60
                })
        except Exception:
            pass

    if not monitors:
        monitors.append({
            'device': 'DefaultDisplay',
            'primary': True,
            'rect': (0, 0, 1920, 1080),
            'work': (0, 0, 1920, 1040),
            'width': 1920,
            'height': 1080,
            'dpi': 96,
            'scale': 100,
            'refresh_rate': 60
        })

    monitors.sort(key=lambda m: (not m['primary'], m['rect'][0]))
    return monitors


def render_ascii_layout(monitors):
    """Draw a scaled visual arrangement of the displays on the terminal."""
    if not monitors:
        return
        
    min_x = min(m['rect'][0] for m in monitors)
    max_x = max(m['rect'][2] for m in monitors)
    min_y = min(m['rect'][1] for m in monitors)
    max_y = max(m['rect'][3] for m in monitors)
    
    total_w = max_x - min_x
    total_h = max_y - min_y
    if total_w <= 0 or total_h <= 0:
        return
        
    TARGET_GRID_WIDTH = 58
    CHAR_ASPECT_RATIO = 2.0
    scale_factor = total_w / TARGET_GRID_WIDTH
    grid_h = int((total_h / scale_factor) / CHAR_ASPECT_RATIO)
    grid_h = max(8, min(grid_h, 20))
    grid_w = TARGET_GRID_WIDTH
    
    grid = [[(' ', None) for _ in range(grid_w)] for _ in range(grid_h)]
    
    display_colors = {}
    sec_idx = 0
    for idx, m in enumerate(monitors):
        if m['primary']:
            display_colors[m['device']] = Style.GREEN
        else:
            display_colors[m['device']] = Style.PALETTE[sec_idx % len(Style.PALETTE)]
            sec_idx += 1
            
    for idx, m in enumerate(monitors):
        color = display_colors[m['device']]
        left = int((m['rect'][0] - min_x) / scale_factor)
        right = int((m['rect'][2] - min_x) / scale_factor) - 1
        top = int(((m['rect'][1] - min_y) / scale_factor) / CHAR_ASPECT_RATIO)
        bottom = int(((m['rect'][3] - min_y) / scale_factor) / CHAR_ASPECT_RATIO) - 1
        
        left = max(0, min(left, grid_w - 1))
        right = max(0, min(right, grid_w - 1))
        top = max(0, min(top, grid_h - 1))
        bottom = max(0, min(bottom, grid_h - 1))
        
        mon_grid_w = right - left + 1
        mon_grid_h = bottom - top + 1
        
        if mon_grid_w < 3 or mon_grid_h < 3:
            if right < grid_w - 1: right = min(right + 1, grid_w - 1)
            else: left = max(0, left - 1)
            if bottom < grid_h - 1: bottom = min(bottom + 1, grid_h - 1)
            else: top = max(0, top - 1)
            mon_grid_w = right - left + 1
            mon_grid_h = bottom - top + 1
            
        grid[top][left] = ('┌', color)
        grid[top][right] = ('┐', color)
        grid[bottom][left] = ('└', color)
        grid[bottom][right] = ('┘', color)
        
        for c in range(left + 1, right):
            grid[top][c] = ('─', color)
            grid[bottom][c] = ('─', color)
        for r in range(top + 1, bottom):
            grid[r][left] = ('│', color)
            grid[r][right] = ('│', color)
        for r in range(top + 1, bottom):
            for c in range(left + 1, right):
                grid[r][c] = ('░', Style.GRAY)
                
        box_inner_w = right - left - 1
        box_inner_h = bottom - top - 1
        
        lines = []
        if box_inner_w >= 14 and box_inner_h >= 4:
            lines.append(f"DISPLAY {idx+1}")
            lines.append(f"{m['width']}x{m['height']}")
            lines.append(f"{m['scale']}% · {m['refresh_rate']}Hz")
            if m['primary']: lines.append("[PRIMARY]")
        elif box_inner_w >= 10 and box_inner_h >= 2:
            lines.append(f"DISP {idx+1}")
            lines.append(f"{m['width']}x{m['height']}")
            if m['primary']: lines.append("[PRI]")
        else:
            lines.append(f"D{idx+1}")
            
        start_row = top + 1 + (box_inner_h - len(lines)) // 2
        for offset_r, line in enumerate(lines):
            r = start_row + offset_r
            if top < r < bottom:
                truncated_line = line[:box_inner_w]
                centered_line = truncated_line.center(box_inner_w)
                for char_idx, char in enumerate(centered_line):
                    col_idx = left + 1 + char_idx
                    if char != ' ':
                        grid[r][col_idx] = (char, color)
                    
    print(f"  {Style.BOLD}{Style.UNDERLINE}Visual Layout Map:{Style.RESET}")
    print()
    for r in range(grid_h):
        line_str = "    "
        for c in range(grid_w):
            char, color = grid[r][c]
            if color:
                line_str += color + char + Style.RESET
            else:
                line_str += char
        print(line_str)
    print()

def get_aspect_ratio_str(w, h):
    def gcd(a, b):
        while b: a, b = b, a % b
        return a
    g = gcd(w, h)
    ar_w = round(w / g)
    ar_h = round(h / g)
    ratio = w / h
    common_ratios = [(16/9, "16:9"), (16/10, "16:10"), (4/3, "4:3"), (21/9, "21:9"), (32/9, "32:9"), (3/2, "3:2")]
    for r_val, r_str in common_ratios:
        if abs(ratio - r_val) < 0.02: return r_str
    return f"{ar_w}:{ar_h}"

def render_table(monitors):
    if not monitors:
        return
    
    print(f"  {Style.BOLD}{Style.UNDERLINE}Connected Display Details:{Style.RESET}")
    print()
    
    sec_idx = 0
    for idx, m in enumerate(monitors):
        color = Style.GREEN if m['primary'] else Style.PALETTE[sec_idx % len(Style.PALETTE)]
        if not m['primary']: sec_idx += 1
        
        role_str = "PRIMARY" if m['primary'] else "SECONDARY"
        pos_x, pos_y = m['rect'][0], m['rect'][1]
        ar_str = get_aspect_ratio_str(m['width'], m['height'])
        
        info_str = (
            f"  {Style.BOLD}Display {idx+1}:{Style.RESET} {color}{m['device']}{Style.RESET} · "
            f"{Style.BOLD}{m['width']}x{m['height']}{Style.RESET} ({ar_str}) · "
            f"{m['refresh_rate']}Hz · "
            f"Scale: {m['scale']}% · "
            f"[{role_str}] · "
            f"Position: X:{pos_x}, Y:{pos_y}"
        )
        print(info_str)
    print()

def fetch_and_save_data(url):
    """Fetch JSON or text data from a URL and save it to data.json."""
    try:
        print(f"  {Style.DIM}Fetching data from {url}...{Style.RESET}")
        r = requests.get(url, timeout=12)
        r.raise_for_status()
        
        try:
            data = r.json()
        except ValueError:
            data = {"raw_data": r.text}
            
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"  {Style.GREEN}Data fetched and saved to {data_path}{Style.RESET}")
        return data
    except Exception as e:
        print(f"  {Style.RED}Error fetching URL data:{Style.RESET} {e}")
        return None

def ensure_default_data(force=False):
    """Ensure data.json exists in deskpat_src, optionally overwriting it with defaults."""
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
    if force or not os.path.exists(data_path):
        default_data = {
            "title": "DESKPAT DEV ENVIRONMENT",
            "message": "Welcome back! Your screen rendering pipeline is active.",
            "quote": "Simplicity is the ultimate sophistication.",
            "author": "Leonardo da Vinci",
            "items": [
                "Verify DESKPAT script configuration",
                "Customize templates inside deskpat_src/templates",
                "Pass a --url argument to fetch real-time API data!"
            ]
        }
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=2)

def select_template():
    """Prompt the user to select an available template from deskpat_src/templates."""
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(deskpat_src_dir, "templates")
    
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
    templates = [d for d in os.listdir(templates_dir) if os.path.isdir(os.path.join(templates_dir, d))]
    
    if not templates:
        return "default"
        
    print(f"\n  {Style.BOLD}Available HTML Templates:{Style.RESET}")
    for i, t in enumerate(templates):
        print(f"    [{i+1}] {t}")
        
    try:
        val = input(f"\n  Select template number [1-{len(templates)}]: ").strip()
        idx = int(val) - 1
        if 0 <= idx < len(templates):
            return templates[idx]
    except Exception:
        pass
        
    print(f"  {Style.DIM}Defaulting to template 'default'{Style.RESET}")
    return "default"

def set_wallpaper_style_span():
    """Configure spanned wallpaper desktop settings if running on Windows."""
    if os.name == "nt":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "WallpaperStyle", 0, winreg.REG_SZ, "22")
            winreg.SetValueEx(key, "TileWallpaper", 0, winreg.REG_SZ, "0")
            winreg.CloseKey(key)
        except Exception as e:
            print(f"  {Style.YELLOW}Warning:{Style.RESET} Failed to set wallpaper Span settings: {e}")

def run_custom_script(script_name, extra_args=None):
    """Run a custom fetcher script in deskpat_src/scripts/ and output to data.json."""
    if extra_args is None:
        extra_args = []
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    scripts_dir = os.path.join(deskpat_src_dir, "scripts")
    script_path = os.path.join(scripts_dir, script_name)

    
    if not os.path.exists(script_path):
        print(f"  {Style.RED}Error:{Style.RESET} Script file '{script_name}' not found under scripts/.")
        return False
        
    print(f"  {Style.BOLD}Running custom data fetcher: '{script_name}'...{Style.RESET}")
    
    # Determine execution interpreter based on file extension
    ext = os.path.splitext(script_name)[1].lower()
    if ext == ".js":
        cmd = ["node", script_path] + extra_args
    elif ext == ".py":
        cmd = [sys.executable, script_path] + extra_args
    elif ext == ".ps1":
        cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script_path] + extra_args
    elif ext in [".bat", ".cmd"]:
        cmd = [script_path] + extra_args
    else:
        cmd = [script_path] + extra_args
        
    try:
        result = subprocess.run(
            cmd,
            cwd=deskpat_src_dir,
            shell=True if ext in [".bat", ".cmd"] else False,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        output_str = result.stdout.strip()
        try:
            parsed_data = json.loads(output_str)
            data_path = os.path.join(deskpat_src_dir, "data.json")
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(parsed_data, f, indent=2)
            
            print(f"  {Style.GREEN}Data fetched and saved to {data_path} successfully.{Style.RESET}")
            return True
        except ValueError as json_err:
            print(f"  {Style.RED}Error:{Style.RESET} Script stdout was not valid JSON: {json_err}")
            print(f"  Captured output: {output_str}")
            return False
            
    except subprocess.CalledProcessError as err:
        print(f"  {Style.RED}Error running script:{Style.RESET} {err}")
        print(f"  Script Stderr: {err.stderr}")
        output_str = (err.stdout or "").strip()
        if output_str:
            try:
                parsed_data = json.loads(output_str)
                data_path = os.path.join(deskpat_src_dir, "data.json")
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(parsed_data, f, indent=2)
                print(f"  {Style.YELLOW}Script failed but provided fallback JSON. Saved to {data_path}.{Style.RESET}")
                return True
            except ValueError:
                pass
        return False

def handle_todo_cli(args):
    """Local todo list CLI manager."""
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    todo_path = os.path.join(deskpat_src_dir, "todo.json")
    
    # Load existing todos
    todos = []
    if os.path.exists(todo_path):

        try:
            with open(todo_path, "r", encoding="utf-8") as f:
                todos = json.load(f)
        except Exception:
            pass
            
    if not args or args[0].lower() in ["list", "show"]:
        # List tasks
        if not todos:
            print("\n  No active tasks in your TODO list!")
            return False
        print(f"\n  {Style.BOLD}Your TODO List:{Style.RESET}")
        for i, t in enumerate(todos):
            status = "[✓]" if t.get("done") else "[ ]"
            color = Style.GRAY if t.get("done") else Style.CYN
            print(f"    {i+1}. {color}{status} {t.get('text')}{Style.RESET}")
        print()
        return False
        
    elif args[0].lower() == "add":
        if len(args) < 2:
            print(f"  {Style.RED}Error:{Style.RESET} Missing task text. Usage: deskpat todo add \"My new task\"")
            return False
        task_text = " ".join(args[1:])
        todos.append({"text": task_text, "done": False})
        
        try:
            with open(todo_path, "w", encoding="utf-8") as f:
                json.dump(todos, f, indent=2)
            print(f"  {Style.GREEN}Task added:{Style.RESET} {task_text}")
            return True
        except Exception as e:
            print(f"  {Style.RED}Error saving task:{Style.RESET} {e}")
            return False
            
    elif args[0].lower() in ["done", "complete", "toggle"]:
        if len(args) < 2:
            print(f"  {Style.RED}Error:{Style.RESET} Missing task index. Usage: deskpat todo done <index>")
            return False
        try:
            idx = int(args[1]) - 1
            if 0 <= idx < len(todos):
                todos[idx]["done"] = not todos[idx]["done"]
                status = "completed" if todos[idx]["done"] else "active"
                with open(todo_path, "w", encoding="utf-8") as f:
                    json.dump(todos, f, indent=2)
                print(f"  {Style.GREEN}Task marked as {status}:{Style.RESET} {todos[idx]['text']}")
                return True
            else:
                print(f"  {Style.RED}Error:{Style.RESET} Task index {args[1]} is out of range.")
                return False
        except ValueError:
            print(f"  {Style.RED}Error:{Style.RESET} Task index must be a number.")
            return False
            
    elif args[0].lower() in ["remove", "delete"]:
        if len(args) < 2:
            print(f"  {Style.RED}Error:{Style.RESET} Missing task index. Usage: deskpat todo remove <index>")
            return False
        try:
            idx = int(args[1]) - 1
            if 0 <= idx < len(todos):
                removed = todos.pop(idx)
                with open(todo_path, "w", encoding="utf-8") as f:
                    json.dump(todos, f, indent=2)
                print(f"  {Style.GREEN}Task removed:{Style.RESET} {removed['text']}")
                return True
            else:
                print(f"  {Style.RED}Error:{Style.RESET} Task index {args[1]} is out of range.")
                return False
        except ValueError:
            print(f"  {Style.RED}Error:{Style.RESET} Task index must be a number.")
            return False
            
    elif args[0].lower() == "clear":
        todos = []
        try:
            with open(todo_path, "w", encoding="utf-8") as f:
                json.dump(todos, f, indent=2)
            print(f"  {Style.GREEN}Todo list cleared successfully.{Style.RESET}")
            return True
        except Exception as e:
            print(f"  {Style.RED}Error clearing todo list:{Style.RESET} {e}")
            return False
            
    else:
        print(f"  {Style.RED}Unknown todo subcommand:{Style.RESET} {args[0]}")
        print("  Available subcommands: list, add, done, remove, clear")
        return False

def augment_payload_data():
    """Inject local system stats, config details, and todo items into data.json."""
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(deskpat_src_dir, "data.json")
    
    data = {}
    if os.path.exists(data_path):
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
            
    # 3. Query modular OS/system sensors
    try:
        import sensors
        system_stats = {}
        for name, func in sensors.SENSORS.items():
            try:
                system_stats[name] = func()
            except Exception as e:
                print(f"  {Style.YELLOW}Warning:{Style.RESET} Sensor '{name}' failed: {e}")
                system_stats[name] = None
        data["system"] = system_stats
    except ImportError:
        import socket
        import platform
        data["system"] = {
            "username": os.environ.get("USERNAME", "Developer"),
            "hostname": socket.gethostname(),
            "os": f"{platform.system()} {platform.release()}",
            "local_ip": "127.0.0.1",
            "ram_used_gb": 0.0,
            "ram_total_gb": 0.0,
            "ram_usage_percent": 0,
            "uptime": {"hours": 0, "minutes": 0}
        }
    
    todo_path = os.path.join(deskpat_src_dir, "todo.json")
    todos = []
    if os.path.exists(todo_path):
        try:
            with open(todo_path, "r", encoding="utf-8") as f:
                todos = json.load(f)
        except Exception:
            pass
    data["todos"] = todos
    
    # 4. Read config.json features
    config_path = os.path.join(deskpat_src_dir, "config.json")
    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception:
            pass
    data["config"] = config_data
    
    # 5. Determine active theme (system / light / dark)
    theme_pref = config_data.get("theme", "system").lower()
    active_theme = "dark"
    
    if theme_pref == "light":
        active_theme = "light"
    elif theme_pref == "dark":
        active_theme = "dark"
    else:
        if os.name == "nt":
            try:
                import winreg
                reg_key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                apps_use_light_theme, _ = winreg.QueryValueEx(reg_key, "AppsUseLightTheme")
                winreg.CloseKey(reg_key)
                active_theme = "light" if apps_use_light_theme == 1 else "dark"
            except Exception:
                active_theme = "dark"
        else:
            active_theme = "dark"

            
    data["system"]["theme"] = active_theme
    
    try:
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"  {Style.RED}Error saving augmented data:{Style.RESET} {e}")

def main():
    # Ensure UTF-8 stdout encoding to support unicode block graphics on Windows console
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
            
    # Intercept todo subcommand
    if len(sys.argv) > 1 and sys.argv[1].lower() == "todo":
        changed = handle_todo_cli(sys.argv[2:])
        if not changed:
            sys.exit(0)
        # Fall through to regenerate wallpaper!
        print(f"\n  {Style.BOLD}Todo list changed. Regenerating wallpaper dashboard...{Style.RESET}\n")
        
    enable_vt_processing()
            
    # banner
    banner = f"""
  {Style.BOLD}{Style.CYN}██████╗ ███████╗███████╗██╗  ██╗██████╗  █████╗ ████████╗
  ██╔══██╗██╔════╝██╔════╝██║ ██╔╝██╔══██╗██╔══██╗╚══██╔══╝
  ██║  ██║█████╗  ███████╗█████╔╝ ██████╔╝███████║   ██║   
  ██║  ██║██╔══╝  ╚════██║██╔═██╗ ██╔═══╝ ██╔══██║   ██║   
  ██████╔╝███████╗███████║██║  ██╗██║     ██║  ██║   ██║   
  ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝   ╚═╝{Style.RESET}
  {Style.DIM}Wallpaper Generator & Screen Detection CLI{Style.RESET}
    """
    print(banner)
    
    # Parse args
    parser = argparse.ArgumentParser(description="DESKPAT: Dynamic Wallpaper Generator")
    parser.add_argument("--url", type=str, help="URL to fetch data from (JSON or text)")
    parser.add_argument("--script", type=str, help="Script filename in scripts/ to execute (e.g. sadhguru.js)")
    parser.add_argument("--template", type=str, default=None, help="Template folder name to render")
    parser.add_argument("--select", action="store_true", help="Prompt to select a template interactively")
    args, extra_args = parser.parse_known_args()
    
    # Ensure folder structure is intact
    deskpat_src_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(deskpat_src_dir, "templates")
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
        
    # Read config.json
    config_path = os.path.join(deskpat_src_dir, "config.json")

    config_data = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as cf:
                config_data = json.load(cf)
        except Exception as e:
            print(f"  {Style.YELLOW}Warning: Failed to load config.json: {e}{Style.RESET}")

    # Determine script to run
    script_to_run = args.script or config_data.get("default_script")
    
    # Determine template to use
    template = args.template
    if not template:
        template = config_data.get("default_template", "default")
        
    # Check dependencies
    check_python_dependencies()
    check_npm_dependencies()
    
    # Fetch data based on priority
    if args.url:
        fetch_and_save_data(args.url)
    elif script_to_run:
        success = run_custom_script(script_to_run, extra_args)
        if not success:
            print(f"  {Style.YELLOW}Live fetch failed. Writing deterministic default fallback payload.{Style.RESET}")
            ensure_default_data(force=True)
    else:
        ensure_default_data()
        
    # Augment payload context with local tasks and system variables
    augment_payload_data()
        
    # Interactively select template if requested
    if args.select:
        template = select_template()
        
    # Verify template exists
    template_html = os.path.join(templates_dir, template, "template.html")
    if not os.path.exists(template_html):
        print(f"  {Style.YELLOW}Warning:{Style.RESET} Selected template HTML '{template_html}' not found.")
        # Fallback to default
        template = "default"
        template_html = os.path.join(templates_dir, "default", "template.html")
        if not os.path.exists(template_html):
            print(f"  {Style.RED}Error:{Style.RESET} Default template not found. Creating a simple dummy template.")
            # Create a basic default template
            default_tpl_dir = os.path.join(templates_dir, "default")
            os.makedirs(default_tpl_dir, exist_ok=True)
            dummy_html = """<!DOCTYPE html>
<html>
<head>
<style>
  body {
    background: linear-gradient(135deg, #1e1e2f, #11111d);
    color: #00ffcc;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    margin: 0;
    height: 100vh;
    overflow: hidden;
  }
  h1 { font-size: 4rem; text-shadow: 0 0 20px rgba(0,255,204,0.4); margin-bottom: 10px; }
  p { font-size: 1.5rem; color: #a0a0c0; }
  .items { margin-top: 20px; list-style-type: square; color: #8888aa; font-size: 1.2rem; }
</style>
</head>
<body>
  <h1 id="title">DESKPAT</h1>
  <p id="quote">Waiting for data...</p>
  <ul id="items" class="items"></ul>
  <script>
    document.addEventListener('DOMContentLoaded', () => {
      const data = window.wallpaperData || {};
      document.getElementById('title').textContent = data.title || 'DESKPAT ACTIVE';
      document.getElementById('quote').textContent = data.quote || 'Ready to render';
      const itemsList = document.getElementById('items');
      if (data.items && Array.isArray(data.items)) {
        data.items.forEach(it => {
          const li = document.createElement('li');
          li.textContent = it;
          itemsList.appendChild(li);
        });
      }
    });
  </script>
</body>
</html>"""
            with open(template_html, "w", encoding="utf-8") as f:
                f.write(dummy_html)
                
    # Detect displays
    try:
        monitors = get_monitor_data()
    except Exception as e:
        print(f"  {Style.RED}Error detecting displays:{Style.RESET} {e}")
        sys.exit(1)
        
    if not monitors:
        print(f"  {Style.RED}Error:{Style.RESET} No displays found.")
        sys.exit(1)
        
    # Render layout mapping & table
    render_ascii_layout(monitors)
    render_table(monitors)
    
    # ── Render Screens via Puppeteer ────────────────────────
    temp_images = []
    render_js_path = os.path.join(deskpat_src_dir, "render.js")
    data_json_path = os.path.join(deskpat_src_dir, "data.json")
    
    print(f"  {Style.BOLD}Rendering templates for displays using Puppeteer...{Style.RESET}")
    for idx, m in enumerate(monitors):
        img_out = os.path.join(deskpat_src_dir, f"temp_screen_{idx}.png")
        temp_images.append(img_out)
        
        cmd = [
            "node", render_js_path,
            "--template", template_html,
            "--width", str(m['width']),
            "--height", str(m['height']),
            "--output", img_out,
            "--data", data_json_path
        ]
        
        print(f"    - Render screen {idx+1} ({m['width']}x{m['height']}) -> {os.path.basename(img_out)}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as err:
            print(f"  {Style.RED}Failed to render display screen {idx+1}:{Style.RESET} {err}")
            sys.exit(1)
            
    # ── Stitch Screens via Pillow (Python) ──────────────────
    print(f"\n  {Style.BOLD}Stitching wallpapers into virtual desktop canvas...{Style.RESET}")
    
    # Find total virtual bounds
    min_x = min(m['rect'][0] for m in monitors)
    max_x = max(m['rect'][2] for m in monitors)
    min_y = min(m['rect'][1] for m in monitors)
    max_y = max(m['rect'][3] for m in monitors)
    
    virtual_width = max_x - min_x
    virtual_height = max_y - min_y
    
    print(f"    - Virtual Desktop Size: {virtual_width}x{virtual_height} (offsets X: [{min_x} to {max_x}], Y: [{min_y} to {max_y}])")
    
    try:
        from PIL import Image
        
        # Create virtual canvas filled with black background
        canvas = Image.new('RGB', (virtual_width, virtual_height), (0, 0, 0))
        
        for idx, m in enumerate(monitors):
            img_path = temp_images[idx]
            if os.path.exists(img_path):
                img = Image.open(img_path)
                
                # Calculate relative offset
                offset_x = m['rect'][0] - min_x
                offset_y = m['rect'][1] - min_y
                
                print(f"    - Paste screen {idx+1} at grid offset X:{offset_x}, Y:{offset_y}")
                canvas.paste(img, (offset_x, offset_y))
                
        wallpaper_out = os.path.join(deskpat_src_dir, "wallpaper.png")
        canvas.save(wallpaper_out)
        print(f"  {Style.GREEN}Wallpaper saved successfully to {wallpaper_out}{Style.RESET}")
        
    except Exception as e:
        print(f"  {Style.RED}Error combining wallpapers:{Style.RESET} {e}")
        sys.exit(1)
    finally:
        # Clean up temporary screenshots
        for img_path in temp_images:
            if os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception:
                    pass
                    
    # ── Apply Spanned Wallpaper ────────────────────────────
    print(f"  {Style.BOLD}Applying wallpaper style & setting desktop background...{Style.RESET}")
    set_wallpaper_style_span()
    
    abs_wallpaper_path = os.path.abspath(wallpaper_out)
    
    if os.name == "nt":
        try:
            import ctypes
            SPI_SETDESKWALLPAPER = 20
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            
            result = ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER,
                0,
                abs_wallpaper_path,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            
            if result:
                print(f"  {Style.GREEN}Success! Spanned wallpaper updated.{Style.RESET}")
            else:
                print(f"  {Style.RED}Warning:{Style.RESET} SystemParametersInfoW returned failure.")
        except Exception as e:
            print(f"  {Style.RED}Failed to update system wallpaper:{Style.RESET} {e}")
            
    elif sys.platform == "darwin":
        try:
            script = f'tell application "Finder" to set desktop picture to POSIX file "{abs_wallpaper_path}"'
            subprocess.run(["osascript", "-e", script], check=True)
            print(f"  {Style.GREEN}Success! Desktop wallpaper updated.{Style.RESET}")
        except Exception as e:
            print(f"  {Style.RED}Failed to update system wallpaper:{Style.RESET} {e}")
            
    else:
        try:
            # Linux GNOME fallback
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{abs_wallpaper_path}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", f"file://{abs_wallpaper_path}"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print(f"  {Style.GREEN}Success! Desktop wallpaper updated.{Style.RESET}")
        except Exception:
            print(f"  {Style.YELLOW}Desktop wallpaper updated locally at: {abs_wallpaper_path}{Style.RESET}")

        
if __name__ == "__main__":
    main()
