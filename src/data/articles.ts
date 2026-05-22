import { readFileSync } from "node:fs";

export type ArticleCategory =
  | "新手必讀"
  | "CNFCD 核心"
  | "代謝修復"
  | "胰島素與血糖"
  | "腸道與發炎"
  | "睡眠與壓力"
  | "外食族指南"
  | "疾病與代謝風險"
  | "常見迷思"
  | "案例與研究整理";

export type ArticleSource = "觀念短文" | "知識整理" | "原站文章";

export interface ArticleSection {
  heading: string;
  body: string[];
}

export interface ArticleContentBlock {
  type: "heading" | "paragraph" | "list" | "quote";
  text?: string;
  items?: string[];
}

export interface ArticleLink {
  label: string;
  href: string;
}

export interface ArticleVisual {
  type:
    | "flow"
    | "mindmap"
    | "cycle"
    | "risk"
    | "decision"
    | "compare"
    | "system";
  title: string;
  center?: string;
  nodes: string[];
}

export interface CleanArticleContent {
  slug: string;
  originalSlug: string;
  title: string;
  originalUrl: string;
  importedAt: string;
  summary: string[];
  keyTakeaways: string[];
  visual: ArticleVisual;
  blocks: ArticleContentBlock[];
  related?: ArticleLink[];
  references?: ArticleLink[];
}

export interface ArticleEntry {
  slug: string;
  title: string;
  description: string;
  category: ArticleCategory;
  url: string;
  originalUrl?: string;
  tags: string[];
  recommendedOrder: number;
  source: ArticleSource;
  sourceFile?: string;
  sections?: ArticleSection[];
  content?: CleanArticleContent;
}

export interface ArticleCategoryMeta {
  slug: string;
  title: ArticleCategory;
  description: string;
}

interface CsvRow {
  url: string;
  http_status: string;
  class: string;
  location: string;
  canonical: string;
}

export const articleCategories: ArticleCategoryMeta[] = [
  {
    slug: "beginner",
    title: "新手必讀",
    description: "先用最少篇幅建立 CNFCD、代謝節奏與身體卡住原因的共同語言。",
  },
  {
    slug: "cnfcd-core",
    title: "CNFCD 核心",
    description: "整理 CNFCD 的方法框架、代謝健康觀念與和傳統減重邏輯的差異。",
  },
  {
    slug: "metabolic-repair",
    title: "代謝修復",
    description: "聚焦代謝適應、停滯感、能量動員與身體如何慢慢回到穩定狀態。",
  },
  {
    slug: "insulin-blood-sugar",
    title: "胰島素與血糖",
    description: "整理血糖波動、肝醣、胰島素敏感度與飢餓感之間的關係。",
  },
  {
    slug: "gut-inflammation",
    title: "腸道與發炎",
    description: "從腸道菌相、短鏈脂肪酸、發炎與食慾訊號理解日常狀態。",
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
    slug: "metabolic-disease",
    title: "疾病與代謝風險",
    description: "收錄脂肪肝、糖尿病、三高、腎臟、關節與其他代謝相關風險文章。",
  },
  {
    slug: "myths",
    title: "常見迷思",
    description: "整理常見誤解，幫助讀者拆解熱量、節食、運動與速效說法。",
  },
  {
    slug: "cases-research",
    title: "案例與研究整理",
    description: "放置案例、觀察與研究摘要，作為延伸閱讀入口。",
  },
];

export const categorySlugMap = Object.fromEntries(
  articleCategories.map((category) => [category.title, category.slug]),
) as Record<ArticleCategory, string>;

export const principleArticles: ArticleEntry[] = [
  {
    slug: "metabolism-is-not-willpower",
    title: "代謝不是意志力問題",
    description:
      "從身體節奏、血糖、睡眠與壓力理解為什麼很多人不是不努力，而是方法沒有接住真實生活。",
    category: "新手必讀",
    url: "/notes/metabolism-is-not-willpower",
    tags: ["入門", "代謝", "意志力"],
    recommendedOrder: 1,
    source: "觀念短文",
    sourceFile: "粉絲團神殿思考記錄/2026-05-21-1301-少吃多動然後呢.md",
    sections: [
      {
        heading: "先換一個問題",
        body: [
          "很多人卡住時，第一個反應是問自己是不是不夠自律。但從代謝角度看，更值得問的是：身體現在是不是處在容易失控的環境裡。",
          "長期睡不好、壓力高、吃飯時間亂、外食比例高、血糖起伏大，都會讓身體更難穩定。這些因素不會讓人一夕之間改變，卻會慢慢把飢餓、疲勞與想吃甜的訊號推高。",
        ],
      },
      {
        heading: "為什麼少吃多動不一定夠",
        body: [
          "熱量仍然重要，但身體不是只用熱量表運作。當睡眠、壓力與血糖都不穩，單純把食物再減少，可能讓人更累、更餓，也更難維持。",
          "CNFCD 的入口不是叫人更用力，而是先看懂卡住的位置：飲食結構、血糖穩定、胰島素敏感度、睡眠壓力與腸道狀態。",
        ],
      },
      {
        heading: "這不是治療承諾",
        body: [
          "這個框架屬於健康教育與生活型態理解，不取代醫療診斷、治療或用藥建議。若已有疾病、用藥或持續不適，仍應和專業醫療人員討論。",
        ],
      },
    ],
  },
  {
    slug: "blood-sugar-rollercoaster",
    title: "血糖雲霄飛車：外食族的一天",
    description:
      "用早餐店、便當、手搖飲與宵夜四個場景，理解為什麼外食族常覺得下午崩潰或晚上更餓。",
    category: "胰島素與血糖",
    url: "/notes/blood-sugar-rollercoaster",
    tags: ["血糖", "外食", "飢餓感"],
    recommendedOrder: 2,
    source: "觀念短文",
    sourceFile: "粉絲團神殿思考記錄/2026-05-21-2200-血糖雲霄飛車.md",
    sections: [
      {
        heading: "血糖起伏不是抽象概念",
        body: [
          "早餐只吃精緻澱粉與含糖飲，中午便當又快速補進大量白飯與醬汁，下午再用手搖飲撐精神，晚上疲累後又想吃宵夜。這條路線很像一天裡的血糖雲霄飛車。",
          "血糖快速上升後，身體會透過胰島素協助處理血糖。若一天反覆高低震盪，很多人會感覺下午想睡、容易餓、想吃甜，或晚上更難停下來。",
        ],
      },
      {
        heading: "外食族先做一件事",
        body: [
          "外食不需要追求完美，第一步是找出最常失守的一餐。有人是早餐太甜，有人是午餐飯量與醬汁太重，有人是下午飲料，有人是宵夜。",
          "先把最常震盪的那一站穩住，比整天要求自己完美更實際。這也是文章地圖裡外食族指南的核心：先建立判斷邏輯，再慢慢調整。",
        ],
      },
    ],
  },
  {
    slug: "middle-age-metabolism-after-40",
    title: "為什麼 40 歲後吃一樣的東西卻會胖？真正的原因不是「代謝變慢」",
    description:
      "從胰島素敏感度、肌肉量、睡眠品質與血糖波動，理解 40 歲後身體為什麼更容易卡住。",
    category: "新手必讀",
    url: "/library/middle-age-metabolism-after-40",
    tags: ["40歲後", "中年代謝", "胰島素敏感度", "肌肉量", "睡眠"],
    recommendedOrder: 2,
    source: "知識整理",
    content: {
      slug: "middle-age-metabolism-after-40",
      originalSlug: "middle-age-metabolism-after-40",
      title: "為什麼 40 歲後吃一樣的東西卻會胖？真正的原因不是「代謝變慢」",
      originalUrl: "",
      importedAt: "2026-05-23",
      summary: [
        "很多人 40 歲後覺得自己吃得和以前差不多，體重、腰圍或健檢數字卻開始變化。常見說法是代謝變慢，但這個答案只說到一小部分。",
        "更值得觀察的是身體處理食物的方式變了。胰島素敏感度、肌肉量、睡眠深度、壓力與血糖波動，會一起改變身體如何儲存與使用能量。",
      ],
      keyTakeaways: [
        "20 到 60 歲之間，調整體組成後的日常能量消耗並沒有像大眾想像中大幅下降。",
        "40 歲後更常見的問題，是同樣一餐引發更大的血糖與胰島素反應。",
        "肌肉量下降會讓血糖緩衝能力變差，體重不變也可能代表身體組成改變。",
        "睡眠變淺與壓力累積，會讓飢餓感、嘴饞與隔天飲食選擇更難穩定。",
      ],
      visual: {
        type: "system",
        title: "40 歲後卡住的系統地圖",
        center: "中年代謝卡住",
        nodes: [
          "胰島素敏感度下降",
          "肌肉量無聲流失",
          "睡眠品質變淺",
          "血糖波動變大",
          "身體更容易儲存",
        ],
      },
      blocks: [
        {
          type: "quote",
          text: "我明明吃得跟以前一樣，怎麼一過 40 就開始發胖？這句話背後，常常不是一個原因，而是一整套身體反應方式的改變。",
        },
        {
          type: "heading",
          text: "一、代謝變慢這件事，常被高估了",
        },
        {
          type: "paragraph",
          text: "大部分人一提到中年發胖，第一個解釋就是年紀大了、代謝變慢。這句話聽起來合理，但如果只用它解釋 40 歲後的變化，會忽略更重要的部分。",
        },
        {
          type: "paragraph",
          text: "2021 年 Science 期刊發表一項橫跨 29 國、超過 6,400 人的研究，觀察人類一生的日常能量消耗。研究指出，調整體組成後，20 到 60 歲之間的成人能量消耗大致維持穩定，明顯下降主要出現在 60 歲後。",
        },
        {
          type: "paragraph",
          text: "換句話說，40 歲和 25 歲的差距，通常沒有大到足以單獨解釋所有變胖。真正該問的是：為什麼身體開始用不同方式處理同樣的食物？",
        },
        {
          type: "heading",
          text: "二、真正改變的是身體的反應方式",
        },
        {
          type: "paragraph",
          text: "40 歲後變胖，常見背景不是代謝引擎突然壞掉，而是身體處理血糖、胰島素、肌肉與睡眠壓力的條件變了。以下三件事最常同時發生。",
        },
        {
          type: "list",
          items: [
            "胰島素敏感度下降：同樣一碗飯，身體可能需要更多胰島素才能處理。胰島素長時間偏高時，身體會更傾向儲存能量，也比較不容易動員脂肪。",
            "肌肉量無聲流失：肌肉是血糖的緩衝器。肌肉少了，血糖能被肌肉吸收使用的空間變小，身體組成也可能在體重沒有大變時悄悄改變。",
            "睡眠品質下降：深層睡眠變少、半夜容易醒、壓力恢復不足，都可能影響飽足感、飢餓感與隔天對高熱量食物的渴望。",
          ],
        },
        {
          type: "heading",
          text: "三、所以問題不是更努力，而是換一張地圖",
        },
        {
          type: "paragraph",
          text: "如果只把中年變胖理解成少吃不夠、多動不夠，很容易走回同一條路：更用力節食、撐一段時間、生活一亂就復胖，然後覺得自己失敗。",
        },
        {
          type: "paragraph",
          text: "CNFCD 的知識入口想做的是另一件事：把代謝、血糖、胰島素、肌肉、睡眠、壓力、腸道與外食節奏放回同一張地圖。當你知道身體卡在哪裡，調整才不會只剩下責怪自己。",
        },
        {
          type: "list",
          items: [
            "如果飯後 1 小時想睡、腦袋鈍、需要咖啡續命，可以先觀察血糖波動。",
            "如果半夜常醒、早上疲累、下午嘴饞，可以先觀察睡眠與壓力恢復。",
            "如果體重沒變但腰圍變大，可以先觀察肌肉量、活動量與身體組成。",
          ],
        },
        {
          type: "heading",
          text: "四、這不是治療承諾，而是觀察起點",
        },
        {
          type: "paragraph",
          text: "這篇文章是健康教育與代謝原理整理，不取代醫療診斷、治療或用藥建議。若你已經有糖尿病、脂肪肝、腎臟病、心血管疾病或正在用藥，請以醫師與專業醫療人員的建議為主。",
        },
        {
          type: "paragraph",
          text: "但如果你只是覺得自己 40 歲後開始卡住，可以先不用急著責怪意志力。先觀察飯後精神、半夜醒來次數、腰圍變化與外食節奏，這些線索往往比單次體重更接近身體正在發生的事。",
        },
      ],
      related: [
        {
          label: "胰島素阻抗完整指南",
          href: "/library/life-insulin-resistance-complete-guide",
        },
        {
          label: "CNFCD 與 168 間歇性斷食比較",
          href: "/library/life-cnfcd-vs-168-intermittent-fasting-comparison",
        },
        {
          label: "肌少症、肌肉流失與代謝老化",
          href: "/library/life-sarcopenia-muscle-loss-metabolic-aging",
        },
      ],
      references: [
        {
          label:
            "Pontzer 等人，Daily Energy Expenditure through the Human Life Course，Science 2021",
          href: "https://pubmed.ncbi.nlm.nih.gov/34385400/",
        },
      ],
    },
  },
  {
    slug: "sleep-appetite-metabolism",
    title: "睡不好，為什麼更難穩定飲食",
    description:
      "睡眠不只影響精神，也會牽動飢餓感、甜食渴望、壓力反應與隔天的飲食選擇。",
    category: "睡眠與壓力",
    url: "/notes/sleep-appetite-metabolism",
    tags: ["睡眠", "食慾", "壓力"],
    recommendedOrder: 3,
    source: "觀念短文",
    sourceFile: "粉絲團神殿思考記錄/2026-05-21-2107-今晚睡前做一件小事.md",
    sections: [
      {
        heading: "很多失控從前一晚開始",
        body: [
          "睡不好的人通常不只是累。隔天早上更想吃快速能量，下午更想喝咖啡或甜飲，晚上也更難做出穩定選擇。",
          "這不是單純的意志力問題。睡眠不足會讓身體更容易處在壓力狀態，也會讓大腦更偏好能快速獲得回饋的食物。",
        ],
      },
      {
        heading: "睡前的小事為什麼有用",
        body: [
          "把手機放遠、固定關燈時間、讓晚餐不要太晚、減少睡前刺激，這些小事不是魔法，但它們能降低身體的警戒感。",
          "當睡眠穩一點，隔天的飢餓與情緒波動通常也更容易被管理。CNFCD 看睡眠，是因為它常常是飲食節奏的上游。",
        ],
      },
    ],
  },
  {
    slug: "metabolism-after-40",
    title: "40 歲後代謝環境為什麼會改變",
    description:
      "年齡不是唯一原因；肌肉量、睡眠、壓力、外食與血糖波動一起改變了身體處理能量的背景。",
    category: "代謝修復",
    url: "/notes/metabolism-after-40",
    tags: ["40歲後", "代謝環境", "肌肉量"],
    recommendedOrder: 4,
    source: "觀念短文",
    sourceFile: "FB-本帳貼文包-40後代謝環境-AB最終版-2026-05-08.md",
    sections: [
      {
        heading: "不是突然變差",
        body: [
          "很多人到 40 歲後會發現，以前少吃幾天、走多一點就有感，現在卻不一定有效。這不一定代表人變懶，而是身體處理能量的背景變了。",
          "肌肉量下降、睡眠變淺、壓力累積、外食比例增加、血糖波動變大，這些因素會一起影響身體是否願意穩定動員能量。",
        ],
      },
      {
        heading: "先看代謝環境",
        body: [
          "若只把策略放在吃更少，可能會忽略身體已經處在高壓、疲勞或反覆震盪裡。更務實的做法，是先找出哪個背景因素最常把節奏拉亂。",
          "這也是為什麼體重管理不能只看體重。腰圍、精神、睡眠、下午飢餓、健檢數字，都可能是代謝環境的線索。",
        ],
      },
    ],
  },
  {
    slug: "fatty-liver-metabolic-signal",
    title: "脂肪肝常是代謝訊號，不只是少吃油",
    description:
      "從血糖、胰島素、精緻澱粉、睡眠壓力與肝臟能量處理理解脂肪肝的代謝背景。",
    category: "疾病與代謝風險",
    url: "/notes/fatty-liver-metabolic-signal",
    tags: ["脂肪肝", "三酸甘油脂", "肝臟"],
    recommendedOrder: 5,
    source: "觀念短文",
    sourceFile: "開發-IG-FB新帳開設資料包.md",
    sections: [
      {
        heading: "為什麼不是只看油脂",
        body: [
          "很多人看到脂肪肝，第一個反應是少吃油。但脂肪肝的背景常常不只和油有關，也可能牽涉到血糖波動、胰島素反應、精緻澱粉、酒精、睡眠與壓力。",
          "肝臟是能量處理的重要器官。當能量進出長期失衡，或身體經常處理過多快速吸收的糖與精緻澱粉，肝臟負擔就可能增加。",
        ],
      },
      {
        heading: "該怎麼閱讀這類文章",
        body: [
          "脂肪肝與三酸甘油脂紅字都需要謹慎看待。本站只整理原理與生活型態相關知識，不提供診斷或治療建議。",
          "如果健檢已經有紅字，應以醫師追蹤為主，並把飲食結構、睡眠、壓力、酒精與外食節奏當成可以一起觀察的背景因素。",
        ],
      },
    ],
  },
  {
    slug: "eating-out-stable-rhythm",
    title: "外食族先建立穩定節奏",
    description:
      "外食不是不能減脂；真正關鍵是先在早餐、午餐、下午與晚餐找到最容易崩掉的節點。",
    category: "外食族指南",
    url: "/notes/eating-out-stable-rhythm",
    tags: ["外食", "生活節奏", "餐食順序"],
    recommendedOrder: 6,
    source: "觀念短文",
    sourceFile: "論壇-社群首批發文草稿包.md",
    sections: [
      {
        heading: "真實生活裡的選擇更難",
        body: [
          "早餐店、便當、便利商店、聚餐與宵夜，才是多數人的日常。真正困難的不是知道什麼叫健康，而是在忙、累、壓力大的時候仍有一套可執行的判斷。",
          "因此外食族不必從完美菜單開始，而是先問：哪一餐最常讓整天失速？",
        ],
      },
      {
        heading: "三個簡單判斷",
        body: [
          "第一，這餐有沒有足夠蛋白質。第二，澱粉與含糖飲是不是讓血糖太快上升。第三，吃飯順序能不能先從蔬菜與蛋白質開始，再處理澱粉。",
          "這些不是治療，也不是保證結果，只是讓身體少一點劇烈震盪，讓日常更容易穩住。",
        ],
      },
    ],
  },
  {
    slug: "plateau-and-metabolic-adaptation",
    title: "體重停滯與代謝適應",
    description:
      "停滯不一定代表失敗；有時是身體正在適應長期熱量、壓力與活動變化。",
    category: "代謝修復",
    url: "/notes/plateau-and-metabolic-adaptation",
    tags: ["停滯", "復胖", "代謝適應"],
    recommendedOrder: 7,
    source: "觀念短文",
    sourceFile: "論壇-社群首批發文草稿包.md",
    sections: [
      {
        heading: "一直重來的真正成本",
        body: [
          "反覆下定決心、撐一陣子、生活一亂又回去，最傷的常常不是體重，而是開始不相信自己。",
          "如果一套方法必須每天都完美，才不會崩掉，它可能本來就不適合多數人的真實生活。",
        ],
      },
      {
        heading: "停滯時先看背景",
        body: [
          "停滯時可以先檢查幾件事：睡眠是否變差、壓力是否變高、蛋白質是否不足、日常活動是否下降、外食與飲料是否讓血糖更震盪。",
          "真正的調整不是再罵自己一次，而是找出哪個背景因素正在讓身體更難穩定。",
        ],
      },
    ],
  },
  {
    slug: "gut-appetite-inflammation",
    title: "腸道、發炎與食慾訊號",
    description:
      "腸道不是只管消化，也會透過菌相、短鏈脂肪酸與發炎訊號影響食慾與代謝狀態。",
    category: "腸道與發炎",
    url: "/notes/gut-appetite-inflammation",
    tags: ["腸道", "發炎", "短鏈脂肪酸"],
    recommendedOrder: 8,
    source: "觀念短文",
    sections: [
      {
        heading: "腸道是訊號系統",
        body: [
          "腸道裡的菌相、膳食纖維發酵產生的短鏈脂肪酸，以及腸道屏障狀態，都可能影響食慾、飽足感與發炎背景。",
          "當腸道狀態長期不穩，身體可能更容易出現脹氣、排便不穩、食慾混亂或精神狀態起伏。這些訊號不等於診斷，但值得被放進同一張代謝地圖裡。",
        ],
      },
      {
        heading: "從飲食結構開始",
        body: [
          "腸道相關文章可以優先看膳食纖維、短鏈脂肪酸、腸肝軸與腸腦軸。它們會幫你理解為什麼食物不是只有熱量，也會改變身體接收到的訊號。",
        ],
      },
    ],
  },
];

const csvRows = parseCsv(
  readFileSync("src/data/cnfcd-life-index.csv", "utf-8"),
);

const cleanedLifeArticles = JSON.parse(
  readFileSync("src/data/life-articles.json", "utf-8"),
) as Record<string, CleanArticleContent>;

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

const externalArticles = uniqueCanonicalRows(csvRows)
  .filter((row) => row.class === "indexable_200")
  .filter((row) => row.http_status === "200")
  .filter((row) => row.canonical.startsWith("https://cnfcd.life/"))
  .filter(
    (row) => !excludedUrlParts.some((part) => row.canonical.includes(part)),
  )
  .map((row, index): ArticleEntry => {
    const slug = slugFromUrl(row.canonical);
    const articleSlug = `life-${slug}`;
    const category = categoryFromSlug(slug);
    const content = cleanedLifeArticles[articleSlug]
      ? sanitizeContent(cleanedLifeArticles[articleSlug])
      : undefined;
    return {
      slug: articleSlug,
      title: titleFromSlug(slug),
      description: descriptionFor(category, slug),
      category,
      url: content ? `/library/${articleSlug}` : row.canonical,
      originalUrl: row.canonical,
      tags: tagsFromSlug(slug, category),
      recommendedOrder: index + 20,
      source: content ? "知識整理" : "原站文章",
      content,
    };
  });

export const articles: ArticleEntry[] = [
  ...principleArticles,
  ...externalArticles,
].sort(
  (a, b) =>
    a.recommendedOrder - b.recommendedOrder ||
    a.title.localeCompare(b.title, "zh-Hant"),
);

export const articleStats = {
  total: articles.length,
  principle: principleArticles.length,
  external: externalArticles.length,
  cleaned: externalArticles.filter((article) => article.content).length,
};

function parseCsv(text: string): CsvRow[] {
  const [headerLine, ...lines] = text
    .replace(/^\uFEFF/, "")
    .trim()
    .split(/\r?\n/);
  const headers = parseCsvLine(headerLine);

  return lines.map((line) => {
    const values = parseCsvLine(line);
    const row = Object.fromEntries(
      headers.map((header, index) => [header, values[index] ?? ""]),
    );
    return row as unknown as CsvRow;
  });
}

function parseCsvLine(line: string): string[] {
  const cells: string[] = [];
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

function uniqueCanonicalRows(rows: CsvRow[]): CsvRow[] {
  const seen = new Set<string>();
  return rows.filter((row) => {
    if (!row.canonical || seen.has(row.canonical)) return false;
    seen.add(row.canonical);
    return true;
  });
}

function sanitizeContent(content: CleanArticleContent): CleanArticleContent {
  const blocks: ArticleContentBlock[] = [];

  for (const block of content.blocks) {
    if (isHardStopBlock(block)) break;

    const cleanedBlock = cleanBlock(block);
    if (cleanedBlock) blocks.push(cleanedBlock);
  }

  return {
    ...content,
    summary: content.summary
      .map(normalizeText)
      .filter(isUsefulText)
      .slice(0, 2),
    keyTakeaways: content.keyTakeaways
      .map(normalizeText)
      .filter(isUsefulText)
      .filter((item) => !isStructuralLabel(item))
      .slice(0, 4),
    blocks,
  };
}

function cleanBlock(block: ArticleContentBlock): ArticleContentBlock | null {
  if (block.type === "list") {
    const items = (block.items ?? [])
      .map(normalizeText)
      .filter(isUsefulText)
      .filter((item) => !isStructuralLabel(item));
    return items.length > 0 ? { ...block, items } : null;
  }

  const text = normalizeText(block.text ?? "");
  if (!isUsefulText(text)) return null;
  if (block.type === "heading" && isStructuralLabel(text)) return null;
  return { ...block, text };
}

function isHardStopBlock(block: ArticleContentBlock): boolean {
  const values =
    block.type === "list" ? (block.items ?? []) : [block.text ?? ""];
  return values.some((value) =>
    [
      "CNFCD 個人化代謝健康系統",
      "微康公司",
      "桑日創意",
      "Sun Innovative",
      "Copyright",
      "Design by",
      "發布：",
      "最後更新：",
      "星期一至星期五",
      "Monday–Friday",
      "resetwith0926@gmail.com",
      "email@email.com",
    ].some((keyword) => normalizeText(value).includes(keyword)),
  );
}

function normalizeText(text: string): string {
  return text
    .replace(/【\s*AI\s*摘要\s*】/gi, "")
    .replace(/🔍\s*AI\s*摘要/gi, "")
    .replace(/AI\s*摘要[:：]?/gi, "")
    .replace(
      /CNFCD 是由微康公司開發的個人化代謝飲食方法[，,]?/g,
      "CNFCD 在這裡被整理成一套代謝健康理解框架，",
    )
    .replace(/由微康公司開發的/g, "")
    .replace(/個人化代謝飲食方法/g, "代謝健康理解框架")
    .replace(/個人化飲食調整方向/g, "飲食結構觀察方向")
    .replace(/針對[^，。]*量身設計/g, "以代謝脈絡整理")
    .trim();
}

function isUsefulText(text: string): boolean {
  const value = text.trim();
  if (!value) return false;
  if (/^[a-z0-9-]+$/i.test(value)) return false;
  if (value.startsWith("→ ")) return false;

  const noisyFragments = [
    "💡 本文重點導覽",
    "📋 本文重點摘要",
    "📚 延伸閱讀",
    "AI 摘要",
    "AI摘要",
    "CNFCD 個人化代謝健康系統",
    "微康公司",
    "桑日創意",
    "Sun Innovative",
    "cnfcd-joy123",
    "產品",
    "開發者",
    "官方網站",
    "本文作者",
    "健康顧問",
    "對 CNFCD 學員",
    "CNFCD 學員",
    "學員",
    "客戶",
    "CNFCD 如何幫助",
    "CNFCD 如何協助",
    "立即購買",
    "加入課程",
    "預約諮詢",
    "聯絡我們",
    "免費諮詢",
    "email@email.com",
    "resetwith0926@gmail.com",
    "Copyright",
    "Design by",
  ];

  return !noisyFragments.some((fragment) => value.includes(fragment));
}

function isStructuralLabel(text: string): boolean {
  return [
    "Summary",
    "Main Content",
    "重要免責聲明",
    "完整延伸閱讀地圖",
    "認識脂肪肝",
    "補充與生活",
    "CNFCD 應用",
  ].includes(text.trim());
}

function slugFromUrl(url: string): string {
  return new URL(url).pathname.replace(/^\/|\/$/g, "");
}

function categoryFromSlug(slug: string): ArticleCategory {
  if (
    hasAny(slug, [
      "about-cnfcd",
      "what-is-cnfcd",
      "cnfcd-faq",
      "cnfcd-complete-guide",
      "cnfcd-not",
      "cnfcd-product",
      "who-is-cnfcd",
      "cnfcd-vs-conventional",
      "cnfcd-vs-other",
      "cnfcd-ultimate",
    ])
  ) {
    return slug.includes("complete-guide") || slug.includes("about-cnfcd")
      ? "新手必讀"
      : "CNFCD 核心";
  }

  if (
    hasAny(slug, [
      "diabetes",
      "fatty-liver",
      "nafld",
      "three-highs",
      "cancer",
      "ckd",
      "kidney",
      "gout",
      "uric",
      "pcos",
      "arthritis",
      "gerd",
      "heart",
      "blood-pressure",
      "alzheimers",
      "hypothyroidism",
      "eye-health",
      "skin",
      "autoimmune",
      "cholesterol",
      "triglycerides",
      "blood-lipids",
    ])
  ) {
    return "疾病與代謝風險";
  }

  if (
    hasAny(slug, [
      "insulin",
      "blood-sugar",
      "hba1c",
      "glucose",
      "glycated",
      "gi-food",
    ])
  ) {
    return "胰島素與血糖";
  }

  if (
    hasAny(slug, [
      "gut",
      "microbiome",
      "butyrate",
      "fiber",
      "stool",
      "inflammation",
      "scfa",
    ])
  ) {
    return "腸道與發炎";
  }

  if (
    hasAny(slug, [
      "sleep",
      "stress",
      "cortisol",
      "circadian",
      "breathing",
      "chrononutrition",
    ])
  ) {
    return "睡眠與壓力";
  }

  if (
    hasAny(slug, [
      "eating-out",
      "breakfast",
      "bubble-tea",
      "convenience",
      "hotpot",
      "supermarket",
      "taiwan-common-foods",
      "alcohol",
    ])
  ) {
    return "外食族指南";
  }

  if (
    hasAny(slug, [
      "myth",
      "glp1",
      "intermittent",
      "exercise",
      "artificial",
      "scale",
      "body-fat",
      "eating-less",
      "calorie",
      "fat-loss-vs-weight-loss",
    ])
  ) {
    return "常見迷思";
  }

  if (
    hasAny(slug, [
      "fact-checking",
      "dietary-guidelines",
      "journal",
      "clinical-evidence",
      "metabolic-health-evidence",
      "nutrition-aging-evidence",
    ])
  ) {
    return "案例與研究整理";
  }

  return "代謝修復";
}

function hasAny(value: string, keywords: string[]): boolean {
  return keywords.some((keyword) => value.includes(keyword));
}

function titleFromSlug(slug: string): string {
  const overrides: Record<string, string> = {
    "about-cnfcd": "CNFCD 是什麼",
    "cnfcd-faq": "CNFCD 常見問題",
    "cnfcd-complete-guide": "CNFCD 完整指南",
    "who-is-cnfcd-for-5-types": "誰適合先理解 CNFCD：五種常見情境",
    "cnfcd-vs-other-fat-loss-methods": "CNFCD 與其他減脂方法的差異",
    "cnfcd-vs-conventional-weight-loss": "CNFCD 與傳統減重邏輯的差異",
    "cnfcd-vs-glp1-semaglutide-comparison": "CNFCD 與 GLP-1 藥物機制比較",
    "cnfcd-vs-168-intermittent-fasting-comparison":
      "CNFCD 與 168 間歇性斷食比較",
    "cnfcd-vs-cico-calories-metabolic-structure-comparison":
      "CNFCD 與熱量計算的代謝結構差異",
    "cnfcd-vs-ketogenic-diet-mechanism-pros-cons-comparison":
      "CNFCD 與生酮飲食的機制比較",
    "cnfcd-vs-mediterranean-diet-comparison-metabolic-health":
      "CNFCD 與地中海飲食的代謝健康比較",
    "cnfcd-vs-tcm-traditional-chinese-medicine-comparison":
      "CNFCD 與中醫體質觀點比較",
    "cnfcd-not-a-diet-health-logic-from-160k-data":
      "CNFCD 不是飲食法：從代謝邏輯重新理解健康",
    "fat-loss-week2-plateau-why": "減脂第二週停滯的常見原因",
    "fat-loss-mindset-3-key-shifts": "減脂心態的三個轉換",
    "binge-eating-at-night-solution": "晚上容易暴食的代謝與情緒背景",
    "eating-less-makes-you-fatter-metabolic-truth": "少吃反而更胖？代謝真相",
    "why-eating-too-little-makes-you-fat-metabolic-adaptation":
      "吃太少為什麼可能讓代謝更保守",
    "mindful-eating-emotional-regulation": "正念飲食與情緒調節",
    "family-healthy-eating-strategies": "家庭健康飲食策略",
    "low-gi-food-list-taiwan-diet": "台灣常見低 GI 食物清單",
    "gerd-visceral-fat-root-cause": "胃食道逆流與內臟脂肪的代謝關聯",
    "weight-loss-plateau-science": "體重停滯的科學原因",
    "fat-loss-plateau-complete-guide": "減脂停滯完整指南",
    "fat-loss-plateau-eat-less-myth": "少吃就會突破停滯嗎",
    "insulin-resistance-complete-guide": "胰島素阻抗完整指南",
    "insulin-resistance-self-test-5-warning-signs": "胰島素阻抗的五個常見警訊",
    "insulin-resistance-metabolic-syndrome-science": "胰島素阻抗與代謝症候群",
    "insulin-resistance-root-cause-metabolic-syndrome":
      "代謝症候群背後的胰島素阻抗",
    "insulin-resistance-most-overlooked-metabolic-problem":
      "最容易被忽略的胰島素阻抗問題",
    "diabetes-blood-sugar-organ-damage": "糖尿病、血糖與器官傷害",
    "high-triglycerides-meaning-fat-loss": "三酸甘油脂偏高代表什麼",
    "hba1c-glycated-hemoglobin-fat-loss": "糖化血色素 HbA1c 與脂肪代謝",
    "normal-fasting-glucose-insulin-resistance":
      "空腹血糖正常，也可能有胰島素阻抗",
    "blood-sugar-fat-loss-switch-why-eating-less-fails":
      "血糖與減脂開關：為什麼少吃不一定有效",
    "cgm-continuous-glucose-monitoring-metabolic-optimization":
      "連續血糖監測與代謝觀察",
    "fatty-liver-nafld-reversal-stages": "脂肪肝與 NAFLD 的改善階段",
    "fatty-liver-symptoms-warning-signs": "脂肪肝常見警訊",
    "fatty-liver-symptoms-metabolic-warning-signs": "脂肪肝的代謝警訊",
    "fatty-liver-diet-guide-nafld-stages-food-tips":
      "脂肪肝飲食指南與 NAFLD 階段",
    "fructose-fatty-liver-dnl-mechanism": "果糖、脂肪肝與新生脂肪生成",
    "fatty-liver-metabolic-syndrome-deadly-link": "脂肪肝與代謝症候群的關聯",
    "masld-diet-reversal-clinical-evidence": "MASLD、飲食與臨床證據",
    "pillar-fatty-liver-complete-guide-stages-reversal":
      "脂肪肝完整指南：階段與改善方向",
    "gut-microbiome-obesity-metabolism-2024": "腸道菌相、肥胖與代謝",
    "gut-microbiome-metabolism-fat-loss-connection":
      "腸道菌相、代謝與減脂的關聯",
    "gut-brain-axis-appetite-cravings-metabolism": "腸腦軸、食慾與嘴饞",
    "dietary-fiber-gut-scfa-metabolism": "膳食纖維、短鏈脂肪酸與代謝",
    "butyrate-5-benefits-gut-health-key-molecule": "丁酸鹽與腸道健康",
    "gut-liver-axis-microbiome-liver-health": "腸肝軸與肝臟健康",
    "gut-health-routine-diet-stress-triangle": "腸道健康、飲食與壓力三角",
    "leaky-gut-5-chronic-diseases-connection": "腸漏與慢性疾病的五個關聯",
    "pillar-gut-microbiome-metabolism-complete-guide": "腸道菌相與代謝完整指南",
    "sibo-small-intestinal-bacterial-overgrowth-metabolic":
      "SIBO 小腸菌叢過度生長與代謝",
    "sleep-deprivation-obesity-hormones-science": "睡眠不足如何影響肥胖荷爾蒙",
    "metabolic-syndrome-insomnia-blood-sugar": "代謝症候群、失眠與血糖不穩",
    "poor-sleep-prevents-fat-loss-hormone-science": "睡不好為什麼會影響減脂",
    "stress-eating-cortisol-mechanism": "壓力進食與皮質醇機制",
    "stress-weight-gain-cortisol-root-cause": "壓力、體重上升與皮質醇",
    "stress-cortisol-metabolism-visceral-fat": "壓力、皮質醇與內臟脂肪",
    "breathing-techniques-metabolism-stress-cortisol": "呼吸練習、壓力與皮質醇",
    "eating-out-fat-loss-complete-guide": "外食族減脂完整指南",
    "eating-out-fat-loss-taiwan-blood-sugar": "台灣外食與血糖地雷",
    "breakfast-shop-fat-loss-guide": "早餐店減脂選擇指南",
    "convenience-store-fat-loss-guide": "便利商店減脂選擇指南",
    "hotpot-fat-loss-guide": "火鍋減脂選擇指南",
    "eating-out-hotpot-yakiniku-japanese-fat-loss-guide":
      "火鍋、燒肉、日式外食選擇指南",
    "taiwan-breakfast-night-market-metabolic-traps": "台灣早餐與夜市的代謝陷阱",
    "taiwan-breakfast-nightmarket-metabolic-traps-blood-sugar":
      "台灣早餐、夜市與血糖波動",
    "taiwan-supermarket-fat-loss-shopping-list": "台灣超市減脂採買清單",
    "fat-loss-trap-foods-taiwan-blood-sugar-guide":
      "台灣常見減脂地雷食物與血糖",
    "bubble-tea-metabolism-truth": "手搖飲與代謝真相",
    "bubble-tea-blood-sugar-guide": "手搖飲、血糖與選擇指南",
    "why-metabolism-slows-after-40-science-explanation":
      "40 歲後代謝變慢的科學解釋",
    "slow-metabolism-signs-causes-dietary-solutions":
      "代謝變慢的常見訊號與飲食方向",
    "metabolic-syndrome-definition-taiwan": "台灣常見代謝症候群定義",
    "metabolic-syndrome-comprehensive-lifestyle-reversal":
      "代謝症候群與生活型態調整",
    "pillar-metabolic-syndrome-insulin-resistance-complete-guide":
      "代謝症候群與胰島素阻抗完整指南",
    "metabolic-adaptation-why-diets-fail-science": "代謝適應：為什麼節食常失敗",
    "weight-loss-plateau-metabolic-adaptation": "體重停滯與代謝適應",
    "visceral-fat-real-killer-obesity-who-disease": "內臟脂肪與代謝疾病風險",
    "visceral-fat-cardiovascular-risk-science": "內臟脂肪與心血管風險",
    "waist-circumference-vs-weight-visceral-fat": "腰圍比體重更能提示內臟脂肪",
    "obesity-cancer-risk-who-13-types": "肥胖與 13 種癌症風險",
    "high-blood-pressure-metabolic-root-cause": "高血壓背後的代謝因素",
    "gout-uric-acid-metabolic-syndrome-warning": "痛風、尿酸與代謝症候群",
    "hypertension-blood-pressure-dietary-management": "高血壓、血壓與飲食管理",
    "ckd-kidney-disease-diet-management-stages-guide":
      "慢性腎臟病與飲食管理階段",
    "kidney-disease-dietary-protection-ckd": "腎臟疾病與飲食保護",
    "taiwan-dialysis-rate-kidney-disease-metabolic-link":
      "台灣洗腎率與代謝風險",
    "pcos-metabolic-imbalance-not-gynecological": "PCOS 也常是代謝失衡問題",
    "alzheimers-type3-diabetes-blood-sugar-brain":
      "阿茲海默、第三型糖尿病與大腦血糖",
    "autoimmune-disease-metabolism-inflammation-diet":
      "自體免疫、代謝與發炎飲食",
    "hashimoto-autoimmune-thyroid-metabolic-connection":
      "橋本氏甲狀腺炎與代謝關聯",
    "protein-intake-muscle-fat-loss-science": "蛋白質、肌肉與減脂科學",
    "sarcopenia-muscle-loss-metabolic-aging": "肌少症、肌肉流失與代謝老化",
    "sarcopenic-obesity-double-metabolic-risk": "肌少型肥胖的雙重代謝風險",
    "mitochondrial-dysfunction-metabolic-aging": "粒線體功能與代謝老化",
    "tca-cycle-cofactors-b-vitamins-magnesium": "TCA 循環、B 群與鎂",
    "ampk-mtor-balance-metabolic-health": "AMPK、mTOR 與代謝平衡",
    "circadian-rhythm-chrononutrition-metabolism": "晝夜節律、進食時間與代謝",
    "ultra-processed-food-nova-metabolic-risk": "超加工食品與代謝風險",
    "artificial-sweeteners-metabolic-deception": "人工甜味劑與代謝誤判",
    "glp1-mechanism-muscle-loss-rebound": "GLP-1、肌肉流失與復胖風險",
    "glp1-natural-stimulation-food-diet": "用食物自然刺激 GLP-1 的概念",
    "intermittent-fasting-effective-taiwan-3-mistakes":
      "間歇性斷食常見三個錯誤",
    "intermittent-fasting-mechanism-evidence": "間歇性斷食的機制與證據",
    "exercise-but-not-losing-weight-5-reasons": "運動了還瘦不下來的五個原因",
    "exercise-but-not-losing-weight-fat-loss-order":
      "減脂順序：為什麼運動不是唯一開關",
    "fat-loss-vs-weight-loss-scale-lies": "減脂與減重差異：體重機可能誤導",
    "body-fat-scale-accuracy-explained": "體脂機準確度怎麼看",
    "weight-fluctuation-normal-causes": "體重波動的常見原因",
    "how-much-weight-loss-per-month-science": "每月減重多少比較合理",
    "realistic-monthly-weight-loss-expectation": "合理月減重期待",
  };

  if (overrides[slug]) return overrides[slug];

  return fallbackTitleFromSlug(slug);
}

function fallbackTitleFromSlug(slug: string): string {
  const phraseMap: Record<string, string> = {
    "continuous-glucose-monitoring": "連續血糖監測",
    "traditional-chinese-medicine": "中醫",
    "insulin-resistance": "胰島素阻抗",
    "metabolic-syndrome": "代謝症候群",
    "intermittent-fasting": "間歇性斷食",
    "ultra-processed-food": "超加工食品",
    "artificial-sweeteners": "人工甜味劑",
    "blood-pressure": "血壓",
    "blood-sugar": "血糖",
    "blood-lipids": "血脂",
    "blood-lipid": "血脂",
    "body-fat": "體脂",
    "belly-fat": "腹部脂肪",
    "brown-adipose-tissue": "棕色脂肪組織",
    "brown-fat": "棕色脂肪",
    "fatty-liver": "脂肪肝",
    "visceral-fat": "內臟脂肪",
    "weight-loss": "減重",
    "fat-loss": "減脂",
    "gut-microbiome": "腸道菌相",
    "gut-brain-axis": "腸腦軸",
    "gut-liver-axis": "腸肝軸",
    "leaky-gut": "腸漏",
    "low-gi": "低 GI",
    "high-blood-pressure": "高血壓",
    "heart-health": "心臟健康",
    "cardiovascular-risk": "心血管風險",
    "kidney-disease": "腎臟疾病",
    "chronic-inflammation": "慢性發炎",
    "emotional-eating": "情緒性進食",
    "binge-eating": "暴食傾向",
    "menstrual-cycle": "月經週期",
    "post-menopause": "停經後",
    "metabolic-adaptation": "代謝適應",
    "slow-metabolism": "代謝變慢",
    "office-worker": "上班族",
    "eating-out": "外食",
    "breakfast-shop": "早餐店",
    "bubble-tea": "手搖飲",
    "convenience-store": "便利商店",
    "night-market": "夜市",
    nightmarket: "夜市",
    "three-highs": "三高",
    "whole-milk": "全脂牛奶",
    "medical-aesthetic": "醫美",
    "calorie-counting": "熱量計算",
    "ketogenic-diet": "生酮飲食",
    "mediterranean-diet": "地中海飲食",
    "body-recomposition": "身體重組",
    "brown-fat-activation": "棕色脂肪活化",
    "zinc-deficiency": "鋅缺乏",
    "magnesium-deficiency": "鎂缺乏",
    "vitamin-d": "維生素 D",
    "childhood-trauma": "童年創傷",
    "anti-inflammatory": "抗發炎",
    "fat-burning": "脂肪燃燒",
    "organ-damage": "器官傷害",
    "fat-accumulation": "脂肪堆積",
    "tcm-constitution": "中醫體質",
    "phlegm-dampness": "痰濕",
    "sugar-cravings": "甜食渴望",
    "brain-reward-system": "大腦獎賞系統",
    "protein-quality": "蛋白質品質",
    "weight-gain": "體重上升",
    "water-retention": "水分滯留",
    "food-addiction": "食物成癮",
    "metabolic-warning": "代謝警訊",
    "thin-fat": "瘦胖體質",
    "east-asian": "東亞",
    "male-metabolism": "男性代謝",
    "health-checkup-report": "健檢報告",
    "weight-rebound": "體重復胖",
    "eating-too-little": "吃太少",
    "micronutrient-deficiency": "微量營養素缺乏",
    "glycemic-index": "升糖指數",
    "long-covid": "長新冠",
    "stool-shape": "糞便型態",
    "bristol-scale": "布里斯托量表",
    "vicious-cycle": "惡性循環",
    "joint-inflammation": "關節發炎",
    "skin-acne-eczema": "皮膚、痘痘與濕疹",
    "blood-sugar-lipids-pressure": "血糖、血脂與血壓",
    "eating-less": "少吃",
    "health-information-literacy": "健康資訊識讀",
    "fact-checking": "事實查核",
    "dietary-guidelines": "飲食指南",
    "whole-milk-eggs": "全脂牛奶與雞蛋",
    "dry-eye": "乾眼",
    "macular-degeneration": "黃斑部病變",
    "metabolic-disease": "代謝疾病",
    "metabolic-health": "代謝健康",
  };

  let normalized = slug;
  Object.entries(phraseMap)
    .sort(([a], [b]) => b.length - a.length)
    .forEach(([phrase, label]) => {
      normalized = normalized.replaceAll(phrase, label);
    });

  return normalized
    .split("-")
    .filter(Boolean)
    .map(titleToken)
    .filter(Boolean)
    .join("、")
    .replace(/、+/g, "、");
}

function titleToken(part: string): string {
  const tokenTitleMap: Record<string, string> = {
    cnfcd: "CNFCD",
    is: "是",
    for: "適合",
    why: "為什麼",
    how: "如何",
    what: "什麼",
    not: "不是",
    with: "與",
    vs: "比較",
    root: "根本",
    cause: "原因",
    causes: "原因",
    sign: "訊號",
    signs: "訊號",
    warning: "警訊",
    damage: "傷害",
    organ: "器官",
    organs: "器官",
    disease: "疾病",
    diseases: "疾病",
    chronic: "慢性",
    clinical: "臨床",
    evidence: "證據",
    mechanism: "機制",
    mechanisms: "機制",
    connection: "關聯",
    link: "關聯",
    links: "關聯",
    overview: "總覽",
    truth: "真相",
    strategy: "策略",
    strategies: "策略",
    tips: "提示",
    food: "食物",
    foods: "食物",
    day: "天",
    you: "",
    high: "偏高",
    meaning: "代表什麼",
    aces: "ACES",
    polyphenols: "多酚",
    activation: "活化",
    deficiency: "缺乏",
    inflammatory: "發炎",
    burning: "燃燒",
    where: "去了哪裡",
    does: "",
    go: "",
    accumulation: "堆積",
    constitution: "體質",
    phlegm: "痰",
    dampness: "濕",
    tired: "疲勞",
    system: "系統",
    quality: "品質",
    leucine: "白胺酸",
    gain: "上升",
    or: "或",
    retention: "滯留",
    binge: "暴食",
    solution: "方向",
    senescent: "衰老",
    cells: "細胞",
    addiction: "成癮",
    neuroscience: "神經科學",
    eye: "眼睛",
    myopia: "近視",
    dry: "乾",
    floaters: "飛蚊症",
    cataract: "白內障",
    crisis: "危機",
    bmi: "BMI",
    cold: "冷暴露",
    exposure: "暴露",
    sauna: "桑拿",
    thermal: "溫熱",
    therapy: "療法",
    east: "東方",
    asian: "亞洲",
    thin: "瘦",
    phenotype: "表型",
    decline: "下降",
    hypogonadism: "性腺功能低下",
    glaucoma: "青光眼",
    macular: "黃斑部",
    degeneration: "退化",
    retinal: "視網膜",
    checkup: "健檢",
    report: "報告",
    interpretation: "解讀",
    rebound: "復胖",
    cross: "交會",
    point: "交會點",
    yang: "陽",
    micronutrient: "微量營養素",
    glycemic: "升糖",
    index: "指數",
    long: "長期",
    covid: "COVID",
    stool: "糞便",
    shape: "型態",
    bristol: "布里斯托",
    signal: "訊號",
    vicious: "惡性",
    joint: "關節",
    skin: "皮膚",
    acne: "痘痘",
    eczema: "濕疹",
    signals: "訊號",
    lipids: "血脂",
    pressure: "血壓",
    less: "少吃",
    doesnt: "不等於",
    mean: "代表",
    fatter: "更胖",
    information: "資訊",
    literacy: "識讀",
    fact: "事實",
    checking: "查核",
    us: "美國",
    guidelines: "指南",
    eggs: "雞蛋",
    nutrition: "營養",
    metabolic: "代謝",
    metabolism: "代謝",
    health: "健康",
    fat: "脂肪",
    loss: "減脂",
    weight: "體重",
    obesity: "肥胖",
    sugar: "血糖",
    blood: "血液",
    insulin: "胰島素",
    resistance: "阻抗",
    guide: "指南",
    complete: "完整",
    science: "科學",
    diet: "飲食",
    eating: "飲食",
    gut: "腸道",
    liver: "肝臟",
    sleep: "睡眠",
    stress: "壓力",
    hormones: "荷爾蒙",
    hormone: "荷爾蒙",
    inflammation: "發炎",
    visceral: "內臟",
    risk: "風險",
    risks: "風險",
    muscle: "肌肉",
    aging: "老化",
    diabetes: "糖尿病",
    hypertension: "高血壓",
    cholesterol: "膽固醇",
    triglycerides: "三酸甘油脂",
    uric: "尿酸",
    gout: "痛風",
    kidney: "腎臟",
    ckd: "慢性腎臟病",
    pcos: "PCOS",
    autoimmune: "自體免疫",
    thyroid: "甲狀腺",
    hypothyroidism: "甲狀腺低下",
    alzheimers: "阿茲海默",
    arthritis: "關節炎",
    gerd: "胃食道逆流",
    sibo: "SIBO",
    scfa: "短鏈脂肪酸",
    butyrate: "丁酸鹽",
    fiber: "膳食纖維",
    dietary: "飲食",
    protein: "蛋白質",
    magnesium: "鎂",
    zinc: "鋅",
    omega3: "Omega-3",
    vitamin: "維生素",
    vitamins: "維生素",
    mitochondria: "粒線體",
    mitochondrial: "粒線體",
    tca: "TCA",
    ampk: "AMPK",
    mtor: "mTOR",
    glp1: "GLP-1",
    hba1c: "HbA1c",
    glycated: "糖化",
    glucose: "葡萄糖",
    fasting: "空腹",
    homa: "HOMA",
    ir: "IR",
    cgm: "CGM",
    cico: "CICO",
    nafld: "NAFLD",
    masld: "MASLD",
    hdl: "HDL",
    apob: "ApoB",
    sdldl: "sdLDL",
    lpa: "Lp(a)",
    nmn: "NMN",
    nad: "NAD",
    bpa: "BPA",
    pm25: "PM2.5",
    hiit: "HIIT",
    tcm: "中醫",
    taiwan: "台灣",
    Taiwan: "台灣",
    female: "女性",
    women: "女性",
    male: "男性",
    men: "男性",
    menopause: "更年期",
    estrogen: "雌激素",
    testosterone: "睪固酮",
    andropause: "男性更年期",
    menstrual: "月經",
    cycle: "週期",
    four: "四個",
    phases: "階段",
    period: "經期",
    premenstrual: "經前",
    pregnancy: "懷孕",
    infertility: "不孕",
    longevity: "長壽",
    autophagy: "自噬",
    senescence: "細胞衰老",
    senolytics: "抗衰老細胞",
    telomere: "端粒",
    length: "長度",
    epigenetics: "表觀遺傳",
    environmental: "環境",
    toxins: "毒素",
    endocrine: "內分泌",
    disruptors: "干擾物",
    phthalates: "塑化劑",
    air: "空氣",
    pollution: "污染",
    breathing: "呼吸",
    techniques: "技巧",
    circadian: "晝夜節律",
    chrononutrition: "時間營養",
    cortisol: "皮質醇",
    cravings: "渴望",
    craving: "渴望",
    appetite: "食慾",
    reward: "獎賞",
    brain: "大腦",
    mindful: "正念",
    chewing: "咀嚼",
    pace: "速度",
    water: "水分",
    hydration: "水合作用",
    alcohol: "酒精",
    coffee: "咖啡",
    tea: "茶",
    caffeine: "咖啡因",
    cooking: "烹調",
    methods: "方法",
    impact: "影響",
    impacts: "影響",
    supermarket: "超市",
    shopping: "採買",
    list: "清單",
    hotpot: "火鍋",
    yakiniku: "燒肉",
    japanese: "日式",
    breakfast: "早餐",
    trap: "陷阱",
    traps: "陷阱",
    common: "常見",
    normal: "正常",
    hidden: "隱性",
    same: "一樣",
    smaller: "變小",
    waist: "腰圍",
    circumference: "腰圍",
    scale: "體重機",
    lies: "誤導",
    realistic: "合理",
    monthly: "每月",
    expectation: "期待",
    percentage: "百分比",
    reduction: "降低",
    reduce: "降低",
    repair: "修復",
    protection: "保護",
    sedentary: "久坐",
    post: "後",
    progression: "進階",
    exercise: "運動",
    strength: "肌力",
    training: "訓練",
    comprehensive: "完整",
    pillar: "主題支柱",
    definition: "定義",
    management: "管理",
    adjustment: "調整",
    table: "表格",
    stages: "階段",
    stage: "階段",
    reversal: "改善方向",
    reversible: "可逆性",
    routine: "日常",
    triangle: "三角",
    self: "自我",
    test: "檢測",
    overlooked: "被忽略",
    problem: "問題",
    no: "沒有",
    results: "結果",
    fails: "失效",
    failed: "失效",
    wrong: "錯誤",
    logic: "邏輯",
    makes: "讓",
    too: "太",
    little: "少",
    lower: "降低",
    raise: "提升",
    improve: "改善",
    improvement: "改善",
    explained: "說明",
    factors: "因素",
    scientific: "科學",
    data: "資料",
    journal: "期刊",
    validation: "驗證",
    comparison: "比較",
    compare: "比較",
    conventional: "傳統",
    medical: "醫療",
    aesthetic: "醫美",
    semaglutide: "Semaglutide",
    ketogenic: "生酮",
    calories: "熱量",
    structure: "結構",
    pros: "優點",
    cons: "限制",
    mediterranean: "地中海",
  };

  return tokenTitleMap[part] ?? part;
}

function descriptionFor(category: ArticleCategory, slug: string): string {
  const descriptions: Record<ArticleCategory, string> = {
    新手必讀:
      "適合先建立共同語言，理解 CNFCD 為什麼從代謝、飲食結構與生活節奏一起看身體。",
    "CNFCD 核心":
      "整理 CNFCD 方法框架與代謝健康邏輯，聚焦觀念理解，不放銷售導向。",
    代謝修復:
      "從能量動員、肌肉、粒線體、代謝適應與停滯感，理解身體如何重新穩定。",
    胰島素與血糖:
      "理解血糖波動、胰島素敏感度與食慾、精神、脂肪動員之間的關係。",
    腸道與發炎:
      "整理腸道菌相、膳食纖維、短鏈脂肪酸、發炎與代謝狀態的交互影響。",
    睡眠與壓力: "從睡眠不足、壓力荷爾蒙與節律變化理解為什麼飲食選擇會被帶亂。",
    外食族指南:
      "把代謝原理放回台灣外食情境，整理早餐店、便當、手搖飲與便利商店的選擇邏輯。",
    疾病與代謝風險:
      "以健康教育角度整理代謝與脂肪肝、糖尿病、三高、心血管等風險的關聯。",
    常見迷思:
      "拆解常見減重迷思，避免把所有問題都簡化成意志力、熱量或單一方法。",
    案例與研究整理:
      "以案例或研究索引方式整理可延伸閱讀的脈絡，協助讀者建立完整地圖。",
  };

  if (slug.includes("glp1")) {
    return "整理 GLP-1 相關機制、肌肉流失與復胖風險，提醒讀者用原理理解而非追逐速效。";
  }

  return descriptions[category];
}

function tagsFromSlug(slug: string, category: ArticleCategory): string[] {
  const tags = new Set<string>([category]);
  const keywordTags: [string, string][] = [
    ["insulin", "胰島素"],
    ["blood-sugar", "血糖"],
    ["glucose", "血糖"],
    ["fatty-liver", "脂肪肝"],
    ["gut", "腸道"],
    ["microbiome", "菌相"],
    ["sleep", "睡眠"],
    ["stress", "壓力"],
    ["cortisol", "皮質醇"],
    ["eating-out", "外食"],
    ["bubble-tea", "手搖飲"],
    ["breakfast", "早餐"],
    ["visceral", "內臟脂肪"],
    ["pcos", "PCOS"],
    ["diabetes", "糖尿病"],
    ["glp1", "GLP-1"],
    ["protein", "蛋白質"],
    ["muscle", "肌肉"],
    ["mitochondrial", "粒線體"],
    ["inflammation", "發炎"],
  ];

  keywordTags.forEach(([keyword, tag]) => {
    if (slug.includes(keyword)) tags.add(tag);
  });

  return [...tags].slice(0, 5);
}
