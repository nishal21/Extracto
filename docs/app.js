/* ═══════════════════════════════════════════════════════
   Extracto — Website Interactivity
   Terminal animation, playground demo, scroll effects
   ═══════════════════════════════════════════════════════ */

// ── Nav scroll effect ────────────────────────────────
const nav = document.getElementById('nav');
window.addEventListener('scroll', () => {
    nav.classList.toggle('scrolled', window.scrollY > 40);
});

// ── Mobile nav toggle ────────────────────────────────
document.getElementById('navToggle').addEventListener('click', () => {
    document.getElementById('navLinks').classList.toggle('open');
});

// ── Terminal typing animation ────────────────────────
const commands = [
    {
        cmd: 'python main.py "https://books.toscrape.com/" "Extract all book titles and prices"',
        output: [
            '',
            '<span class="success">   🕷️  Extracto v3.0</span>',
            '<span class="output">   ─────────────────────────────</span>',
            '<span class="output">   URL:      books.toscrape.com</span>',
            '<span class="output">   Provider: mistral (mistral-small-latest)</span>',
            '<span class="output">   Format:   json</span>',
            '',
            '<span class="output">   ⠋ Rendering page...</span>',
            '<span class="output">   ⠙ Extracting with AI...</span>',
            '',
            '<span class="success">   ✓ Done! 20 items extracted in 3.2s</span>',
            '<span class="success">   ✓ Saved to output/scraped_data.json</span>',
        ]
    },
    {
        cmd: 'python main.py --batch urls.txt "Get all prices" -f csv --cache --screenshots',
        output: [
            '',
            '<span class="success">   🕷️  Extracto v3.0</span>',
            '<span class="output">   ─────────────────────────────</span>',
            '<span class="output">   Batch mode: 15 URLs loaded</span>',
            '<span class="output">   Cache: enabled | Screenshots: on</span>',
            '',
            '<span class="output">   [1/15] ✓ amazon.com/product/123</span>',
            '<span class="output">   [2/15] ✓ amazon.com/product/456</span>',
            '<span class="output">   [3/15] ✓ amazon.com/product/789</span>',
            '<span class="output">   ...</span>',
            '',
            '<span class="success">   ✓ 15/15 pages scraped in 28.4s</span>',
            '<span class="success">   ✓ Saved to output/scraped_data.csv</span>',
        ]
    },
    {
        cmd: 'python main.py serve --port 8080',
        output: [
            '',
            '<span class="success">   🚀 Extracto API starting on http://0.0.0.0:8080</span>',
            '<span class="output">      Docs: http://0.0.0.0:8080/docs</span>',
            '',
            '<span class="output">   INFO:     Uvicorn running on http://0.0.0.0:8080</span>',
            '<span class="output">   INFO:     Press CTRL+C to quit</span>',
        ]
    }
];

let currentCmd = 0;

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function typeCommand(text, el) {
    el.textContent = '';
    for (let i = 0; i < text.length; i++) {
        el.textContent += text[i];
        await sleep(18 + Math.random() * 25);
    }
}

async function showOutput(lines, container) {
    for (const line of lines) {
        const div = document.createElement('div');
        div.innerHTML = line || '&nbsp;';
        container.appendChild(div);
        await sleep(120);
    }
}

async function runTerminal() {
    const line1 = document.getElementById('termLine1');
    const output = document.getElementById('termOutput');

    while (true) {
        const { cmd, output: lines } = commands[currentCmd];

        // clear
        line1.textContent = '';
        output.innerHTML = '';

        // type the command
        await sleep(800);
        await typeCommand(cmd, line1);
        await sleep(400);

        // show output
        await showOutput(lines, output);

        // wait then loop
        await sleep(4000);
        currentCmd = (currentCmd + 1) % commands.length;
    }
}

runTerminal();


// ── Playground demo data ─────────────────────────────
const DEMO_DATA = {
    books: {
        prompt: "Extract all book titles and their prices",
        json: [
            { title: "A Light in the Attic", price: 51.77, rating: 3, in_stock: true },
            { title: "Tipping the Velvet", price: 53.74, rating: 1, in_stock: true },
            { title: "Soumission", price: 50.10, rating: 1, in_stock: true },
            { title: "Sharp Objects", price: 47.82, rating: 4, in_stock: true },
            { title: "Sapiens", price: 54.23, rating: 5, in_stock: true },
            { title: "The Requiem Red", price: 22.65, rating: 1, in_stock: true },
            { title: "The Dirty Little Secrets", price: 33.34, rating: 4, in_stock: true },
            { title: "The Coming Woman", price: 17.93, rating: 3, in_stock: true },
            { title: "The Boys in the Boat", price: 22.60, rating: 4, in_stock: true },
            { title: "The Black Maria", price: 52.15, rating: 1, in_stock: true },
        ]
    },
    quotes: {
        prompt: "Extract all quotes with their authors and tags",
        json: [
            { quote: "The world as we have created it is a process of our thinking.", author: "Albert Einstein", tags: ["change", "deep-thoughts", "thinking", "world"] },
            { quote: "It is our choices, Harry, that show what we truly are.", author: "J.K. Rowling", tags: ["abilities", "choices"] },
            { quote: "There are only two ways to live your life.", author: "Albert Einstein", tags: ["inspirational", "life", "live", "miracle"] },
            { quote: "The person, be it gentleman or lady, who has not pleasure in a good novel, must be intolerably stupid.", author: "Jane Austen", tags: ["aliteracy", "books", "classic"] },
            { quote: "Imperfection is beauty, madness is genius.", author: "Marilyn Monroe", tags: ["be-yourself", "inspirational"] },
            { quote: "Try not to become a man of success. Rather become a man of value.", author: "Albert Einstein", tags: ["adulthood", "success", "value"] },
        ]
    },
    news: {
        prompt: "Extract all post titles and their point counts",
        json: [
            { title: "Show HN: I built a web scraper with AI", points: 342, comments: 128, url: "https://example.com/scraper" },
            { title: "The State of LLMs in 2026", points: 289, comments: 95, url: "https://example.com/llms" },
            { title: "PostgreSQL 18 Released", points: 567, comments: 201, url: "https://postgresql.org/18" },
            { title: "Why Rust is Taking Over Systems Programming", points: 198, comments: 143, url: "https://example.com/rust" },
            { title: "The Future of Web Scraping", points: 156, comments: 67, url: "https://example.com/scraping" },
            { title: "GPT-5 Benchmarks Are In", points: 891, comments: 456, url: "https://example.com/gpt5" },
        ]
    }
};

const demoUrlEl = document.getElementById('demoUrl');
const demoPromptEl = document.getElementById('demoPrompt');
const demoFormatEl = document.getElementById('demoFormat');
const demoOutputEl = document.getElementById('demoOutput');
const demoRunEl = document.getElementById('demoRun');
const statusDotEl = document.getElementById('statusDot');
const statusTextEl = document.getElementById('statusText');
const demoTimerEl = document.getElementById('demoTimer');

// update prompt when URL changes
demoUrlEl.addEventListener('change', () => {
    const key = demoUrlEl.value;
    demoPromptEl.value = DEMO_DATA[key].prompt;
});

function syntaxHighlight(json) {
    const str = JSON.stringify(json, null, 2);
    return str.replace(
        /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
        (match) => {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                cls = /:$/.test(match) ? 'json-key' : 'json-string';
            }
            return `<span class="${cls}">${match}</span>`;
        }
    );
}

function toCSV(data) {
    if (!data.length) return '';
    const headers = Object.keys(data[0]);
    const rows = data.map(row =>
        headers.map(h => {
            const v = row[h];
            return typeof v === 'string' ? `"${v}"` : Array.isArray(v) ? `"${v.join(', ')}"` : v;
        }).join(',')
    );
    return headers.join(',') + '\n' + rows.join('\n');
}

function toTable(data) {
    if (!data.length) return '';
    const headers = Object.keys(data[0]);
    const widths = headers.map(h =>
        Math.max(h.length, ...data.map(r => String(r[h]).length))
    );
    const pad = (s, w) => String(s).padEnd(w);
    const sep = widths.map(w => '─'.repeat(w)).join('─┼─');

    let out = headers.map((h, i) => pad(h.toUpperCase(), widths[i])).join(' │ ') + '\n';
    out += sep + '\n';
    out += data.map(row =>
        headers.map((h, i) => pad(row[h], widths[i])).join(' │ ')
    ).join('\n');
    return out;
}

demoRunEl.addEventListener('click', async () => {
    const key = demoUrlEl.value;
    const format = demoFormatEl.value;
    const data = DEMO_DATA[key].json;

    // running state
    demoRunEl.disabled = true;
    demoRunEl.textContent = '⏳ Scraping...';
    statusDotEl.className = 'status-dot running';
    statusTextEl.textContent = 'Rendering page...';
    demoOutputEl.innerHTML = '';

    let elapsed = 0;
    const timer = setInterval(() => {
        elapsed += 100;
        demoTimerEl.textContent = (elapsed / 1000).toFixed(1) + 's';
    }, 100);

    // simulate rendering
    await sleep(800);
    statusTextEl.textContent = 'Loading JavaScript...';
    await sleep(600);
    statusTextEl.textContent = 'Extracting with AI...';
    await sleep(1200);
    statusTextEl.textContent = 'Formatting output...';
    await sleep(400);

    clearInterval(timer);

    // format output
    let outputStr;
    if (format === 'csv') {
        outputStr = toCSV(data);
    } else if (format === 'table') {
        outputStr = toTable(data);
    } else {
        outputStr = syntaxHighlight(data);
    }

    // show result with success message
    const summary = `<span style="color:var(--cyan)">✓ ${data.length} items extracted in ${(elapsed / 1000).toFixed(1)}s</span>\n\n`;
    demoOutputEl.innerHTML = summary + outputStr;

    // reset state
    statusDotEl.className = 'status-dot ready';
    statusTextEl.textContent = `Done — ${data.length} items`;
    demoRunEl.disabled = false;
    demoRunEl.textContent = '🕷️ Run Extracto';
});


// ── Intersection Observer for fade-in ────────────────
const observer = new IntersectionObserver((entries) => {
    entries.forEach(e => {
        if (e.isIntersecting) {
            e.target.style.opacity = '1';
            e.target.style.transform = 'translateY(0)';
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .install-step, .provider-card').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(20px)';
    el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
    observer.observe(el);
});
