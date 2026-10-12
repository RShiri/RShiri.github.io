/* CV bootcamp content: target companies (Marquee, LSports).
   1. window.BOOTCAMP_TARGETS - dossiers, action checklist, outreach templates (#targets page).
   2. Three prep topics (group "target") for what Marquee will ask that the CV doesn't cover.
   Company facts come from public reporting (see sources); verify open roles before applying. */
window.BOOTCAMP_TARGETS = {
  lead: "שתי חברות, שתי דרכים שונות להיכנס. ל־Marquee לא מצאתי משרה מפורסמת, אז שם פונים ישירות לצוות המייסדים עם משהו להראות. ב־LSports יש משרות Data Engineer פתוחות, אז שם מגישים ומבקשים המלצה מבפנים. בשני המקרים מה שמכריע הוא הפרויקטים שכבר בנית.",

  companies: [
    {
      name: "Marquee",
      pill: "יעד ראשון",
      pillClass: "pill--keep",
      tagline: "סטארטאפ מתל אביב שבונה שכבת החלטות מבוססת AI למחלקות הגיוס במועדוני כדורגל. הוא מאחד נתונים מכל ספק חיצוני עם המודלים הפרטיים של המועדון, והופך אותם לדוחות גיוס ולניתוח טקטי.",
      facts: [
        "המייסדים: דין ברכה (מנכ״ל), דרור רוזנפלד (מוצר ותפעול), יונתן חזות (CTO, בוגר 8200) וטל דרכי (מדענית נתונים ראשית, מעל שמונה שנות ניסיון). החברה צמחה מקבוצת אוהדים ישראלית של ארסנל.",
        "יותר מ־20 מועדונים והתאחדויות משתמשים בפלטפורמה, ביניהם רדינג (Football Intelligence Partner) ולאנוס מארגנטינה. דווח על שיחות עם קבוצות בפרמייר ליג וב־MLS.",
        "אינטגרציה עם SkillCorner: נתונים פיזיים וטקטיים ממעקב וידאו, יחד עם נתוני אירועים, נתונים פיננסיים ונתוני פציעות מספקים אחרים.",
        "גייסו 1.2 מיליון דולר בפברואר 2026, ובסוף יולי 2026 הודיעו על 6.5 מיליון דולר בסך הכול. הכסף מיועד בין היתר <strong>לגיוס עובדים ב־AI, בהנדסה ובמדעי הנתונים</strong>.",
        "מתוכננת התרחבות ל<strong>כדורסל</strong> ולפוטבול אמריקאי, ולשווקים בארה״ב ובבריטניה.",
        "כלכליסט תיאר אותם כ״ה־Claude Code של גיוס שחקנים״.",
        "לא מצאתי עמוד משרות או משרה מפורסמת. לכן פונים ישירות."
      ],
      fit: [
        "הבעיה שלהם היא לאחד נתונים מהרבה ספקים למודל אחד נקי. זה בדיוק מה שעשו הפייפליינים שלך: לה ליגה, הפרמייר ליג והמונדיאל, כולם עם סקרייפינג, ולידציה וטעינה.",
        "מודל ה־xG שלך מכויל, ויש לו דף שמסביר אותו גם למי שאינו טכני. במוצר שלהם, להסביר מודל לסקאוט זה חצי מהעבודה.",
        "יש לך דשבורד NBA, והם מתרחבים לכדורסל.",
        "אתה עובד יומיום עם Claude Code ועם סוכנים, וזה בדיוק סוג המוצר שהם בונים לסקאוטים.",
        "אתה אוהד כדורגל שבונה כלים לכדורגל. בחברה שקמה מקבוצת אוהדים, זה שווה הרבה."
      ],
      gaps: [
        "אנליטיקת גיוס: נרמול ל־90 דקות, התאמה לאחזקת כדור, אחוזונים לפי עמדה ודמיון בין שחקנים. <a href=\"#t/recruit\">לנושא</a>.",
        "נתוני מעקב ונתונים פיזיים, כמו של SkillCorner, ואיך מאחדים נתונים מכמה ספקים. <a href=\"#t/tracking\">לנושא</a>.",
        "מודל שפה בתוך מוצר: RAG, קריאה לכלים, ומניעת הזיות של מספרים. <a href=\"#t/llm\">לנושא</a>.",
        "אין לך פרויקט שנראה כמו המוצר שלהם, כלומר מסך שעוזר לבחור שחקן. דמו קטן כזה הוא הדבר הכי חזק שתוכל לשלוח להם (צעד 5 ברשימה)."
      ]
    },
    {
      name: "LSports",
      pill: "יש משרות פתוחות",
      pillClass: "pill--weak",
      tagline: "ספקית נתוני ספורט בזמן אמת לחברות הימורים (B2B). המוצר המרכזי הוא פיד TRADE360: אירועים, תוצאות חיות ויחסים, באלפי משחקים במקביל.",
      facts: [
        "באתרי משרות מופיעים תפקידי Data Engineer ו־Senior Data Engineer באשקלון במודל היברידי, ו־Data Architect בתל אביב או באשקלון.",
        "דרישות שחוזרות במודעות: פייפליינים בפרודקשן, כלי תזמור כמו Airflow, Glue או Prefect, Kafka, ומאגרי נתונים כמו Iceberg ו־ClickHouse.",
        "המודעות נמצאו באתר שמעתיק משרות, בלי תאריך פרסום. צריך לוודא בלינקדאין או בעמוד הקריירה של LSports שהן עדיין פתוחות.",
        "אשקלון קרובה לבאר שבע יותר מתל אביב. משרה היברידית שם מסתדרת טוב עם לימודים בבן־גוריון."
      ],
      fit: [
        "בנית מיניאטורה של TRADE360 (<code>live-pipeline</code>): producer ו־consumer מעל RabbitMQ topic exchange, מספרי רצף לכל משחק, זיהוי פערים, שחזור מ־snapshot, ומודל in-play שמפרסם יחסי 1X2.",
        "מודל הסתברויות ניצחון חי, שמכויל על נתוני ה־xG שלך.",
        "יש לך כבר אתר הכנה שלם בשבילם (<code>lsports-prep</code>), עם מבחן לכל מיומנות."
      ],
      gaps: [
        "הכלי Kafka מופיע במודעות ולא אצלך. <a href=\"../lsports-prep/skills/kafka.html\">לנושא באתר ההכנה</a>.",
        "תזמור עם Airflow. <a href=\"#t/etl\">לנושא ה־ETL</a>.",
        "השפות C# ו־.NET הן שפות ה־backend המרכזיות שלהם. <a href=\"../lsports-prep/skills/csharp.html\">לנושא באתר ההכנה</a>.",
        "ה־live-pipeline לא מופיע בקו״ח בכלל. זה הפרויקט הכי רלוונטי אליהם, אז צריך להוסיף אותו (צעד 2)."
      ]
    }
  ],

  steps: [
    { id: "bootcamp", who: "שניהם", text: "לעבור את כל הבוטקאמפ, להחליט מה נשאר, ולהעתיק את שורת ה־Skills החדשה לקו״ח." },
    { id: "cv-projects", who: "שניהם", text: "להוסיף לקו״ח שני פרויקטים שחסרים בו: ה־live-pipeline ודשבורד ה־NBA. הנוסח בהודעות המוכנות למטה." },
    { id: "cv-versions", who: "שניהם", text: "להכין שתי גרסאות של שורת הפרופיל, אחת לכל חברה (נוסח למטה), ולשמור שני קבצי PDF." },
    { id: "prep-topics", who: "Marquee", text: "לעבור את שלושת נושאי ההכנה (גיוס, נתוני מעקב, LLM) בציון 70% ומעלה." },
    { id: "demo", who: "Marquee", text: "לבנות דמו קטן שנראה כמו המוצר שלהם: בוחרים שחקן, מקבלים רשימת שחקנים דומים עם אחוזונים לפי עמדה, ודוח סקאוטינג קצר שנכתב רק מתוך המספרים. אפשר לבנות אותו יחד בסשן הבא." },
    { id: "li-follow", who: "Marquee", text: "לעקוב אחרי עמוד החברה בלינקדאין, ולשלוח בקשת חיבור עם הודעה לטל דרכי וליונתן חזות." },
    { id: "email-ceo", who: "Marquee", text: "אחרי שהדמו באוויר: לשלוח לדין ברכה את ההודעה הישירה, עם קישור לדמו." },
    { id: "ls-verify", who: "LSports", text: "לוודא בלינקדאין ובעמוד הקריירה איזו משרת Data Engineer פתוחה, ולשאול אם יש תפקיד סטודנט או ג׳וניור." },
    { id: "ls-prep", who: "LSports", text: "להגיע ל־80% ומעלה באתר ההכנה של LSports, במיוחד ב־Kafka וב־C#." },
    { id: "ls-referral", who: "LSports", text: "למצוא בלינקדאין Data Engineer שעובד ב־LSports, ולבקש שיחה קצרה או המלצה (נוסח למטה). ואז להגיש." },
    { id: "followup", who: "שניהם", text: "אם אין תשובה תוך שבוע: הודעת המשך אחת, קצרה. לא יותר." }
  ],

  templates: [
    {
      title: "שורת פרופיל לקו״ח, גרסת Marquee",
      note: "מחליפה את פסקת ה־PROFILE בגרסה שנשלחת ל־Marquee.",
      text: "Third-year B.Sc. Data Engineering student building football intelligence tools end to end: automated match-data pipelines across several data sources, a calibrated xG model with a plain-language explainer, and live win-probability models. Uses AI-assisted development (Claude Code, agentic workflows) daily to ship fast and verifies every result against the data. Seeking a data / AI engineering role where club decision-making is the product."
    },
    {
      title: "שורת פרופיל לקו״ח, גרסת LSports",
      note: "מחליפה את פסקת ה־PROFILE בגרסה שנשלחת ל־LSports.",
      text: "Third-year B.Sc. Data Engineering student focused on real-time sports data. Built a working miniature of a live sportsbook feed: RabbitMQ topic-exchange fan-out, per-fixture sequencing with gap detection and snapshot recovery, and an in-play model publishing 1X2 prices. Also builds scraping and ETL pipelines into PostgreSQL and MongoDB. Seeking a student or junior Data Engineering position."
    },
    {
      title: "שני פרויקטים להוסיף לקו״ח",
      note: "על פרויקט ה־NBA תשלים בעצמך מה הדשבורד מראה. לא ראיתי את התוכן שלו, ולכן השארתי מקום.",
      text: "Live Sports Data Pipeline (mini-TRADE360) | Python, RabbitMQ, pytest\n• Producer/consumer feed that replays World Cup 2026 matches as live messages over a RabbitMQ topic exchange, with per-fixture sequence numbers, gap detection, snapshot recovery for late joiners, and an in-play Poisson model publishing 1X2 prices.\n\nNBA Analytics Dashboard | Python, Streamlit\n• Interactive NBA dashboard deployed on Streamlit Community Cloud: [what it shows - e.g. player/team stats, comparisons, charts]."
    },
    {
      title: "בקשת חיבור בלינקדאין לטל דרכי (נתונים)",
      note: "בחשבון לינקדאין חינמי, הודעה שמצורפת לבקשת חיבור מוגבלת ל־200 תווים בערך. ההודעה הזו קצרה מזה.",
      text: "Hi Tal, I'm a BGU Data Engineering student building football data tools (a calibrated xG model, match-data pipelines). Marquee is where I want to work - happy to connect. Ram"
    },
    {
      title: "בקשת חיבור בלינקדאין ליונתן חזות (CTO)",
      text: "Hi Jonathan, BGU Data Engineering student here. I build football data pipelines and a live sports feed in Python. Would love to connect and follow Marquee's engineering. Ram"
    },
    {
      title: "הודעה ישירה לדין ברכה (מנכ״ל)",
      note: "לשלוח רק אחרי שהדמו באוויר, ולהחליף את [DEMO LINK]. בלינקדאין כהודעה, או במייל אם תמצא כתובת.",
      text: "Subject: Football data student who wants to build at Marquee\n\nHi Dean,\n\nI'm Ram, a third-year Data Engineering student at Ben-Gurion University. For the past two years I've been building football data tools on my own, and Marquee is the company I most want to work for.\n\nA few things I've built that are close to what you do:\n- A calibrated xG model, with a page that explains to a non-technical reader how it values each shot: https://rshiri.github.io/xg-model/\n- Pipelines that scrape, validate and store match and player data from several sources (La Liga, Premier League, World Cup 2026) - the same many-sources-into-one-model problem Marquee solves for clubs.\n- A small scouting demo built for this message: [DEMO LINK]\n\nI also saw you're expanding into basketball - I built an NBA dashboard as well: https://nba-dashboard-ramshiri.streamlit.app/\n\nI'm looking for a student or junior role in data or AI engineering. Could I have 15 minutes to show you what I built, or is there someone on Tal's or Jonathan's team I should talk to?\n\nThanks,\nRam Shiri\nhttps://rshiri.github.io"
    },
    {
      title: "בקשת המלצה מעובד ב־LSports",
      note: "לשלוח ל־Data Engineer או לראש צוות דאטה שעובד שם. להחליף את [NAME].",
      text: "Hi [NAME], I'm a third-year Data Engineering student at BGU (Beer Sheva, so Ashkelon works well for me). To learn how a feed like TRADE360 works, I built a small version of one: RabbitMQ topic exchange, per-fixture MsgSeq with gap detection, Snapshot-style recovery and an in-play 1X2 pricing consumer - https://rshiri.github.io/live-pipeline/\n\nI'm applying for the Data Engineer role. Would you be open to a 10-minute chat, or to referring me? Thanks either way. Ram"
    },
    {
      title: "הודעת המשך אחרי שבוע",
      text: "Hi [NAME], just following up on my note from last week. I know things are busy - if there's a better person to talk to about data roles, I'd be grateful for a pointer. Ram"
    }
  ],

  sources: [
    { title: "GlobeNewswire: Marquee Raises $6.5 Million (July 2026)", url: "https://www.globenewswire.com/news-release/2026/07/30/3336140/0/en/marquee-raises-6-5-million-to-scale-ai-decision-layer-across-global-sports.html" },
    { title: "Calcalist: Marquee as the Claude Code for sports recruitment", url: "https://www.calcalistech.com/ctechnews/article/kbfidxotv" },
    { title: "Jewish News: From Arsenal to AI", url: "https://www.jewishnews.co.uk/from-arsenal-to-ai-the-israeli-startup-transforming-how-clubs-sign-players/" },
    { title: "Ynet: Marquee raises $1.2 million", url: "https://www.ynetnews.com/business/article/hjkc8rwowe" },
    { title: "AnD Ventures: Marquee", url: "https://www.and-ventures.com/companies/marquee" },
    { title: "Marquee website", url: "https://themarquee.ai/" },
    { title: "Jobify: LSports Data Engineer (Ashkelon)", url: "https://jobify360.co.il/jobs/4264581642-in" },
    { title: "Jobify: LSports Senior Data Engineer (Ashkelon)", url: "https://jobify360.co.il/jobs/4273863645-in" }
  ]
};

(window.BOOTCAMP_TOPICS = window.BOOTCAMP_TOPICS || []).push(

/* ======================================================================= */
{
  id: "recruit",
  group: "target",
  title: "אנליטיקת גיוס שחקנים",
  cv: [],
  why: "זה בדיוק המוצר של Marquee: להפוך נתונים לרשימה קצרה של שחקנים שכדאי להחתים. אם תדע לדבר בשפה של מחלקת גיוס, תבלוט על פני מועמדים שמכירים רק ML.",
  summary: "איך הופכים סטטיסטיקה של שחקנים להמלצת גיוס: נרמול, התאמה להקשר, אחוזונים ודמיון בין שחקנים.",
  html: `
<section>
  <h2>נרמול ל־90 דקות</h2>
  <p>שחקן שהבקיע 6 שערים ב־900 דקות טוב יותר משחקן שהבקיע 8 ב־2,700. לכן כל מספר מצטבר מחולק בדקות ומוכפל ב־90:</p>
<pre><code>df["np_xg_p90"] = df["np_xg"] / df["minutes"] * 90
df = df[df["minutes"] &gt;= 900]     # סף דקות: מתחת לזה, יותר מדי רעש</code></pre>
  <p>בלי <strong>סף דקות</strong>, מחליף ששיחק 40 דקות והבקיע פעם אחת יוביל את הליגה בשערים ל־90 דקות. משתמשים גם ב־<strong>np</strong> (non-penalty): בלי פנדלים, כי מי שבועט פנדלים זו החלטה של המאמן ולא יכולת.</p>
</section>

<section>
  <h2>התאמה להקשר</h2>
  <ul>
    <li><strong>התאמה לאחזקת כדור</strong> (possession-adjusted): בלם בקבוצה שמחזיקה את הכדור 35% מהזמן יבצע הרבה יותר תיקולים ויירוטים, פשוט כי ליריבה יש יותר כדור. מנרמלים פעולות הגנה לפי זמן האחזקה של היריבה.</li>
    <li><strong>חוזק הליגה</strong>: 0.4 xG ל־90 בליגה הבלגית שווה פחות מאותו מספר בפרמייר ליג. משתמשים במקדמי ליגה, או בודקים שחקנים שעברו בין ליגות.</li>
    <li><strong>תפקיד בקבוצה</strong>: קשר שמשחק כ״6״ בקבוצה שתוקפת כל הזמן נראה אחרת מאותו שחקן בקבוצה שמתגוננת.</li>
  </ul>
</section>

<section>
  <h2>אחוזונים לפי עמדה</h2>
  <p>הסקאוט לא שואל ״כמה מסירות מתקדמות הוא עושה״, אלא ״האם הוא בטופ 10% של הקשרים בזה״. משווים כל שחקן <strong>רק לשחקנים באותה עמדה</strong>, ומציגים אחוזונים. זה הבסיס לגרפי הרדאר (pizza charts) שכל מחלקת גיוס מכירה.</p>
<pre><code>df["prog_passes_pct"] = df.groupby("position")["prog_passes_p90"].rank(pct=True) * 100</code></pre>
</section>

<section>
  <h2>דמיון בין שחקנים</h2>
  <p>השאלה הקלאסית: ״השחקן שלנו נמכר. מי דומה לו, זול יותר וצעיר יותר?״</p>
<pre><code>from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity

feats = ["np_xg_p90", "xa_p90", "prog_carries_p90", "pressures_p90", "aerials_won_pct"]
pool = df[df.position == "CM"].reset_index(drop=True)
Z = StandardScaler().fit_transform(pool[feats])     # בלי סטנדרטיזציה, הפיצ׳ר עם הסקאלה הגדולה שולט
sim = cosine_similarity(Z[pool.index[pool.name == "Pedri"]], Z)[0]
pool.assign(sim=sim).query("age &lt;= 23 and market_value &lt; 30e6").nlargest(10, "sim")</code></pre>
  <p>שתי נקודות שמראות הבנה: <strong>בחירת הפיצ׳רים היא החלטה של סגנון</strong>, ולכן היא צריכה להגיע מהסקאוטים. ופיצ׳רים מתואמים, למשל שלושה מדדי מסירה, מקבלים משקל כפול בלי שהתכוונת. אפשר להוריד ממדים עם PCA, או לתת משקלים מפורשים.</p>
</section>

<section>
  <h2>מעבר למספרים</h2>
  <ul>
    <li><strong>גיל</strong>: שחקני שדה מגיעים לשיא בערך בין 24 ל־28, ותלוי בעמדה. בגיוס משלמים על השנים הבאות, לא על העונה האחרונה.</li>
    <li><strong>רגרסיה לממוצע</strong>: חלוץ שהבקיע הרבה יותר מה־xG שלו בעונה אחת כנראה יחזור לממוצע. מי שקונה לפי שערים ולא לפי xG משלם על מזל.</li>
    <li><strong>חוזה, שכר, פציעות ומחיר</strong>: מועדון קונה שחקן, לא שורה בטבלה. Marquee מאחדת גם נתונים פיננסיים ונתוני פציעות בדיוק בגלל זה.</li>
    <li>המשפך: אלפי שחקנים, ואז סינון לפי נתונים, רשימה קצרה, צפייה בווידאו ובדיקת רקע, ובסוף החלטה.</li>
  </ul>
</section>
`,
  tip: "תשתמש במילים שלהם: shortlist, per 90, possession-adjusted, percentile rank, similarity search. ותגיד משפט שמראה שאתה מבין שהמודל משרת סקאוט ולא מחליף אותו: ״המספרים מצמצמים 3,000 שחקנים ל־15, ואז הסקאוט צופה בהם״.",
  questions: [
    {
      q: "שחקן הבקיע 3 שערים ב־180 דקות, כלומר 1.5 ל־90. למה הוא לא אמור להופיע בראש הרשימה?",
      choices: ["כי שערים לא חשובים", "המדגם קטן מדי. לכן משתמשים בסף דקות, למשל 900 דקות, לפני שמדרגים לפי ערכים ל־90", "כי צריך לחלק ב־60 ולא ב־90", "כי צריך להשתמש ב־accuracy"],
      answer: 1,
      explain: "שיעור על מדגם קטן הוא בעיקר רעש. סף דקות, או התאמה בייסיאנית שמושכת מדגמים קטנים לכיוון הממוצע, פותרים את זה."
    },
    {
      q: "למה מתאימים פעולות הגנה לאחזקת הכדור?",
      choices: ["כדי שהמספרים ייראו גבוהים", "שחקן בקבוצה שמחזיקה מעט את הכדור מקבל יותר הזדמנויות לתקל וליירט. בלי התאמה, הסגנון של הקבוצה נראה כמו יכולת של השחקן", "כי זה מה שדורשת אופ״א", "זה רלוונטי רק לשוערים"],
      answer: 1,
      explain: "מנרמלים לפי הזמן שבו ליריבה יש כדור, וכך משווים בלמים מקבוצות בסגנונות שונים."
    },
    {
      q: "איך הכי נכון להציג לסקאוט ש״קשר X טוב במסירות מתקדמות״?",
      choices: ["המספר הגולמי בעונה", "אחוזון מול קשרים אחרים, למשל ״אחוזון 92 בקרב קשרי מרכז בליגה״", "ממוצע מול כל שחקני הליגה, כולל שוערים", "ציון ה־accuracy של המודל"],
      answer: 1,
      explain: "השוואה לאותה עמדה הופכת מספר מופשט למשהו שסקאוט מבין מיד. זה הבסיס לגרפי הרדאר."
    },
    {
      q: "חיפוש שחקנים דומים עם cosine similarity מחזיר תוצאות מוזרות, שנשלטות לגמרי על ידי ״דקות משחק״ ו״מסירות״. מה שכחת?",
      choices: ["לנרמל את הפיצ׳רים (סטנדרטיזציה) לפני חישוב הדמיון", "להשתמש ב־XGBoost", "להוסיף עוד פיצ׳רים", "למיין הפוך"],
      answer: 0,
      explain: "פיצ׳רים עם סקאלה גדולה (מאות מסירות) שולטים במרחק על פני פיצ׳רים קטנים (0.3 xG). לכן הופכים כל פיצ׳ר לציון תקן. ודקות משחק בכלל לא אמורות להיות פיצ׳ר של סגנון."
    },
    {
      q: "חלוץ הבקיע 18 שערים מ־10.5 xG ללא פנדלים. מה הסיכון בגיוס שלו לפי מספר השערים?",
      choices: ["אין סיכון, 18 שערים זה 18 שערים", "סביר שחלק גדול מהפער הוא רעש, והוא יחזור לכיוון ה־xG שלו. משלמים מחיר של 18 על שחקן שמייצר בערך 11", "ה־xG שגוי", "הוא כנראה בועט פנדלים"],
      answer: 1,
      explain: "גימור שעולה ב־xG באופן עקבי קיים, אבל הוא קטן יותר ממה שעונה אחת מראה. לכן בודקים כמה עונות ברצף."
    },
    {
      q: "שלושה פיצ׳רים של מסירה, שמתואמים מאוד ביניהם, נכנסים לחיפוש דמיון. מה הבעיה?",
      choices: ["אין בעיה", "המסירה מקבלת בפועל משקל משולש, והדמיון מוטה לסגנון מסירה בלי שהתכוונת", "החישוב יהיה איטי", "cosine לא עובד עם יותר משני פיצ׳רים"],
      answer: 1,
      explain: "פותרים עם בחירה מכוונת של פיצ׳רים, משקלים מפורשים או PCA. ההחלטה מה ״דומה״ היא החלטה מקצועית של המועדון."
    },
    {
      q: "מה התפקיד הנכון של מודל במחלקת גיוס?",
      choices: ["להחליט את מי להחתים", "לצמצם אלפי שחקנים לרשימה קצרה ומנומקת, שהסקאוטים בודקים בווידאו ובשטח", "להחליף את הסקאוטים", "לחזות את מחיר השחקן בלבד"],
      answer: 1,
      explain: "זה גם מה ש־Marquee מוכרת: שכבה שחוסכת עבודה ידנית ומשפרת החלטות, לא החלטה אוטומטית."
    }
  ],
  open: [
    { q: "המועדון מכר את הקשר המרכזי שלו. איך תשתמש בנתונים כדי למצוא לו מחליף?", a: "<p>קודם מגדירים עם המאמן והסקאוטים מה התפקיד שלו בפועל: פריצת קווים במסירה, לחץ, הגעה לרחבה. בוחרים 6 עד 10 מדדים ל־90 דקות שמתארים את התפקיד, עם התאמה לאחזקה. מגדירים מאגר לפי מגבלות: גיל, תקציב, ליגות, מינימום דקות. מחשבים דמיון על נתונים מנורמלים, ומציגים אחוזונים מול קשרים בליגה של כל מועמד. בודקים עקביות על פני כמה עונות. מוציאים רשימה של 10 עד 15 שחקנים, עם הסבר לכל אחד, שהסקאוטים בודקים בווידאו.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "tracking",
  group: "target",
  title: "נתוני מעקב ואיחוד ספקים",
  cv: [],
  why: "ל־Marquee יש אינטגרציה עם SkillCorner, והמוצר מבטיח לאחד נתונים מכל ספק. בתור מהנדס נתונים אצלם, זו תהיה העבודה שלך: נתוני מעקב, מערכות קואורדינטות שונות, וזיהוי של אותו שחקן אצל ספקים שונים.",
  summary: "ההבדל בין נתוני אירועים לנתוני מעקב, מה מודדים בנתונים פיזיים, ומה שובר פייפליין שמאחד כמה ספקים.",
  html: `
<section>
  <h2>שלושה סוגי נתונים</h2>
  <div class="tbl-scroll"><table>
    <tr><th>סוג</th><th>מה יש בו</th><th>דוגמאות לספקים</th></tr>
    <tr><td><strong>אירועים</strong> (event)</td><td>כל פעולה עם כדור: מסירה, בעיטה, תיקול, עם מיקום וזמן. בערך 3,000 אירועים למשחק</td><td>Opta, StatsBomb, Wyscout</td></tr>
    <tr><td><strong>מעקב</strong> (tracking)</td><td>המיקום של כל 22 השחקנים ושל הכדור, בין 10 ל־25 פעמים בשנייה. מיליוני נקודות למשחק</td><td>מצלמות באצטדיון, SkillCorner (מתוך שידור הטלוויזיה)</td></tr>
    <tr><td><strong>לא ספורטיביים</strong></td><td>חוזים, שכר, שווי שוק ופציעות</td><td>ספקים פיננסיים ורפואיים</td></tr>
  </table></div>
  <p>SkillCorner מפיקה נתוני מעקב מתוך <strong>וידאו של שידור</strong> בעזרת ראייה ממוחשבת. לכן יש לה כיסוי של הרבה ליגות, גם כאלה בלי מצלמות ייעודיות, וזה מה שמעניין מחלקת גיוס. החיסרון: שחקנים שלא נמצאים בפריים מוערכים, ולא נמדדים.</p>
</section>

<section>
  <h2>מה מודדים בנתונים פיזיים</h2>
  <ul>
    <li><strong>מרחק כולל</strong> ו<strong>מרחק בעצימות גבוהה</strong> (HSR), בדרך כלל מעל 20 קמ״ש.</li>
    <li><strong>ספרינטים</strong>, בדרך כלל מעל 25 קמ״ש: מספר ומרחק.</li>
    <li><strong>מהירות שיא</strong>, ולעיתים קרובות אחוזון 99 של המהירות. זה יציב יותר מהמקסימום, שרגיש לרעש.</li>
    <li><strong>האצות</strong> ו<strong>האטות</strong>.</li>
    <li>מדדים טקטיים: ריצות בלי כדור לעומק, לחץ על המוסר, ואפשרויות מסירה שנוצרו.</li>
  </ul>
  <p>הספים משתנים בין ספקים. לכן לפני שמשווים, חייבים לבדוק את ההגדרות. בנוסף מנרמלים לזמן משחק נטו, או לפי שלב המשחק (עם כדור או בלי), ולא רק ל־90 דקות.</p>
</section>

<section>
  <h2>מה שובר איחוד של ספקים</h2>
  <h3>זיהוי ישויות</h3>
  <p>לכל ספק יש מזהים משלו לשחקנים, לקבוצות ולמשחקים. ״Vinícius Júnior״ אצל ספק אחד הוא ״Vinicius Jr.״ אצל ספק אחר. פותרים עם טבלת מיפוי מזהים, התאמה לפי שם מנורמל (בלי ניקוד וסימנים), תאריך לידה ומועדון, ובדיקה ידנית של מקרים לא ודאיים. זו בעיה קלאסית של entity resolution.</p>
  <h3>מערכות קואורדינטות</h3>
<pre><code># כל ספק משתמש ביחידות אחרות למגרש
# StatsBomb: x בין 0 ל־120, y בין 0 ל־80 (יארדים)
# Opta:      x בין 0 ל־100, y בין 0 ל־100 (אחוזים), ציר y הפוך
# מעקב:      מטרים, ראשית הצירים במרכז המגרש
def statsbomb_to_meters(x, y, length=105, width=68):
    return x / 120 * length, y / 80 * width</code></pre>
  <p>גם כיוון ההתקפה משתנה: יש ספקים שתמיד מנרמלים כך שהקבוצה תוקפת ימינה, ויש שלא. מודל xG שאומן על קואורדינטות של ספק אחד ייתן שטויות על קואורדינטות של ספק אחר.</p>
  <h3>זמן, נפח וכיסוי</h3>
  <ul>
    <li>שעון המשחק מול שעון הווידאו, תוספות זמן, ויישור בין אירוע לפריים של מעקב.</li>
    <li>נפח: 25 פריימים בשנייה, כפול 23 אובייקטים, כפול 90 דקות. שומרים ב־Parquet ומחלקים למחיצות לפי משחק, ולא בשורות של טבלה רגילה.</li>
    <li>כיסוי חלקי: לא לכל ליגה יש את כל סוגי הנתונים. המוצר צריך להראות מה חסר, ולא להשלים בשקט.</li>
  </ul>
</section>
`,
  tip: "אם ישאלו מה האתגר באיחוד ספקים, תענה בשלוש מילים: מזהים, קואורדינטות, הגדרות. ותספר מה ראית בעצמך כשעבדת עם כמה מקורות בפרויקטים, למשל שמות קבוצות שונים בין אתרים.",
  questions: [
    {
      q: "מה ההבדל המרכזי בין נתוני אירועים לנתוני מעקב?",
      choices: ["אין הבדל", "נתוני אירועים מתעדים פעולות עם הכדור. נתוני מעקב מתעדים את המיקום של כל השחקנים והכדור, הרבה פעמים בשנייה", "נתוני מעקב כוללים רק את הכדור", "נתוני אירועים מגיעים מ־GPS"],
      answer: 1,
      explain: "רק נתוני מעקב מראים מה עשו השחקנים בלי הכדור: ריצות, מיקום, לחץ. בגלל זה הם יקרים וכבדים."
    },
    {
      q: "מה היתרון של SkillCorner, שמפיקה נתוני מעקב מתוך וידאו של שידור?",
      choices: ["דיוק מושלם", "כיסוי רחב של ליגות שאין בהן מצלמות מעקב ייעודיות, וזה קריטי לגיוס", "הוא חינמי", "הוא כולל נתונים רפואיים"],
      answer: 1,
      explain: "סקאוטינג דורש להשוות שחקנים מהרבה ליגות. החיסרון הוא ששחקנים מחוץ לפריים מוערכים, ולא נמדדים."
    },
    {
      q: "שילבת נתונים משני ספקים, ומודל ה־xG נותן ערכים גבוהים מדי לבעיטות מאחד מהם. מה החשוד הראשון?",
      choices: ["באג ב־XGBoost", "מערכת קואורדינטות שונה: יחידות שונות (יארדים או אחוזים) או ציר הפוך, ולכן המרחק מהשער מחושב לא נכון", "חוסר בנתונים", "הספק השני טוב יותר"],
      answer: 1,
      explain: "צריך להמיר הכול למערכת אחת, למשל מטרים עם כיוון התקפה אחיד, עוד לפני חישוב הפיצ׳רים."
    },
    {
      q: "אותו שחקן מופיע כ־\"Vinícius Júnior\" אצל ספק אחד וכ־\"Vinicius Jr.\" אצל אחר. איך קוראים לבעיה, ואיך פותרים?",
      choices: ["Data leakage, ופותרים עם פיצול לפי זמן", "Entity resolution: טבלת מיפוי מזהים, התאמה לפי שם מנורמל, תאריך לידה ומועדון, ובדיקה ידנית של מקרים לא ודאיים", "Overfitting, ופותרים עם רגולריזציה", "מתעלמים, זה רק שם"],
      answer: 1,
      explain: "טעות כאן היא שקטה ומסוכנת: שני שחקנים יתמזגו לאחד, או ששחקן אחד יתפצל לשניים."
    },
    {
      q: "למה משתמשים באחוזון 99 של המהירות ולא במהירות המקסימלית?",
      choices: ["כי הוא גבוה יותר", "כי המקסימום רגיש לרעש של פריים בודד. אחוזון 99 משקף מהירות שהשחקן באמת מגיע אליה", "כי ככה מחייבת פיפ״א", "אין סיבה"],
      answer: 1,
      explain: "שגיאת מדידה אחת יכולה ליצור ״ספרינט״ של 40 קמ״ש. אחוזון גבוה עמיד יותר לחריגים."
    },
    {
      q: "איך כדאי לשמור נתוני מעקב בהיקף של כמה עונות?",
      choices: ["שורה לכל פריים בטבלת PostgreSQL רגילה", "בקבצים עמודתיים כמו Parquet, עם מחיצות לפי משחק או תאריך, ומעליהם שכבה מסוכמת למדדים לכל שחקן", "בקובץ CSV אחד", "ב־Excel"],
      answer: 1,
      explain: "מיליוני נקודות למשחק דורשים פורמט עמודתי ודחוס. רוב השאילתות במוצר רצות ממילא על המדדים המסוכמים."
    }
  ],
  open: [
    { q: "איך היית מתכנן פייפליין שמאחד נתוני אירועים, נתוני מעקב ונתונים פיננסיים לפרופיל שחקן אחד?", a: "<p>שכבה גולמית לכל ספק כמו שהוא. שכבת סטנדרטיזציה: קואורדינטות במטרים עם כיוון התקפה אחיד, זמנים ב־UTC ובשעון משחק, ויחידות ושמות שדות אחידים. טבלת מיפוי מזהים לשחקנים, לקבוצות ולמשחקים, עם ציון ביטחון ובדיקה ידנית. אחר כך מדדים לכל שחקן ולכל משחק, ותצוגה מאוחדת לכל שחקן ועונה, שמסמנת אילו מקורות קיימים ואילו חסרים. בכל שלב ולידציה ובדיקת נפחים. בסוף, פיצ׳רים למודלים ול־LLM שמגיעים מהתצוגה המאוחדת.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "llm",
  group: "target",
  title: "מודל שפה בתוך מוצר נתונים",
  cv: [],
  why: "Marquee מתוארת כ״ה־Claude Code של גיוס שחקנים״: סקאוט שואל בשפה חופשית ומקבל דוח. בתור מי שעובד עם סוכנים, אתה צריך לדעת גם איך בונים אחד כזה, לא רק איך משתמשים בו.",
  summary: "איך בונים עוזר מבוסס LLM מעל נתוני ספורט בלי שהוא ימציא מספרים: RAG, קריאה לכלים, פלט מובנה והערכה.",
  html: `
<section>
  <h2>הבעיה: מודל שפה ממציא מספרים</h2>
  <p>אם שואלים מודל שפה ״כמה xG היה לסאקה בעונה שעברה?״, הוא ייתן מספר שנשמע סביר, וייתכן מאוד שהוא שגוי. במוצר לגיוס, מספר מומצא אחד מספיק כדי שהסקאוט יפסיק לסמוך על הכלי. לכן העיקרון הוא: <strong>המודל לא יודע את המספרים, הוא שולף אותם</strong>.</p>
</section>

<section>
  <h2>קריאה לכלים (tool use)</h2>
  <p>נותנים למודל פונקציות מוגדרות היטב, והוא מחליט מתי לקרוא להן. החישוב קורה בקוד ובמסד הנתונים, והמודל רק מנסח את התוצאה.</p>
<pre><code>tools = [
  {"name": "player_stats",
   "description": "Per-90 stats and position percentiles for one player and season",
   "input_schema": {"type": "object",
                    "properties": {"player_id": {"type": "string"}, "season": {"type": "string"}},
                    "required": ["player_id", "season"]}},
  {"name": "similar_players",
   "description": "Players most similar to a given player, with optional age and value filters",
   "input_schema": {...}},
]
# שאלה: "מי דומה לפדרי, מתחת לגיל 23?"
# המודל קורא ל־similar_players, הקוד מריץ את החיפוש מול המסד ומחזיר JSON,
# והמודל כותב דוח שמצטט רק את המספרים שחזרו</code></pre>
  <p>זו אותה לולאה אג׳נטית שאתה מכיר מ־Claude Code: המודל מחליט, כלי מבצע, המודל רואה את התוצאה וממשיך.</p>
</section>

<section>
  <h2>RAG, לטקסט חופשי</h2>
  <p><strong>Retrieval-Augmented Generation</strong>: לפני שהמודל עונה, שולפים את הקטעים הרלוונטיים ומכניסים אותם להקשר. זה מתאים לדוחות סקאוטינג כתובים, לסיכומי משחקים ולהערות של המועדון, כלומר לידע הפרטי שהמועדון לא רוצה לחשוף.</p>
  <ol>
    <li>מחלקים את המסמכים לקטעים (chunks), ומחשבים לכל קטע <strong>embedding</strong>: וקטור שמייצג את המשמעות שלו.</li>
    <li>שומרים את הווקטורים במאגר וקטורי, למשל pgvector בתוך PostgreSQL.</li>
    <li>בזמן שאלה: מחשבים embedding לשאלה, ושולפים את הקטעים הקרובים ביותר.</li>
    <li>שולחים למודל את השאלה ואת הקטעים, עם הוראה לענות רק מתוכם ולציין מקור.</li>
  </ol>
  <p>למספרים מדויקים עדיף text-to-SQL או כלים ייעודיים, ולא RAG. חיפוש וקטורי מוצא טקסט דומה, לא מחשב סכומים.</p>
</section>

<section>
  <h2>מה הופך את זה למוצר</h2>
  <ul>
    <li><strong>פלט מובנה</strong>: מבקשים JSON לפי סכמה, כדי שהממשק יציג אותו בצורה אחידה ויוכל לבדוק אותו.</li>
    <li><strong>הרשאות</strong>: הכלים מקבלים גישה לקריאה בלבד, ורק לנתונים של המועדון שלך. נתונים של מועדון אחד לעולם לא יגיעו למועדון אחר.</li>
    <li><strong>הערכה</strong>: סט של שאלות עם תשובות ידועות, שרץ על כל שינוי בהנחיות או במודל. בודקים נכונות של מספרים, ציטוט מקורות ומקרים שבהם צריך לסרב.</li>
    <li><strong>עלות וזמן תגובה</strong>: מודל קטן לסיווג השאלה, מודל חזק לדוח עצמו, ו־caching להקשר שחוזר על עצמו.</li>
  </ul>
</section>
`,
  tip: "תגיד את העיקרון במשפט אחד: ״המודל אף פעם לא ממציא מספר. כל מספר בדוח מגיע מקריאה לכלי, וכל טענה בטקסט מגיעה ממקור שאפשר להציג״. ואם תבנה את הדמו לצעד 5, תבנה אותו בדיוק כך.",
  questions: [
    {
      q: "סקאוט שואל את העוזר ״כמה xG היה לשחקן X בעונה שעברה?״. מה הארכיטקטורה הנכונה?",
      choices: ["לסמוך על הידע של המודל", "המודל קורא לכלי שמריץ שאילתה מול המסד, ומנסח תשובה רק מהמספר שחזר", "לשאול את המודל שלוש פעמים ולמצע", "RAG על כתבות חדשות"],
      answer: 1,
      explain: "מספרים מגיעים מהמסד, דרך כלי. המודל אחראי על הבנת השאלה ועל הניסוח, לא על העובדות."
    },
    {
      q: "מה זה embedding?",
      choices: ["דחיסה של קובץ", "וקטור מספרי שמייצג את המשמעות של טקסט, כך שטקסטים דומים במשמעות קרובים זה לזה", "סוג של מסד נתונים", "הצפנה"],
      answer: 1,
      explain: "בזכות זה, חיפוש של ״קשר שפורץ קווים במסירה״ ימצא דוח שכתוב בו ״מסירות חודרות בין הקווים״, גם בלי מילים משותפות."
    },
    {
      q: "מתי RAG מתאים, ומתי כלי שמריץ SQL?",
      choices: ["תמיד RAG", "RAG מתאים לטקסט חופשי, כמו דוחות סקאוטינג. SQL או כלי מתאימים למספרים, סכומים וסינונים מדויקים", "תמיד SQL", "אין הבדל"],
      answer: 1,
      explain: "חיפוש וקטורי מחזיר קטעים דומים, הוא לא סוכם ולא מסנן במדויק. שאלה כמו ״כמה שחקנים מתחת לגיל 23 עם יותר מ־0.3 xG״ היא שאילתה."
    },
    {
      q: "למה לבקש מהמודל פלט מובנה (JSON לפי סכמה) ולא טקסט חופשי?",
      choices: ["כי זה זול יותר", "כדי שהממשק יציג את הדוח בצורה אחידה, ושהקוד יוכל לבדוק אותו, למשל שכל מספר קיים בנתונים", "כי מודלים לא יודעים לכתוב טקסט", "אין סיבה"],
      answer: 1,
      explain: "פלט מובנה הופך תשובה של מודל לנתון שאפשר לעבד, לאמת ולהציג."
    },
    {
      q: "איך יודעים ששינוי בהנחיות (prompt) לא שבר את העוזר?",
      choices: ["בודקים שאלה אחת ידנית", "מריצים סט הערכה של שאלות עם תשובות ידועות, ובודקים נכונות מספרים, ציטוט מקורות וסירוב כשצריך", "סומכים על המודל", "מחכים לתלונות"],
      answer: 1,
      explain: "זה המקבילה של בדיקות יחידה בעולם של מודלי שפה. בלי זה, כל שינוי הוא הימור."
    },
    {
      q: "בפלטפורמה שמשרתת כמה מועדונים, מה הסיכון הכי חמור בעוזר מבוסס LLM?",
      choices: ["תשובות ארוכות מדי", "שהמודל ישלוף ויחשוף דוחות סקאוטינג פרטיים של מועדון אחד למועדון אחר", "שהוא יענה באנגלית", "עלות"],
      answer: 1,
      explain: "הדוחות הפרטיים הם הנכס הכי רגיש של מועדון. ההפרדה נאכפת בשכבת הכלים וההרשאות, ולא בהנחיה למודל."
    }
  ],
  open: [
    { q: "תכנן עוזר שעונה לסקאוט ״תמצא לי מחליף לבלם השמאלי שלנו, עד 20 מיליון״.", a: "<p>המודל מפרק את הבקשה לפרמטרים: עמדה, רגל, תקציב, ואולי גיל וליגות. הוא קורא לכלי שמביא את הפרופיל של הבלם הנוכחי, ואחר כך לכלי של חיפוש שחקנים דומים עם הסינונים. לכל מועמד הוא קורא לכלי סטטיסטיקה ואחוזונים, ואולי ל־RAG על הדוחות הפנימיים של המועדון. בסוף מחזיר JSON לפי סכמה: מועמדים, נימוק לכל אחד, והמספרים מתוך הכלים בלבד. כל טענה מקושרת למקור. מעל כל זה יש סט הערכה, הרשאות לפי מועדון, ולוגים.</p>" }
  ]
}
);
