async function main() {
    try {
        const url = "https://iso-facade.sadhguru.org/content/fetchcsr/content?format=json&sitesection=wisdom&slug=wisdom&lang=&topic=&start=0&limit=12&contentType=quotes&sortby=newest";
        const response = await fetch(url, {
            headers: {
                "accept": "application/json"
            },
            method: "GET"
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const firstCard = data.posts?.cards?.[0];

        if (!firstCard) {
            throw new Error("No quotes found in response.");
        }

        // Standardize output JSON structure
        const result = {
            title: firstCard.title || "Daily Wisdom",
            quote: firstCard.summary || "",
            author: "Sadhguru",
            image_url: firstCard.cardImage?.url || "",
            items: [
                `Section: Wisdom`,
                `Alias: ${firstCard.urlAlias || 'n/a'}`,
                `Date: ${new Date(firstCard.createdAt).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`
            ]
        };

        // Write standardized JSON to stdout
        console.log(JSON.stringify(result, null, 2));
    } catch (err) {
        console.error("Error running sadhguru.js fetch script:", err);
        
        // Output fallback data
        const fallback = {
            title: "Sadhguru Wisdom",
            quote: "Devotion does not mean worship. Devotion means becoming devoid of yourself.",
            author: "Sadhguru",
            items: [
                "Fallback offline status",
                "Failed to fetch live Quote"
            ]
        };
        console.log(JSON.stringify(fallback, null, 2));
        process.exit(1);
    }
}

main();
