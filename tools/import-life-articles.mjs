import { readFile, writeFile } from "node:fs/promises";

const csvPath = "src/data/cnfcd-life-index.csv";
const outputPath = "src/data/life-articles.json";

const excludedUrlParts = [
  "/en/",
  "privacy",
  "cost",
  "worth-it",
  "pricing",
  "product",
  "joy123",
  "30-day",
  "action-plan",
  "breakthrough-plan",
  "story",
  "success",
  "client-case",
  "founder",
  "advisor",
  "consultant",
  "consulting",
  "business",
  "opportunity",
  "joining",
  "direct-sales",
  "mlm",
  "economic",
  "roi",
  "award",
  "trademark",
  "globally-recognized",
  "scientific-evidence-journal-validation",
  "science-proof",
  "certified",
  "health-plan",
  "internationally-certified",
  "plan-pricing",
  "ai-weight-loss-program",
  "resetwith-brand",
  "brand-overview",
  "author/",
  "category/",
  "tag/",
];

const salesPatterns = [
  /立即|馬上|現在就|限時|優惠|購買|下單|加入|報名|預約|諮詢|顧問|方案|課程|服務|陪伴|LINE|Line|line|表單|填寫|聯絡我們|免費諮詢/,
  /ResetWith.*(顧問|服務|方案|陪伴|官方|加入)/,
  /CNFCD.*(產品|方案|費用|顧問|服務|加入|購買)/,
  /點擊|私訊|留言|洽詢|預約|客服|官方網站/,
];

const cautionReplacements = [
  [/逆轉/g, "改善方向"],
  [/治癒/g, "改善"],
  [/根治/g, "處理"],
  [/保證/g, "可能"],
  [/必瘦/g, "可能改善"],
  [/唯一解方/g, "可觀察的方向"],
];

function parseCsv(text) {
  const [headerLine, ...lines] = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/);
  const headers = parseCsvLine(headerLine);

  return lines.map((line) => {
    const values = parseCsvLine(line);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function parseCsvLine(line) {
  const cells = [];
  let cell = "";
  let inQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const char = line[index];
    const next = line[index + 1];

    if (char === '"' && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      cells.push(cell);
      cell = "";
    } else {
      cell += char;
    }
  }

  cells.push(cell);
  return cells;
}

function selectedRows(rows) {
  const seen = new Set();
  return rows
    .filter((row) => row.class === "indexable_200")
    .filter((row) => row.http_status === "200")
    .filter((row) => row.canonical.startsWith("https://cnfcd.life/"))
    .filter((row) => !excludedUrlParts.some((part) => row.canonical.includes(part)))
    .filter((row) => {
      if (seen.has(row.canonical)) return false;
      seen.add(row.canonical);
      return true;
    });
}

function slugFromUrl(url) {
  return new URL(url).pathname.replace(/^\/|\/$/g, "");
}

async function fetchArticle(row) {
  const originalSlug = slugFromUrl(row.canonical);
  const apiPayload = await fetchRestPayload(originalSlug);
  const html = apiPayload?.content?.rendered ?? (await fetchHtml(row.canonical));
  const title = cleanText(apiPayload?.title?.rendered ?? titleFromHtml(html) ?? originalSlug);
  const blocks = cleanBlocks(extractBlocks(html));
  const summary = summarize(blocks);
  const keyTakeaways = takeaways(blocks, title);

  return {
    slug: `life-${originalSlug}`,
    originalSlug,
    title,
    originalUrl: row.canonical,
    importedAt: new Date().toISOString(),
    summary,
    keyTakeaways,
    visual: visualFor(originalSlug, title),
    blocks,
  };
}

async function fetchRestPayload(slug) {
  const endpoints = [
    `https://cnfcd.life/wp-json/wp/v2/posts?slug=${encodeURIComponent(slug)}&_fields=slug,title,content,link`,
    `https://cnfcd.life/wp-json/wp/v2/pages?slug=${encodeURIComponent(slug)}&_fields=slug,title,content,link`,
  ];

  for (const endpoint of endpoints) {
    try {
      const response = await fetch(endpoint);
      if (!response.ok) continue;
      const payload = await response.json();
      if (Array.isArray(payload) && payload[0]?.content?.rendered) return payload[0];
    } catch {
      // Fall through to the next source.
    }
  }

  return undefined;
}

async function fetchHtml(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${url}: ${response.status}`);
  }
  return response.text();
}

function titleFromHtml(html) {
  return html.match(/<title[^>]*>([\s\S]*?)<\/title>/i)?.[1];
}

function extractBlocks(html) {
  const contentHtml = pickContentHtml(html);
  const blocks = [];
  const pattern = /<(h2|h3|h4|p|li|blockquote)[^>]*>([\s\S]*?)<\/\1>/gi;
  let currentList = [];

  for (const match of contentHtml.matchAll(pattern)) {
    const tag = match[1].toLowerCase();
    const text = cleanText(match[2]);

    if (!text || shouldSkip(text)) continue;

    if (tag === "li") {
      currentList.push(text);
      continue;
    }

    if (currentList.length) {
      blocks.push({ type: "list", items: currentList.splice(0, 8) });
      currentList = [];
    }

    if (tag.startsWith("h")) {
      blocks.push({ type: "heading", text });
    } else if (tag === "blockquote") {
      blocks.push({ type: "quote", text });
    } else {
      blocks.push({ type: "paragraph", text });
    }
  }

  if (currentList.length) blocks.push({ type: "list", items: currentList.splice(0, 8) });

  return blocks;
}

function pickContentHtml(html) {
  const postContent = html.match(
    /elementor-widget-theme-post-content[\s\S]*?<div[^>]*class="[^"]*elementor-widget-container[^"]*"[^>]*>([\s\S]*?)<\/div>\s*<\/div>/i,
  )?.[1];

  if (postContent) return postContent;

  const wpMain = html.match(/<main[\s\S]*?<\/main>/i)?.[0];
  return wpMain ?? html;
}

function cleanBlocks(blocks) {
  const cleaned = [];
  const seen = new Set();

  for (const block of blocks) {
    if (block.type === "list") {
      const items = block.items
        .map(cleanText)
        .filter((item) => item.length >= 6)
        .filter((item) => !shouldSkip(item));

      if (items.length >= 2) cleaned.push({ type: "list", items: unique(items).slice(0, 7) });
      continue;
    }

    const text = cleanText(block.text);
    if (!text || shouldSkip(text) || seen.has(text)) continue;

    seen.add(text);
    cleaned.push({ ...block, text });
  }

  return cleaned.slice(0, 80);
}

function shouldSkip(text) {
  if (text.length < 5) return true;
  if (/^(首頁|文章目錄|延伸閱讀|相關文章|分享|目錄|結論)$/.test(text)) return true;
  if (salesPatterns.some((pattern) => pattern.test(text))) return true;
  if (/^\d+$/.test(text)) return true;
  return false;
}

function cleanText(value) {
  let text = decodeHtml(
    String(value)
      .replace(/<script[\s\S]*?<\/script>/gi, "")
      .replace(/<style[\s\S]*?<\/style>/gi, "")
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/\[[^\]]+\]/g, " ")
      .replace(/\s+/g, " ")
      .trim(),
  );

  cautionReplacements.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });

  return text
    .replace(/CNFCD®/g, "CNFCD")
    .replace(/ResetWith\s*/g, "")
    .replace(/｜.*官方網站/g, "")
    .trim();
}

function decodeHtml(value) {
  return value
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'")
    .replace(/&#8211;/g, "–")
    .replace(/&#8217;/g, "’")
    .replace(/&#8220;/g, "“")
    .replace(/&#8221;/g, "”")
    .replace(/&#8230;/g, "…")
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(Number.parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, code) => String.fromCodePoint(Number.parseInt(code, 10)));
}

function summarize(blocks) {
  return blocks
    .filter((block) => block.type === "paragraph")
    .map((block) => block.text)
    .filter((text) => text.length >= 30)
    .slice(0, 2);
}

function takeaways(blocks, title) {
  const candidates = [
    ...blocks.filter((block) => block.type === "heading").map((block) => block.text),
    ...blocks.filter((block) => block.type === "paragraph").map((block) => truncate(block.text, 72)),
  ];

  return unique(candidates)
    .filter((text) => text !== title)
    .filter((text) => text.length >= 10)
    .slice(0, 4);
}

function visualFor(slug, title) {
  if (hasAny(slug, ["blood-sugar", "insulin", "glucose", "hba1c", "gi-food"])) {
    return {
      type: "flow",
      title: "血糖與胰島素路徑",
      nodes: ["食物結構", "血糖波動", "胰島素反應", "飢餓與精神", "下一餐選擇"],
    };
  }

  if (hasAny(slug, ["gut", "microbiome", "fiber", "scfa", "butyrate", "inflammation"])) {
    return {
      type: "mindmap",
      title: "腸道訊號地圖",
      center: "腸道狀態",
      nodes: ["菌相", "膳食纖維", "短鏈脂肪酸", "發炎背景", "食慾訊號"],
    };
  }

  if (hasAny(slug, ["sleep", "stress", "cortisol", "circadian", "breathing"])) {
    return {
      type: "cycle",
      title: "睡眠壓力循環",
      nodes: ["睡眠不足", "壓力上升", "食慾變動", "血糖更震盪", "恢復變慢"],
    };
  }

  if (hasAny(slug, ["fatty-liver", "diabetes", "blood-pressure", "gout", "ckd", "pcos", "heart", "arthritis"])) {
    return {
      type: "risk",
      title: "代謝風險觀察框架",
      nodes: ["腰圍", "血糖", "血脂", "血壓", "肝腎指標", "睡眠壓力"],
    };
  }

  if (hasAny(slug, ["eating-out", "breakfast", "bubble-tea", "convenience", "hotpot", "supermarket"])) {
    return {
      type: "decision",
      title: "外食選擇順序",
      nodes: ["先看蛋白質", "再看蔬菜纖維", "調整澱粉份量", "避開含糖飲", "觀察餐後狀態"],
    };
  }

  if (hasAny(slug, ["myth", "glp1", "exercise", "calorie", "eating-less"])) {
    return {
      type: "compare",
      title: "常見說法與代謝視角",
      nodes: ["單點解法", "身體訊號", "生活節奏", "可持續調整"],
    };
  }

  return {
    type: "system",
    title: title.includes("CNFCD") ? "CNFCD 框架圖" : "代謝修復系統圖",
    nodes: ["飲食結構", "血糖穩定", "胰島素敏感度", "睡眠壓力", "代謝回穩"],
  };
}

function hasAny(value, keywords) {
  return keywords.some((keyword) => value.includes(keyword));
}

function unique(values) {
  return [...new Set(values)];
}

function truncate(text, length) {
  if (text.length <= length) return text;
  return `${text.slice(0, length)}…`;
}

const csv = await readFile(csvPath, "utf-8");
const rows = selectedRows(parseCsv(csv));
const output = {};

for (const [index, row] of rows.entries()) {
  try {
    const article = await fetchArticle(row);
    output[article.slug] = article;
    console.log(`[${index + 1}/${rows.length}] imported ${article.slug}`);
  } catch (error) {
    console.warn(`[${index + 1}/${rows.length}] skipped ${row.canonical}: ${error.message}`);
  }
}

await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`);
console.log(`Wrote ${Object.keys(output).length} cleaned articles to ${outputPath}`);
