/**
 * DESKPAT Custom Script Template (Node.js)
 * 
 * You can write dynamic JS scripts to pull data from any API, database, or local system.
 * The script must log the standardized JSON payload to standard output (console.log).
 * 
 * Standard Payload Format:
 * {
 *   "title": "Title shown on dashboard",
 *   "quote": "Main text, quote, or status message",
 *   "author": "Author or subtitle",
 *   "image_url": "Optional web URL of background image to render",
 *   "items": [
 *      "Item list shown as bullet points",
 *      "Additional details here"
 *   ]
 * }
 */
async function main() {
    try {
        // Example: Fetch data from a public API
        // const response = await fetch("https://api.example.com/data");
        // const data = await response.json();

        // 1. Process your custom data structures
        const payload = {
            title: "CUSTOM SERVICE STATUS",
            quote: "All systems operational. Main cluster running without alerts.",
            author: "System Monitor",
            image_url: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe", // abstract artwork
            items: [
                "CPU Usage: 14%",
                "Memory Free: 8.2 GB",
                "Load Average: 0.12"
            ]
        };

        // 2. Output to stdout
        console.log(JSON.stringify(payload, null, 2));
    } catch (err) {
        console.error("Custom script error:", err);
        process.exit(1);
    }
}

main();
