const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);

let templatePath = '';
let width = 1920;
let height = 1080;
let outputPath = '';
let dataPath = '';

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--template') {
        templatePath = args[++i];
    } else if (args[i] === '--width') {
        width = parseInt(args[++i], 10);
    } else if (args[i] === '--height') {
        height = parseInt(args[++i], 10);
    } else if (args[i] === '--output') {
        outputPath = args[++i];
    } else if (args[i] === '--data') {
        dataPath = args[++i];
    }
}

if (!templatePath || !outputPath) {
    console.error("Usage: node render.js --template <html_path> --width <w> --height <h> --output <png_path> [--data <json_path>]");
    process.exit(1);
}

(async () => {
    // Launch puppeteer
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        
        // Set exact viewport size corresponding to the monitor resolution
        await page.setViewport({ width, height, deviceScaleFactor: 1 });

        // Load data if provided
        let dataJsonStr = '{}';
        if (dataPath && fs.existsSync(dataPath)) {
            try {
                dataJsonStr = fs.readFileSync(dataPath, 'utf8');
            } catch (err) {
                console.error("Error reading data file:", err);
            }
        }

        // Inject data to window.wallpaperData before page loads
        await page.evaluateOnNewDocument((dataStr) => {
            try {
                window.wallpaperData = JSON.parse(dataStr);
            } catch (e) {
                window.wallpaperData = {};
            }
        }, dataJsonStr);

        // Convert file path to absolute URL
        const absolutePath = path.resolve(templatePath).replace(/\\/g, '/');
        const fileUrl = `file:///${absolutePath}`;

        // Load template html
        await page.goto(fileUrl, { waitUntil: 'networkidle0' });

        // Wait a small moment for CSS transitions, image loads, or canvas renders to complete
        await new Promise(resolve => setTimeout(resolve, 600));

        // Take a screenshot of the viewport
        await page.screenshot({
            path: outputPath,
            clip: { x: 0, y: 0, width, height }
        });
        
        console.log(`Rendered screen screenshot to ${outputPath} (${width}x${height})`);
    } catch (err) {
        console.error("Puppeteer capture error:", err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
