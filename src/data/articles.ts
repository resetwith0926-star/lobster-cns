export type ArticleCategory =
  | "新手必讀"
  | "代謝修復"
  | "胰島素與血糖"
  | "腸道與發炎"
  | "睡眠與壓力"
  | "外食族指南"
  | "常見迷思"
  | "案例與研究整理";

export interface ArticleEntry {
  title: string;
  description: string;
  category: ArticleCategory;
  url: string;
  tags: string[];
  recommendedOrder: number;
}

export interface ArticleCategoryMeta {
  slug: string;
  title: ArticleCategory;
  description: string;
}

export const articleCategories: ArticleCategoryMeta[] = [
  {
    slug: "beginner",
    title: "新手必讀",
    description: "先用最少的篇幅，建立對 CNFCD 與代謝節奏的基本理解。",
  },
  {
    slug: "metabolic-repair",
    title: "代謝修復",
    description: "聚焦代謝適應、停滯感與身體如何慢慢回到穩定狀態。",
  },
  {
    slug: "insulin-blood-sugar",
    title: "胰島素與血糖",
    description: "整理血糖波動、肝醣、胰島素敏感度與飢餓感之間的關係。",
  },
  {
    slug: "gut-inflammation",
    title: "腸道與發炎",
    description: "從腸道環境、發炎與食慾訊號理解日常狀態。",
  },
  {
    slug: "sleep-stress",
    title: "睡眠與壓力",
    description: "理解睡眠節律、壓力荷爾蒙與脂肪動員的交互作用。",
  },
  {
    slug: "eating-out",
    title: "外食族指南",
    description: "把觀念轉成可執行的外食選擇與生活節奏策略。",
  },
  {
    slug: "myths",
    title: "常見迷思",
    description: "整理常見誤解，幫助讀者拆解熱量、節食與速效說法。",
  },
  {
    slug: "cases-research",
    title: "案例與研究整理",
    description: "放置案例、觀察與研究摘要，作為延伸閱讀入口。",
  },
];

export const articles: ArticleEntry[] = [
  {
    title: "CNFCD 入門：先理解身體為什麼會卡住",
    description: "TODO：補上真實入門文章連結與摘要，作為新讀者的第一篇導讀。",
    category: "新手必讀",
    url: "https://cnfcd.life/",
    tags: ["入門", "代謝", "閱讀路徑"],
    recommendedOrder: 1,
  },
  {
    title: "代謝修復在談什麼？",
    description: "TODO：補上真實文章，說明代謝修復不是速效，而是恢復穩定節奏。",
    category: "代謝修復",
    url: "https://cnfcd.life/",
    tags: ["代謝修復", "停滯", "節奏"],
    recommendedOrder: 2,
  },
  {
    title: "血糖起伏與飢餓感的關係",
    description: "TODO：補上真實文章，整理血糖波動如何影響精神與飲食選擇。",
    category: "胰島素與血糖",
    url: "https://cnfcd.life/",
    tags: ["血糖", "飢餓", "胰島素"],
    recommendedOrder: 3,
  },
  {
    title: "腸道狀態與食慾訊號",
    description: "TODO：補上真實文章，整理腸道、發炎與日常不適感的連結。",
    category: "腸道與發炎",
    url: "https://cnfcd.life/",
    tags: ["腸道", "發炎", "食慾"],
    recommendedOrder: 4,
  },
  {
    title: "睡不好時，為什麼更難穩定飲食？",
    description: "TODO：補上真實文章，說明睡眠與壓力如何影響節律與脂肪動員。",
    category: "睡眠與壓力",
    url: "https://cnfcd.life/",
    tags: ["睡眠", "壓力", "節律"],
    recommendedOrder: 5,
  },
  {
    title: "外食族的穩定吃法",
    description: "TODO：補上真實文章，整理日常外食下的簡單選擇原則。",
    category: "外食族指南",
    url: "https://cnfcd.life/",
    tags: ["外食", "實作", "飲食結構"],
    recommendedOrder: 6,
  },
  {
    title: "少吃就一定會瘦嗎？",
    description: "TODO：補上真實文章，拆解『只要熱量赤字就夠』的常見迷思。",
    category: "常見迷思",
    url: "https://cnfcd.life/",
    tags: ["迷思", "熱量", "體重管理"],
    recommendedOrder: 7,
  },
  {
    title: "案例與研究閱讀索引",
    description: "TODO：補上真實文章或研究整理頁，集中放置延伸案例與資料來源。",
    category: "案例與研究整理",
    url: "https://cnfcd.life/",
    tags: ["案例", "研究", "索引"],
    recommendedOrder: 8,
  },
];

export const categorySlugMap = Object.fromEntries(
  articleCategories.map((category) => [category.title, category.slug]),
) as Record<ArticleCategory, string>;
