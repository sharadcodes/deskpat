# DESKPAT Setup & User Guide

Welcome to **DESKPAT**, a modular, spanned multi-monitor wallpaper generator and system information dashboard. This guide explains the project structure, how to configure the engine, manage your tasks list, and write custom templates, sensors, or fetchers.

---

## 📂 Project Structure

All implementation files are stored in `deskpat_src/` to keep your root directory clean:

```text
cli-tools/
│
├── deskpat.bat / deskpat.ps1  # Root wrappers (launchers)
└── deskpat_src/
    ├── README.md              # This guide
    ├── deskpat.py             # Python orchestrator & monitor engine
    ├── sensors.py             # System telemetry sensor plugins
    ├── render.js              # Puppeteer HTML screenshot render engine
    ├── config.json            # Theme & default configurations
    ├── todo.json              # Local tasks list database
    ├── data.json              # Standardized API payload context
    ├── scripts/               # Custom fetchers folder
    │   ├── sadhguru.js        # Dynamic quotes & feeds fetcher
    │   └── template.js        # Fetcher boilerplate template
    └── templates/             # HTML layout templates
        ├── default/           # Glassmorphic full-stats dashboard
        └── minimal/           # Joyful split layout (Checklist & Quotes)
```

---

## ⚡ Quick Start & Setup

### 1. Prerequisites
Ensure you have the following installed on your computer:
* **Python 3.x** (with `pip` in your system `PATH`)
* **Node.js & npm** (with `node` in your system `PATH`)

### 2. Dependency Initialization
When you run the tool for the first time, it automatically installs any missing dependencies:
* **Python**: `Pillow` (PIL) library
* **Node.js**: `puppeteer` (headless compiler)

### 3. Running the Engine
To fetch the latest data, build the layout canvas, and set the Span desktop wallpaper, simply run the launcher for your shell:

```bash
# Using Batch (on compatible shells)
.\deskpat.bat

# Using PowerShell
.\deskpat.ps1

# Directly via Python
python deskpat_src/deskpat.py
```

---

## 🛠️ CLI Options

The orchestrator CLI accepts arguments to override default settings:

* `--script <filename.js|py|ps1>`: Run a custom data fetcher script from `scripts/` (e.g. `--script sadhguru.js`).
* `--template <folder>`: Render a specific layout template (e.g. `--template default`).
* `--url <api_url>`: Fetch raw text or JSON data directly from a web URL (bypassing custom scripts).
* `--select`: Interactively list and pick an available template in the console.
* **Argument Passthrough**: Any unrecognized flags are automatically forwarded straight to your custom script (e.g. `deskpat --script my_script.py --city "Seattle" --units "metric"`).

---

## 📋 Local Todo Subcommand

DESKPAT includes a built-in command-line task checklist manager. Running these commands will modify `todo.json`, and the changes will render on your desktop checklist instantly on the next background update:

* **List active tasks**: `deskpat todo list`
* **Add a new task**: `deskpat todo add "Complete developer documentation"`
* **Toggle task completion**: `deskpat todo done <index_number>` (e.g., `deskpat todo done 2`)
* **Delete a task**: `deskpat todo remove <index_number>`
* **Clear all tasks**: `deskpat todo clear`

---

## 🔌 Extensibility & Customization

### 1. Writing Custom Data Fetchers
You can drop scripts into `deskpat_src/scripts/`. Fetcher scripts can be written in **Node.js (`.js`)**, **Python (`.py`)**, **PowerShell (`.ps1`)**, or **Shell (`.sh`/`.bat`)**.
* **Requirement**: The script must output a clean JSON object to `stdout`.
* The orchestrator automatically executes your script, parses its output, and saves it into `data.json`.

### 2. Creating New Visual Layouts
Templates are stored under `deskpat_src/templates/`. To build your own:
1. Create a folder (e.g., `templates/custom-dashboard/`).
2. Add a `template.html` and `style.css`.
3. In `template.html`, read the global context `window.wallpaperData` in JavaScript to populate your fields.
4. Set it as default in `config.json` or call `deskpat --template custom-dashboard`.

### 3. Adding New Modular OS/System Sensors
OS-level metrics are queried via [sensors.py](file:///c:/SOFTWARES/cli-tools/deskpat_src/sensors.py). To add a new system stat (e.g., free disk space, CPU temperature, or battery level):
1. Open `sensors.py` and write a Python function.
2. Register it using the `@sensor("metric_name")` decorator.

```python
@sensor("disk_free_gb")
def get_disk_free():
    import shutil
    total, used, free = shutil.disk_usage("/")
    return round(free / (1024**3), 1)
```

This variable automatically loads into `data.json` and becomes instantly available inside your HTML templates in JavaScript at `window.wallpaperData.system.disk_free_gb`!
