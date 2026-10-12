/* CV bootcamp content: Data Engineering (scraping, ETL, REST, PostgreSQL, MongoDB, Docker, Git). */
(window.BOOTCAMP_TOPICS = window.BOOTCAMP_TOPICS || []).push(

/* ======================================================================= */
{
  id: "scraping",
  group: "de",
  title: "Web scraping",
  cv: ["Web scraping"],
  usedIn: ["laliga", "worldcup", "barca"],
  dropAdvice: "שים לב: שלושה פרויקטים מבוססים על סקרייפינג, אז הורדה מחייבת לנסח מחדש את כולם",
  summary: "הבסיס של רוב הפרויקטים שלך. ישאלו איך מתמודדים עם דפים דינמיים, עם חסימות ועם שבירה של הסקרייפר.",
  html: `
<section>
  <h2>דף סטטי עם requests ו־BeautifulSoup</h2>
<pre><code>import requests
from bs4 import BeautifulSoup

session = requests.Session()                    # שימוש חוזר בחיבור TCP ובעוגיות
session.headers["User-Agent"] = "Mozilla/5.0 (research bot; contact: me@example.com)"

resp = session.get(url, timeout=10)             # בלי timeout הבקשה יכולה להיתקע לנצח
resp.raise_for_status()                         # זורק חריגה על 4xx ו־5xx
soup = BeautifulSoup(resp.text, "html.parser")

for row in soup.select("table.stats_table tbody tr"):    # בורר CSS
    player = row.select_one("th a").get_text(strip=True)
    goals = int(row.select_one('td[data-stat="goals"]').get_text() or 0)</code></pre>
</section>

<section>
  <h2>דף דינמי, כשהטבלה ריקה</h2>
  <p>הרבה אתרים מודרניים טוענים את הנתונים ב־JavaScript אחרי שהדף עולה. אז <code>requests</code> מקבל HTML בלי הנתונים. שתי גישות:</p>
  <ol>
    <li><strong>עדיף</strong>: לפתוח בדפדפן את כלי המפתחים, ללשונית Network, לסנן לפי <code>Fetch/XHR</code>, ולמצוא את קריאת ה־API שמחזירה JSON. אחר כך קוראים ל־API הזה ישירות. זה מהיר יותר, יציב יותר, ומחזיר נתונים מובנים.</li>
    <li><strong>אם אין ברירה</strong>: דפדפן ללא ממשק (headless) כמו Playwright או Selenium, שמריץ את ה־JavaScript ומחכה שהאלמנט יופיע. זה איטי וכבד יותר.</li>
  </ol>
<pre><code>from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto(url)
    page.wait_for_selector("table.match-events")
    html = page.content()</code></pre>
</section>

<section>
  <h2>להיות אזרח טוב, ולא להיחסם</h2>
  <ul>
    <li>בודקים את <code>robots.txt</code> ואת תנאי השימוש של האתר.</li>
    <li><strong>הגבלת קצב</strong>: המתנה בין בקשות, ומספר מוגבל של בקשות מקבילות.</li>
    <li>קוד <strong>429 Too Many Requests</strong>: מאטים, מכבדים את הכותרת <code>Retry-After</code>, ומנסים שוב עם exponential backoff.</li>
    <li>קודי 5xx ו־timeouts הם זמניים, ולכן מנסים שוב. קודים כמו 404 ו־403 לא ישתנו מניסיון חוזר.</li>
    <li>שומרים במטמון דפים שכבר הורדו, כדי לא להוריד שוב משחקים שהסתיימו.</li>
  </ul>
</section>

<section>
  <h2>סקרייפר שלא נשבר בשקט</h2>
  <ul>
    <li><strong>לשמור את ה־HTML או ה־JSON הגולמי</strong> לפני הניתוח. אם הפרסר נשבר או שרוצים שדה חדש, מנתחים מחדש בלי להוריד שוב.</li>
    <li><strong>ולידציה אחרי הניתוח</strong>: האם יש 10 משחקים במחזור? האם יש 11 שחקנים בהרכב? טבלה ריקה היא שגיאה, לא הצלחה.</li>
    <li>בוררים לפי מאפיינים יציבים, כמו <code>data-stat="goals"</code>, ולא לפי מיקום (״העמודה הרביעית״) או לפי שמות class שנוצרו אוטומטית.</li>
    <li>לוגים והתראה כשמספר הרשומות קופץ או צונח פתאום.</li>
  </ul>
</section>
`,
  tip: "ספר על בעיה אמיתית שפתרת: ״אחד האתרים טען את האירועים ב־JavaScript, אז מצאתי בלשונית Network את ה־API הפנימי ועברתי לקרוא JSON ישירות. זה היה פי עשרה מהיר ויציב יותר מ־Selenium״. אם זה לא קרה לך, תבחר דוגמה שכן קרתה. מראיינים מזהים מהר סיפור מומצא.",
  questions: [
    {
      q: "ה־HTML ש־requests מחזיר לא מכיל את טבלת האירועים שאתה רואה בדפדפן. מה הצעד הראשון?",
      choices: ["להחליף ל־lxml במקום html.parser", "לפתוח את לשונית Network בכלי המפתחים ולחפש קריאת XHR שמחזירה את הנתונים כ־JSON", "להוסיף sleep של 10 שניות", "להוסיף User-Agent"],
      answer: 1,
      explain: "הנתונים כנראה נטענים ב־JavaScript. קריאה ישירה ל־API הפנימי היא הפתרון הכי מהיר ויציב. דפדפן ללא ממשק הוא האפשרות הבאה."
    },
    {
      q: "השרת מחזיר קוד 429. מה זה אומר ומה עושים?",
      choices: ["הדף לא קיים, מדלגים עליו", "יותר מדי בקשות. מאטים, מכבדים את Retry-After ומנסים שוב עם backoff", "שגיאת שרת, מנסים מיד שוב", "צריך להתחבר עם סיסמה"],
      answer: 1,
      explain: "הקוד 429 הוא Too Many Requests. ניסיון חוזר מיידי רק יחמיר את המצב, ועלול להוביל לחסימה של כתובת ה־IP."
    },
    {
      q: "למה חשוב להעביר <code>timeout=</code> ל־<code>requests.get</code>?",
      choices: ["כדי שהבקשה תהיה מהירה יותר", "בלי timeout אין מגבלת זמן, ושרת שלא עונה יתקע את כל הפייפליין", "זה נדרש כדי לקבל JSON", "כדי לשמור עוגיות"],
      answer: 1,
      explain: "ברירת המחדל של requests היא בלי timeout. בפייפליין מתוזמן, תהליך אחד תקוע יכול לחסום את כל ההרצות הבאות."
    },
    {
      q: "מה היתרון של שמירת ה־HTML הגולמי לפני הניתוח?",
      choices: ["חיסכון במקום", "אפשר לנתח מחדש אחרי תיקון באג או הוספת שדה, בלי להוריד שוב מהאתר", "האתר דורש את זה", "ההורדה מהירה יותר"],
      answer: 1,
      explain: "זה עיקרון ידוע בהנדסת נתונים: שומרים שכבה גולמית (raw, או bronze) ומנתחים ממנה. זה גם מאפשר לחזור אחורה ולבדוק."
    },
    {
      q: "מה זה exponential backoff?",
      choices: ["להוריד דפים בסדר הפוך", "המתנה שגדלה אקספוננציאלית בין ניסיונות חוזרים, למשל 1, 2, 4 ו־8 שניות", "דחיסה של התגובה", "הגבלה של מספר התהליכונים"],
      answer: 1,
      explain: "מוסיפים לזה בדרך כלל רכיב אקראי קטן (jitter), כדי שהרבה לקוחות לא ינסו שוב בדיוק באותו רגע."
    },
    {
      q: "איזה בורר יחזיק מעמד הכי טוב אחרי שינוי עיצוב באתר?",
      choices: ["<code>td:nth-child(4)</code>", "<code>td[data-stat=\"goals\"]</code>", "<code>.css-1x7f9k2</code>", "<code>div &gt; div &gt; div &gt; span</code>"],
      answer: 1,
      explain: "מאפיין סמנטי כמו data-stat מתאר את משמעות התוכן, ולכן הוא משתנה לעיתים רחוקות. מיקום ושמות class שנוצרו אוטומטית נשברים בכל עיצוב מחדש."
    },
    {
      q: "מה היתרון של <code>requests.Session()</code> על פני קריאות <code>requests.get</code> נפרדות?",
      choices: ["אין יתרון", "שימוש חוזר בחיבור (connection pooling), ושמירה של עוגיות וכותרות בין בקשות", "הוא עוקף robots.txt", "הוא מריץ JavaScript"],
      answer: 1,
      explain: "כשמורידים מאות דפים מאותו אתר, החיסכון בפתיחת חיבורי TCP ו־TLS חדשים מורגש מאוד."
    }
  ],
  open: [
    { q: "הסקרייפר שלך רץ כל לילה. איך תדע שהוא נשבר?", a: "<p>ולידציה אחרי כל הרצה: מספר רשומות צפוי (10 משחקים במחזור), שדות חובה שאינם ריקים, וערכים בטווח הגיוני. השוואה לנפח של ההרצות הקודמות. אם הוולידציה נכשלת, ההרצה נכשלת בקול, עם לוג והתראה, ולא כותבת נתונים חלקיים. בנוסף, שמירת התגובה הגולמית כדי לדבג.</p>" },
    { q: "מה השיקולים החוקיים והאתיים בסקרייפינג?", a: "<p>כיבוד robots.txt ותנאי השימוש. הגבלת קצב כדי לא להעמיס על השרת. לא לאסוף מידע אישי מעבר לנדרש. ולבדוק אם יש API רשמי, שהוא כמעט תמיד עדיף. בפרויקט של המונדיאל, שבו אספתי פוסטים מרשתות חברתיות, כדאי להזכיר אנונימיזציה של משתמשים.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "etl",
  group: "de",
  title: "ETL pipelines",
  cv: ["ETL pipelines"],
  usedIn: ["laliga", "worldcup"],
  summary: "הלב של תפקיד Data Engineer. בקו״ח כתבת scheduling, retry logic ו־data validation, אז כל אחד מהם יכול להפוך לשאלה.",
  html: `
<section>
  <h2>שלושת השלבים, ו־ETL מול ELT</h2>
  <ul>
    <li><strong>Extract</strong>: משיכת נתונים מהמקור, כמו אתר, API או מסד נתונים.</li>
    <li><strong>Transform</strong>: ניקוי, המרת טיפוסים, צירוף טבלאות, חישוב שדות וולידציה.</li>
    <li><strong>Load</strong>: כתיבה ליעד, כמו PostgreSQL או מחסן נתונים.</li>
  </ul>
  <p>ב־<strong>ELT</strong> טוענים קודם את הנתונים הגולמיים ליעד, ועושים את הטרנספורמציה בתוכו עם SQL, למשל בכלי dbt. זה נפוץ במחסני נתונים בענן כמו BigQuery ו־Snowflake, כי המחשוב שם זול וגמיש, והנתונים הגולמיים נשמרים לשימוש חוזר.</p>
</section>

<section>
  <h2>אידמפוטנטיות, המילה הכי חשובה</h2>
  <p>פייפליין <strong>אידמפוטנטי</strong> מחזיר את אותה תוצאה גם אם מריצים אותו פעמיים על אותם נתונים. זה מה שמאפשר retry בלי פחד: אם ההרצה קרסה באמצע, פשוט מריצים שוב, בלי כפילויות.</p>
<pre><code>-- upsert ב־PostgreSQL לפי מפתח טבעי
INSERT INTO matches (match_id, match_date, home_id, away_id, home_goals, away_goals)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (match_id) DO UPDATE
SET home_goals = EXCLUDED.home_goals,
    away_goals = EXCLUDED.away_goals,
    updated_at = now();</code></pre>
  <p>דרכים נוספות: למחוק ולטעון מחדש מחיצה שלמה (״כל משחקי המחזור ה־12״) בתוך טרנזקציה אחת, או לכתוב לטבלת staging ולהחליף בסוף.</p>
</section>

<section>
  <h2>טעינה מלאה מול טעינה מצטברת</h2>
  <ul>
    <li><strong>טעינה מלאה</strong>: מושכים את הכול בכל פעם. פשוט, ומתאים לנתונים קטנים.</li>
    <li><strong>טעינה מצטברת</strong>: מושכים רק מה שהשתנה מאז ההרצה הקודמת, לפי <strong>watermark</strong> כמו <code>max(updated_at)</code> או תאריך המשחק האחרון שנטען.</li>
    <li><strong>Backfill</strong>: הרצה של הפייפליין על טווח היסטורי, למשל כשמוסיפים עמודה חדשה ורוצים אותה גם לעונות קודמות. פייפליין אידמפוטנטי שמקבל תאריכים כפרמטר הופך את זה לפשוט.</li>
  </ul>
</section>

<section>
  <h2>ולידציה</h2>
<pre><code>from pydantic import BaseModel, Field, field_validator

class MatchRow(BaseModel):
    match_id: int
    home_goals: int = Field(ge=0, le=15)
    away_goals: int = Field(ge=0, le=15)
    home_id: int
    away_id: int

    @field_validator("away_id")
    @classmethod
    def different_teams(cls, v, info):
        if v == info.data.get("home_id"):
            raise ValueError("team cannot play itself")
        return v</code></pre>
  <p>בודקים סכמה, טווחים, ייחודיות, ערכים חסרים, ונפח כולל (״20 קבוצות, 380 משחקים בעונה״). רשומות פסולות לא נמחקות בשקט: מעבירים אותן לטבלת הסגר (quarantine) עם סיבת הכישלון.</p>
</section>

<section>
  <h2>תזמון ותזמור</h2>
  <ul>
    <li><strong>cron</strong>: תזמון לפי זמן. הביטוי <code>0 6 * * *</code> פירושו כל יום בשעה 06:00. חמשת השדות הם דקה, שעה, יום בחודש, חודש ויום בשבוע.</li>
    <li><strong>Airflow</strong> (ודומיו Prefect ו־Dagster): הפייפליין מוגדר כ־<strong>DAG</strong>, גרף מכוון בלי מעגלים של משימות עם תלויות. הכלי מטפל ב־retry לכל משימה, בהתראות, ב־backfill ובממשק לניטור.</li>
  </ul>
<pre><code>extract_matches &gt;&gt; validate &gt;&gt; load_postgres &gt;&gt; refresh_league_table</code></pre>
</section>
`,
  tip: "כשמבקשים ״ספר על הפייפליין״, תענה במבנה: מקור, אחר כך תזמון, retry, ולידציה, טעינה אידמפוטנטית, ולבסוף ניטור. המילה ״אידמפוטנטי״ היא מה שמבדיל ג׳וניור שמבין מג׳וניור שהעתיק טוטוריאל.",
  questions: [
    {
      q: "מה פירוש ״פייפליין אידמפוטנטי״?",
      choices: ["פייפליין שרץ מהר", "הרצה חוזרת על אותם נתונים מניבה את אותה תוצאה, בלי כפילויות", "פייפליין שלא נכשל אף פעם", "פייפליין שרץ במקביל"],
      answer: 1,
      explain: "זה מה שמאפשר retry ו־backfill בבטחה. מממשים את זה עם upsert על מפתח טבעי, או החלפה של מחיצה שלמה בטרנזקציה."
    },
    {
      q: "הפייפליין קרס באמצע הטעינה. הרצת אותו שוב, ועכשיו חלק מהמשחקים מופיעים פעמיים. מה התיקון הנכון?",
      choices: ["למחוק כפילויות ידנית בכל פעם", "טעינה עם <code>ON CONFLICT (match_id) DO UPDATE</code> ואילוץ UNIQUE, או טעינה בטרנזקציה אחת", "לא להריץ שוב אחרי קריסה", "להוסיף sleep לפני הטעינה"],
      answer: 1,
      explain: "אילוץ ייחודיות ו־upsert הופכים את הטעינה לאידמפוטנטית. טרנזקציה מבטיחה שקריסה באמצע לא תשאיר נתונים חלקיים."
    },
    {
      q: "מה ההבדל בין ETL ל־ELT?",
      choices: ["אין הבדל", "ב־ELT טוענים את הנתונים הגולמיים ליעד קודם, ומבצעים את הטרנספורמציה בתוכו, בדרך כלל עם SQL", "ב־ELT אין שלב טרנספורמציה", "ETL הוא לנתונים חיים בלבד"],
      answer: 1,
      explain: "שיטת ELT נפוצה במחסני נתונים בענן. היתרון: הנתונים הגולמיים נשמרים, ואפשר להריץ טרנספורמציה מחדש בכל רגע."
    },
    {
      q: "בכל לילה מושכים רק משחקים שהתעדכנו מאז ההרצה הקודמת, לפי <code>max(updated_at)</code>. איך קוראים לזה?",
      choices: ["טעינה מלאה", "טעינה מצטברת עם watermark", "Backfill", "Sharding"],
      answer: 1,
      explain: "ה־watermark הוא הנקודה שבה עצרנו. כדאי לחפוף קצת אחורה, למשל לקחת גם שעה לפני ה־watermark, כדי לא לפספס רשומות שהגיעו באיחור. ה־upsert ידאג שלא ייווצרו כפילויות."
    },
    {
      q: "מה פירוש ביטוי ה־cron <code>0 6 * * *</code>?",
      choices: ["כל 6 דקות", "כל יום בשעה 06:00", "ביום השישי בכל חודש", "כל 6 שעות"],
      answer: 1,
      explain: "חמשת השדות הם דקה, שעה, יום בחודש, חודש ויום בשבוע. כאן הדקה היא 0 והשעה היא 6, וכל השאר כוכבית."
    },
    {
      q: "מה עושים עם רשומה שנכשלה בוולידציה, למשל משחק שבו קבוצה משחקת נגד עצמה?",
      choices: ["מוחקים בשקט", "מעבירים לטבלת הסגר עם סיבת הכישלון, ומתריעים אם יש הרבה כאלה", "טוענים בכל זאת", "עוצרים את הפייפליין לתמיד"],
      answer: 1,
      explain: "מחיקה שקטה מסתירה בעיות במקור. כשל כבד, למשל 50% רשומות פסולות, צריך כן להכשיל את ההרצה."
    },
    {
      q: "מה זה DAG ב־Airflow?",
      choices: ["סוג של מסד נתונים", "גרף מכוון בלי מעגלים של משימות ותלויות ביניהן", "פורמט קובץ", "שפת שאילתות"],
      answer: 1,
      explain: "בלי מעגלים, כי משימה לא יכולה להיות תלויה בעצמה, ישירות או בעקיפין. כך יש תמיד סדר הרצה חוקי."
    },
    {
      q: "הוספת עמודת xG לטבלת המשחקים, ורוצים אותה גם לשלוש העונות הקודמות. איך קוראים לזה?",
      choices: ["Rollback", "Backfill", "Upsert", "Sharding"],
      answer: 1,
      explain: "בפייפליין אידמפוטנטי שמקבל טווח תאריכים כפרמטר, backfill הוא פשוט הרצה על טווח היסטורי."
    }
  ],
  open: [
    { q: "ספר על פייפליין שבנית, מקצה לקצה.", a: "<p>תבנית לפייפליין של לה ליגה: <strong>מקור</strong>, סקרייפינג של דפי משחקים ושחקנים. <strong>תזמון</strong>, cron או Airflow אחרי כל מחזור. <strong>חוסן</strong>, retry עם exponential backoff לשגיאות זמניות. <strong>ולידציה</strong>, סכמה, טווחים ונפח צפוי. <strong>טעינה</strong>, upsert ל־PostgreSQL לפי מזהה המשחק, בתוך טרנזקציה. <strong>סביבה</strong>, הכול ב־Docker כדי שירוץ זהה בכל מקום. תתאים את זה לפרטים האמיתיים שלך.</p>" },
    { q: "מה ההבדל בין עיבוד batch לעיבוד streaming?", a: "<p>בעיבוד batch מעבדים כמות נתונים שהצטברה, בתזמון קבוע, למשל כל לילה. עיבוד streaming מטפל בכל אירוע כשהוא מגיע, תוך שניות, עם כלים כמו Kafka או RabbitMQ. לתוצאות חיות של משחקים צריך streaming. לטבלת ליגה וסטטיסטיקה עונתית batch מספיק, והוא פשוט וזול יותר.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "rest",
  group: "de",
  title: "REST APIs",
  cv: ["REST APIs"],
  usedIn: ["worldcup", "laliga"],
  summary: "גם לצרוך וגם לבנות. ישאלו על מתודות, קודי סטטוס, אידמפוטנטיות ואימות.",
  html: `
<section>
  <h2>עקרונות</h2>
  <ul>
    <li><strong>משאבים</strong> מזוהים ב־URL, בלשון רבים: <code>/matches</code> ו־<code>/matches/42</code>.</li>
    <li><strong>מתודת HTTP</strong> מגדירה את הפעולה על המשאב.</li>
    <li><strong>חסר מצב</strong> (stateless): כל בקשה מכילה את כל מה שהשרת צריך, כולל טוקן אימות. השרת לא זוכר בקשות קודמות, ולכן קל להוסיף שרתים מאחורי load balancer.</li>
    <li>הייצוג הנפוץ הוא <strong>JSON</strong>.</li>
  </ul>
</section>

<section>
  <h2>מתודות</h2>
  <div class="tbl-scroll"><table>
    <tr><th>מתודה</th><th>שימוש</th><th>בטוחה (לא משנה)</th><th>אידמפוטנטית</th></tr>
    <tr><td><code>GET</code></td><td>קריאה</td><td>כן</td><td>כן</td></tr>
    <tr><td><code>POST</code></td><td>יצירה, או פעולה כללית</td><td>לא</td><td><strong>לא</strong></td></tr>
    <tr><td><code>PUT</code></td><td>החלפה מלאה של משאב</td><td>לא</td><td>כן</td></tr>
    <tr><td><code>PATCH</code></td><td>עדכון חלקי</td><td>לא</td><td>לא מובטח</td></tr>
    <tr><td><code>DELETE</code></td><td>מחיקה</td><td>לא</td><td>כן</td></tr>
  </table></div>
  <p>אידמפוטנטי אומר ששליחה של אותה בקשה פעמיים משאירה את השרת באותו מצב כמו שליחה אחת. לכן בטוח לנסות שוב PUT או DELETE אחרי timeout. POST כפול יכול ליצור שתי רשומות. הפתרון המקובל הוא כותרת <code>Idempotency-Key</code>.</p>
</section>

<section>
  <h2>קודי סטטוס</h2>
  <div class="tbl-scroll"><table>
    <tr><th>קוד</th><th>משמעות</th><th>לנסות שוב?</th></tr>
    <tr><td><code>200</code> / <code>201</code> / <code>204</code></td><td>הצלחה / נוצר משאב / הצלחה בלי תוכן</td><td>לא צריך</td></tr>
    <tr><td><code>400</code></td><td>הבקשה לא תקינה</td><td>לא, צריך לתקן את הבקשה</td></tr>
    <tr><td><code>401</code></td><td>לא מאומת: אין טוקן, או שהטוקן לא תקף</td><td>רק אחרי חידוש הטוקן</td></tr>
    <tr><td><code>403</code></td><td>מאומת, אבל אין הרשאה</td><td>לא</td></tr>
    <tr><td><code>404</code></td><td>המשאב לא נמצא</td><td>לא</td></tr>
    <tr><td><code>429</code></td><td>יותר מדי בקשות</td><td>כן, אחרי המתנה</td></tr>
    <tr><td><code>500</code> / <code>502</code> / <code>503</code></td><td>שגיאת שרת או שירות לא זמין</td><td>כן, עם backoff</td></tr>
  </table></div>
</section>

<section>
  <h2>צריכת API</h2>
<pre><code>resp = session.get(
    "https://api.example.com/v1/fixtures",
    params={"league": 140, "season": 2025, "page": 1},   # פרמטרים של query
    headers={"Authorization": f"Bearer {API_TOKEN}"},     # הטוקן מגיע ממשתנה סביבה, לא מהקוד
    timeout=10,
)
resp.raise_for_status()
data = resp.json()</code></pre>
  <p>פרמטר <strong>בנתיב</strong> מזהה משאב (<code>/matches/42</code>). פרמטר <strong>ב־query</strong> מסנן, ממיין או מדפדף (<code>?team=barca&amp;page=2</code>). <strong>עימוד</strong> מתבצע לפי <code>page</code> ו־<code>limit</code>, או לפי cursor, שהוא יציב יותר כשנתונים חדשים מתווספים באמצע.</p>
</section>

<section>
  <h2>בניית API עם FastAPI</h2>
<pre><code>from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/matches/{match_id}")
def get_match(match_id: int):              # הטיפוס נבדק אוטומטית, וערך לא תקין מחזיר 422
    row = db.fetch_match(match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="match not found")
    return row                              # מומר ל־JSON אוטומטית

@app.post("/matches", status_code=201)
def create_match(m: MatchIn): ...</code></pre>
</section>
`,
  tip: "ההבחנות שמראיינים בודקים הן 401 מול 403 ו־PUT מול PATCH, ולמה POST לא אידמפוטנטי. אם צרכת API בפרויקט, תזכיר שטיפלת בעימוד, ב־rate limit וב־retry רק על 429 ו־5xx.",
  questions: [
    {
      q: "מה ההבדל בין 401 ל־403?",
      choices: ["אין הבדל", "קוד 401 אומר שלא זוהית (אין טוקן או שהוא לא תקף). קוד 403 אומר שזוהית, אבל אין לך הרשאה", "קוד 401 הוא שגיאת שרת", "קוד 403 אומר שהמשאב לא קיים"],
      answer: 1,
      explain: "השם הרשמי של 401 הוא Unauthorized, אבל בפועל המשמעות היא Unauthenticated. 403 Forbidden פירושו ״אני יודע מי אתה, והתשובה היא לא״."
    },
    {
      q: "איזו מתודה <strong>אינה</strong> אידמפוטנטית?",
      choices: ["<code>GET</code>", "<code>PUT</code>", "<code>POST</code>", "<code>DELETE</code>"],
      answer: 2,
      explain: "שתי בקשות POST זהות יכולות ליצור שני משאבים. PUT מחליף את המשאב באותו ערך, ולכן הרצה כפולה זהה לאחת."
    },
    {
      q: "צריך לעדכן רק את מספר הקהל במשחק, בלי לשלוח את כל האובייקט. איזו מתודה?",
      choices: ["<code>PUT</code>", "<code>PATCH</code>", "<code>GET</code>", "<code>POST</code>"],
      answer: 1,
      explain: "המתודה PATCH מיועדת לעדכון חלקי. PUT מחליפה את המשאב כולו, ושדות שלא נשלחו עלולים להתאפס."
    },
    {
      q: "יצרת משאב חדש בהצלחה עם POST. מה קוד הסטטוס המתאים?",
      choices: ["<code>200</code>", "<code>201</code>", "<code>204</code>", "<code>202</code>"],
      answer: 1,
      explain: "הקוד 201 Created, בדרך כלל עם כותרת Location שמצביעה למשאב החדש. הקוד 202 Accepted אומר שהבקשה התקבלה ותטופל מאוחר יותר."
    },
    {
      q: "על אילו שגיאות הגיוני לנסות שוב אוטומטית?",
      choices: ["400 ו־404", "429, 502, 503 ו־timeout", "401 ו־403", "על כל שגיאה"],
      answer: 1,
      explain: "שגיאות 4xx (חוץ מ־429) הן בעיה בבקשה, וניסיון חוזר יחזיר את אותה שגיאה. שגיאות 5xx ו־429 הן לרוב זמניות."
    },
    {
      q: "מה פירוש ״REST הוא stateless״?",
      choices: ["אין מסד נתונים", "כל בקשה מכילה את כל המידע הנדרש, כולל אימות, והשרת לא שומר מצב סשן בין בקשות", "אי אפשר לשנות נתונים", "אין עוגיות"],
      answer: 1,
      explain: "בזכות זה כל שרת יכול לטפל בכל בקשה, וקל להוסיף שרתים. המשאבים עצמם כמובן שמורים במסד הנתונים."
    },
    {
      q: "איך נכון לבנות URL לסינון משחקים של קבוצה מסוימת בעונה מסוימת?",
      choices: ["<code>/getMatchesForTeam?id=5</code>", "<code>/matches?team=5&amp;season=2025</code>", "<code>/matches/team/5/season/2025/get</code>", "<code>POST /matches/search</code> תמיד"],
      answer: 1,
      explain: "משאב בלשון רבים, וסינון בפרמטרים של query. בלי פעלים ב־URL, כי הפועל הוא מתודת ה־HTTP."
    }
  ],
  open: [
    { q: "איך היית מתמודד עם API שמגביל ל־100 בקשות בדקה?", a: "<p>מגביל קצב בצד הלקוח, למשל token bucket, כדי לא לעבור את המגבלה מלכתחילה. מטמון לתשובות שלא משתנות, כמו משחקים שהסתיימו. בקשות מרוכזות אם ה־API תומך בכך. ואם בכל זאת מגיע 429, מכבדים את Retry-After ומנסים שוב עם backoff.</p>" },
    { q: "איך שומרים מפתח API בפרויקט?", a: "<p>במשתנה סביבה או במנהל סודות, אף פעם לא בקוד ולא ב־Git. בפיתוח משתמשים בקובץ <code>.env</code> שנמצא ב־<code>.gitignore</code>, ובפרודקשן מעבירים אותו כמשתנה ל־Docker או דרך GitHub Secrets.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "postgres",
  group: "de",
  title: "PostgreSQL",
  cv: ["PostgreSQL"],
  usedIn: ["laliga"],
  summary: "מסד הנתונים של הפייפליין של לה ליגה. מעבר ל־SQL ישאלו על תכנון סכמה, אינדקסים, טרנזקציות ו־ACID.",
  html: `
<section>
  <h2>תכנון סכמה</h2>
<pre><code>CREATE TABLE teams (
    team_id   INT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE
);

CREATE TABLE matches (
    match_id    BIGINT PRIMARY KEY,                       -- המזהה מהמקור, מפתח טבעי
    kickoff     TIMESTAMPTZ NOT NULL,                     -- תמיד עם אזור זמן
    home_id     INT NOT NULL REFERENCES teams(team_id),   -- מפתח זר
    away_id     INT NOT NULL REFERENCES teams(team_id),
    home_goals  SMALLINT CHECK (home_goals &gt;= 0),
    away_goals  SMALLINT CHECK (away_goals &gt;= 0),
    raw         JSONB,                                    -- התגובה הגולמית, עם אפשרות לשאילתות
    CHECK (home_id &lt;&gt; away_id)
);</code></pre>
  <ul>
    <li><strong>מפתח ראשי</strong>: ייחודי ולא NULL, ומזהה כל שורה.</li>
    <li><strong>מפתח זר</strong>: מבטיח שלמות הפניות. אי אפשר להכניס משחק של קבוצה שלא קיימת.</li>
    <li><strong>נרמול</strong>: כל עובדה נשמרת במקום אחד. שם הקבוצה נמצא רק בטבלת teams, ולא משוכפל בכל משחק.</li>
    <li><code>TIMESTAMPTZ</code> שומר נקודת זמן מוחלטת ב־UTC. זה חשוב כשמשחקים מתקיימים באזורי זמן שונים.</li>
    <li><code>JSONB</code> הוא JSON בפורמט בינארי שאפשר לבנות עליו אינדקס ולשאול עליו. סוג <code>JSON</code> רגיל שומר טקסט כמו שהוא.</li>
  </ul>
</section>

<section>
  <h2>ACID וטרנזקציות</h2>
  <ul>
    <li><strong>אטומיות</strong> (Atomicity): הכול או כלום. אם שלב אחד בטרנזקציה נכשל, הכול מתבטל.</li>
    <li><strong>עקביות</strong> (Consistency): אחרי הטרנזקציה כל האילוצים עדיין מתקיימים.</li>
    <li><strong>בידוד</strong> (Isolation): טרנזקציות מקבילות לא רואות זו את המצב החלקי של זו.</li>
    <li><strong>עמידות</strong> (Durability): אחרי COMMIT, הנתונים שורדים גם קריסה.</li>
  </ul>
<pre><code>BEGIN;
DELETE FROM player_stats WHERE match_id = 42;
INSERT INTO player_stats ... ;   -- אם זה נכשל, גם המחיקה מתבטלת
COMMIT;</code></pre>
  <p>PostgreSQL מממש בידוד בעזרת <strong>MVCC</strong>: כל טרנזקציה רואה תמונת מצב (snapshot), כך שקוראים לא חוסמים כותבים ולהפך.</p>
</section>

<section>
  <h2>אינדקסים</h2>
  <p>אינדקס (בדרך כלל <strong>B-tree</strong>) הוא מבנה ממוין שמאפשר למצוא שורות בלי לסרוק את כל הטבלה, כמו אינדקס בסוף ספר.</p>
<pre><code>CREATE INDEX idx_matches_home_kickoff ON matches (home_id, kickoff);

EXPLAIN ANALYZE
SELECT * FROM matches WHERE home_id = 7 AND kickoff &gt; '2025-08-01';
-- Seq Scan       = סריקה של כל הטבלה. על טבלה גדולה, סימן לאינדקס חסר
-- Index Scan     = שימוש באינדקס</code></pre>
  <ul>
    <li>האינדקס מאיץ קריאה, אבל <strong>מאט כתיבה</strong>, כי כל INSERT ו־UPDATE צריך לעדכן גם אותו. הוא גם תופס מקום בדיסק.</li>
    <li>אינדקס מורכב <code>(home_id, kickoff)</code> עוזר לשאילתות על <code>home_id</code> לבד, או על שני השדות יחד. הוא לא עוזר לשאילתה על <code>kickoff</code> לבד. זה כלל <strong>הקידומת השמאלית</strong>.</li>
    <li>אינדקס על עמודה עם מעט ערכים שונים, למשל עמודה בוליאנית, כמעט לא עוזר.</li>
  </ul>
</section>

<section>
  <h2>חיבור מ־Python, ו־SQL injection</h2>
<pre><code>import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"])
with conn, conn.cursor() as cur:            # with conn: commit בהצלחה, rollback בשגיאה
    cur.execute("SELECT * FROM players WHERE name = %s", (name,))   # נכון: שאילתה עם פרמטרים
    # cur.execute(f"SELECT * FROM players WHERE name = '{name}'")    # פגיע ל־SQL injection</code></pre>
  <p>שם כמו <code>O'Brien</code> ישבור שאילתה שנבנתה משרשור מחרוזות, וקלט זדוני יכול להריץ פקודות. שאילתה עם פרמטרים שולחת את הערך בנפרד מהקוד של השאילתה.</p>
</section>
`,
  tip: "ספר על הסכמה שלך: אילו טבלאות, מה המפתח הטבעי של משחק, ואיך ה־upsert על match_id הופך את הפייפליין לאידמפוטנטי. אם ישאלו ״השאילתה איטית, מה תעשה?״, התשובה מתחילה ב־EXPLAIN ANALYZE ולא בניחוש.",
  questions: [
    {
      q: "פייפליין מוחק את הסטטיסטיקות של משחק ומכניס אותן מחדש. ההכנסה נכשלה באמצע. איזה עיקרון ב־ACID מונע מצב שבו הנתונים נמחקו ולא הוכנסו חזרה?",
      choices: ["עמידות (Durability)", "אטומיות (Atomicity), בתנאי ששתי הפעולות נמצאות באותה טרנזקציה", "בידוד (Isolation)", "נרמול"],
      answer: 1,
      explain: "בתוך טרנזקציה אחת, הכישלון גורם ל־ROLLBACK, והמחיקה מתבטלת. בלי טרנזקציה, כל פקודה מתבצעת מיד, ואתה נשאר בלי נתונים."
    },
    {
      q: "מה החיסרון של הוספת אינדקס?",
      choices: ["הוא מאט קריאות", "הוא מאט כתיבות (INSERT, UPDATE, DELETE) ותופס מקום בדיסק", "הוא מוחק כפילויות", "אין חסרונות"],
      answer: 1,
      explain: "כל שינוי בטבלה מחייב עדכון של כל האינדקסים עליה. לכן לא מוסיפים אינדקס על כל עמודה, אלא רק לפי השאילתות שבאמת רצות."
    },
    {
      q: "יש אינדקס מורכב על <code>(home_id, kickoff)</code>. איזו שאילתה <strong>לא</strong> תיהנה ממנו?",
      choices: ["<code>WHERE home_id = 7</code>", "<code>WHERE home_id = 7 AND kickoff &gt; '2025-08-01'</code>", "<code>WHERE kickoff &gt; '2025-08-01'</code>", "<code>WHERE home_id IN (7, 8)</code>"],
      answer: 2,
      explain: "האינדקס ממוין קודם לפי home_id. בלי תנאי על העמודה הראשונה אי אפשר להשתמש בו ביעילות. זה כלל הקידומת השמאלית."
    },
    {
      q: "איך מונעים SQL injection ב־Python?",
      choices: ["בריחה ידנית של גרשיים", "שאילתה עם פרמטרים: <code>cur.execute(\"... WHERE name = %s\", (name,))</code>", "f-string עם בדיקת אורך", "המרה של הקלט לאותיות קטנות"],
      answer: 1,
      explain: "הדרייבר שולח את הערך בנפרד מקוד השאילתה, ולכן קלט אף פעם לא יתפרש כ־SQL. בריחה ידנית תמיד מפספסת מקרה כלשהו."
    },
    {
      q: "ב־<code>EXPLAIN ANALYZE</code> של שאילתה איטית מופיע <code>Seq Scan on matches</code>, על טבלה של 5 מיליון שורות עם סינון לפי עמודה אחת. מה הצעד הסביר?",
      choices: ["להגדיל את השרת", "ליצור אינדקס על העמודה שלפיה מסננים", "למחוק נתונים ישנים", "להמיר ל־MongoDB"],
      answer: 1,
      explain: "סריקה מלאה של טבלה גדולה עבור סינון סלקטיבי היא סימן קלאסי לאינדקס חסר. אחרי שמוסיפים אותו, מריצים EXPLAIN שוב ומוודאים שמופיע Index Scan."
    },
    {
      q: "מה התפקיד של מפתח זר (<code>REFERENCES teams(team_id)</code>)?",
      choices: ["להאיץ שאילתות", "להבטיח שכל home_id במשחקים מפנה לקבוצה שקיימת בטבלת teams", "ליצור אינדקס אוטומטית", "למנוע ערכים כפולים"],
      answer: 1,
      explain: "זו שלמות הפניות. שים לב: ב־PostgreSQL מפתח זר <strong>לא</strong> יוצר אינדקס אוטומטית על העמודה המפנה, ולעיתים קרובות כדאי ליצור אותו ידנית."
    },
    {
      q: "מה ההבדל בין <code>JSONB</code> ל־<code>JSON</code> ב־PostgreSQL?",
      choices: ["אין הבדל", "JSONB נשמר בפורמט בינארי מפורק: אפשר לבנות עליו אינדקס GIN, והשאילתות מהירות. JSON שומר את הטקסט כמו שהוא", "סוג JSON מהיר יותר בשאילתות", "סוג JSONB לא תומך במערכים"],
      answer: 1,
      explain: "כמעט תמיד בוחרים JSONB. סוג JSON רלוונטי רק כשחייבים לשמור על סדר מפתחות או על רווחים בדיוק כמו במקור."
    },
    {
      q: "למה לשמור זמן פתיחת משחק כ־<code>TIMESTAMPTZ</code> ולא כ־<code>TIMESTAMP</code>?",
      choices: ["הוא תופס פחות מקום", "הוא מייצג נקודת זמן מוחלטת (נשמרת ב־UTC), כך שמשחקים מאזורי זמן שונים ומעברי שעון קיץ מושווים נכון", "אין הבדל", "רק הוא תומך בתאריכים"],
      answer: 1,
      explain: "סוג TIMESTAMP בלי אזור זמן הוא רק ״שעה על שעון קיר״. כשמשלבים מקורות ממדינות שונות זה מוביל לטעויות של שעות."
    }
  ],
  open: [
    { q: "שאילתה שהייתה מהירה הפכה לאיטית. איך תחקור?", a: "<p>מריצים <code>EXPLAIN ANALYZE</code> ובודקים: האם יש Seq Scan במקום שצפוי Index Scan? האם הערכת מספר השורות רחוקה מהמספר בפועל? אם כן, הסטטיסטיקות ישנות ומריצים <code>ANALYZE</code>. אחר כך בודקים אינדקס חסר או אינדקס שלא מתאים לסדר העמודות, פונקציה על עמודה שמבטלת את השימוש באינדקס, נעילות מטרנזקציות ארוכות, וטבלה שתפחה ממחיקות (VACUUM).</p>" },
    { q: "למה בחרת PostgreSQL לפייפליין של לה ליגה ו־MongoDB לפייפליין של המונדיאל?", a: "<p>לנתוני משחקים ושחקנים יש מבנה קבוע וקשרים ברורים: משחק, קבוצה, שחקן. רציתי JOIN, מפתחות זרים ואילוצים כדי לשמור על איכות הנתונים, ולכן PostgreSQL. פוסטים מרשתות חברתיות מגיעים כ־JSON במבנים משתנים, בנפח כתיבה גבוה, ונקראים בעיקר בשלמותם, ולכן MongoDB התאים יותר.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "mongodb",
  group: "de",
  title: "MongoDB",
  cv: ["MongoDB"],
  usedIn: ["worldcup"],
  summary: "מסד מסמכים, והבסיס של פייפליין המונדיאל. ישאלו למה Mongo ולא SQL, על embedding ועל ה־aggregation pipeline.",
  html: `
<section>
  <h2>המודל: מסמכים ואוספים</h2>
  <p>במקום טבלאות ושורות יש <strong>אוספים</strong> (collections) של <strong>מסמכים</strong>, שהם אובייקטים דמויי JSON שנשמרים בפורמט BSON. לכל מסמך יש שדה <code>_id</code> ייחודי, ובברירת מחדל זה <code>ObjectId</code>, שכולל בתוכו גם חותמת זמן. הסכמה <strong>גמישה</strong>: לכל מסמך באוסף יכולים להיות שדות שונים.</p>
<pre><code>{
  "_id": ObjectId("6650..."),
  "tweet_id": "1803...",
  "fixture_id": 1032,
  "created_at": ISODate("2026-06-17T19:42:10Z"),
  "text": "What a goal by Messi!!",
  "lang": "en",
  "user": { "followers": 1520, "verified": false },     // מסמך מוטמע
  "hashtags": ["ARGALG", "WorldCup"],                    // מערך
  "sentiment": { "label": "positive", "score": 0.93 }
}</code></pre>
</section>

<section>
  <h2>שאילתות</h2>
<pre><code>from pymongo import MongoClient, UpdateOne
db = MongoClient(os.environ["MONGO_URI"]).worldcup

db.posts.find({"fixture_id": 1032, "user.followers": {"$gt": 10_000}},
              {"text": 1, "created_at": 1})          # הארגומנט השני הוא projection
db.posts.find({"hashtags": {"$in": ["ARGALG"]}}).sort("created_at", -1).limit(50)

# אינדקס ייחודי + upsert = בלי כפילויות גם כשאוספים את אותו פוסט פעמיים
db.posts.create_index("tweet_id", unique=True)
db.posts.bulk_write([UpdateOne({"tweet_id": p["tweet_id"]}, {"$set": p}, upsert=True) for p in batch],
                    ordered=False)</code></pre>
</section>

<section>
  <h2>ה־aggregation pipeline</h2>
  <p>רצף של שלבים שכל אחד מקבל את המסמכים מהשלב הקודם, בדומה לצינור של פקודות ב־Unix. זה המקביל של GROUP BY ו־JOIN ב־SQL.</p>
<pre><code>db.posts.aggregate([
  {"$match": {"fixture_id": 1032}},                              # לסנן מוקדם, כדי להשתמש באינדקס
  {"$group": {
      "_id": {"$dateTrunc": {"date": "$created_at", "unit": "minute"}},
      "posts": {"$sum": 1},
      "avg_sentiment": {"$avg": "$sentiment.score"}}},
  {"$sort": {"_id": 1}},
])
# התוצאה: נפח פוסטים וסנטימנט ממוצע לכל דקה. הקפיצות מתיישרות עם הגולים</code></pre>
  <p>השלב <code>$lookup</code> הוא המקביל של LEFT JOIN, אבל אם צריך אותו כל הזמן, זה סימן שהמודל לא מתאים לגישות שלך.</p>
</section>

<section>
  <h2>להטמיע או להפנות</h2>
  <ul>
    <li><strong>הטמעה</strong> (embedding): כשהנתונים נקראים יחד ושייכים לאב אחד, למשל פרטי המשתמש בתוך הפוסט. קריאה אחת מחזירה הכול.</li>
    <li><strong>הפניה</strong> (reference): כשתת־הרשימה גדלה בלי גבול, כמו מיליון תגובות לפוסט (מסמך מוגבל ל־16MB), או כשהנתון משותף לרבים ומתעדכן.</li>
  </ul>
  <p>כלל האצבע: <strong>מתכננים לפי השאילתות</strong>, ולא לפי הישויות כמו ב־SQL.</p>
</section>

<section>
  <h2>קנה מידה</h2>
  <ul>
    <li><strong>Replica set</strong>: שרת ראשי ומשניים עם עותקים. כך יש שרידות ואפשר לפזר קריאות.</li>
    <li><strong>Sharding</strong>: חלוקה אופקית של אוסף בין כמה שרתים לפי <strong>shard key</strong>. בחירה גרועה, למשל מפתח שעולה כל הזמן כמו זמן יצירה, תיצור shard ״חם״ שמקבל את כל הכתיבות.</li>
    <li>אינדקס TTL מוחק מסמכים ישנים אוטומטית, וזה שימושי ללוגים ולנתונים זמניים.</li>
  </ul>
</section>
`,
  tip: "השאלה ״למה Mongo?״ כמעט בטוחה. התשובה: ״פוסטים מרשתות חברתיות מגיעים כ־JSON מקונן במבנים משתנים, בנפח כתיבה גבוה סביב כל משחק, ונקראים כמסמך שלם. רציתי לשמור אותם כמו שהם בלי סכמה קשיחה, ואת הניתוח לפי דקה עשיתי ב־aggregation pipeline״.",
  questions: [
    {
      q: "למה MongoDB התאים לאיסוף פוסטים מרשתות חברתיות?",
      choices: ["כי הוא תומך ב־JOIN טוב יותר מ־SQL", "כי הנתונים הם JSON מקונן עם מבנה משתנה, בנפח כתיבה גבוה, ונקראים כמסמך שלם", "כי הוא תמיד מהיר יותר מ־PostgreSQL", "כי אין בו אינדקסים"],
      answer: 1,
      explain: "סכמה גמישה ומסמכים שלמים מתאימים לנתונים כאלה. MongoDB לא ״תמיד מהיר יותר״, וזו תשובה שמראיינים לא אוהבים."
    },
    {
      q: "אילו מסמכים מחזירה השאילתה <code>{\"likes\": {\"$gt\": 100}}</code>?",
      choices: ["כאלה עם בדיוק 100 לייקים", "כאלה עם יותר מ־100 לייקים", "כאלה עם 100 לייקים או פחות", "את כל המסמכים, ממוינים לפי לייקים"],
      answer: 1,
      explain: "האופרטור gt הוא greater than. יש גם gte, lt, lte, ne ו־in."
    },
    {
      q: "ב־aggregation pipeline, איפה כדאי לשים את <code>$match</code>?",
      choices: ["בסוף", "כמה שיותר מוקדם, כדי לצמצם מסמכים ולהשתמש באינדקס", "לא משנה", "רק אחרי $group"],
      answer: 1,
      explain: "שלב match בתחילת הצינור יכול להשתמש באינדקס, וכל השלבים הבאים מעבדים פחות מסמכים."
    },
    {
      q: "לכל פוסט יכולות להיות מאות אלפי תגובות. איך כדאי לשמור אותן?",
      choices: ["כמערך מוטמע בתוך מסמך הפוסט", "באוסף נפרד, שבו כל תגובה מפנה ל־post_id", "בשדה טקסט אחד", "בקובץ CSV"],
      answer: 1,
      explain: "מסמך מוגבל ל־16MB, ומערך שגדל בלי גבול גם פוגע בביצועים. הטמעה מתאימה לנתונים קטנים וחסומים."
    },
    {
      q: "הסקרייפר אוסף לפעמים את אותו פוסט פעמיים. איך מונעים כפילויות?",
      choices: ["בודקים ב־Python לפני כל הכנסה", "אינדקס ייחודי על tweet_id, וכתיבה עם upsert", "מוחקים כפילויות פעם בשבוע", "MongoDB מונע את זה אוטומטית"],
      answer: 1,
      explain: "אינדקס ייחודי הוא ההגנה ברמת המסד, ו־upsert הופך את הטעינה לאידמפוטנטית, בדיוק כמו ON CONFLICT ב־PostgreSQL."
    },
    {
      q: "מה המקביל של JOIN ב־MongoDB?",
      choices: ["<code>$group</code>", "<code>$lookup</code>", "<code>$unwind</code>", "אין דבר כזה"],
      answer: 1,
      explain: "השלב lookup מבצע מעין LEFT JOIN לאוסף אחר. אם צריך אותו בכל שאילתה, כנראה שעדיף להטמיע את הנתונים, או ש־SQL מתאים יותר."
    },
    {
      q: "מה זה sharding?",
      choices: ["גיבוי", "חלוקה אופקית של הנתונים בין כמה שרתים לפי shard key", "דחיסה", "אינדקס מיוחד"],
      answer: 1,
      explain: "זו הדרך לגדול מעבר לשרת אחד. צריך לבחור shard key עם פיזור טוב. replica set, לעומת זאת, הוא שכפול לשרידות."
    }
  ],
  open: [
    { q: "מתי לא היית בוחר MongoDB?", a: "<p>כשהנתונים יחסיים במהותם ויש הרבה צירופים, כשצריך טרנזקציות מורכבות על כמה ישויות (MongoDB תומך בזה, אבל זה פחות טבעי), או כשצריך שאילתות אד־הוק ודוחות BI ש־SQL עושה טוב. טבלת ליגה עם קבוצות, משחקים ושחקנים היא דוגמה קלאסית ל־PostgreSQL.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "docker",
  group: "de",
  title: "Docker",
  cv: ["Docker"],
  usedIn: ["laliga"],
  summary: "הפייפליין של לה ליגה רץ ב־Docker. ישאלו מה ההבדל בין image ל־container, איך כותבים Dockerfile טוב, ואיך עובד docker compose.",
  html: `
<section>
  <h2>המושגים</h2>
  <ul>
    <li><strong>Image</strong>: תבנית לקריאה בלבד שבנויה משכבות, וכוללת מערכת קבצים, תלויות ופקודת הרצה. בדומה למחלקה.</li>
    <li><strong>Container</strong>: מופע רץ של image, עם שכבה כתיבה דקה משלו. בדומה לאובייקט. כשמוחקים אותו, כל מה שנכתב בתוכו נמחק.</li>
    <li><strong>Registry</strong>: מאגר של images, כמו Docker Hub או GHCR.</li>
    <li><strong>לעומת מכונה וירטואלית</strong>: container חולק את הקרנל של המארח, ולכן הוא עולה בשניות ושוקל מגה־בייטים. מכונה וירטואלית מריצה מערכת הפעלה שלמה.</li>
  </ul>
</section>

<section>
  <h2>Dockerfile טוב</h2>
<pre><code>FROM python:3.12-slim

WORKDIR /app

# קודם רק התלויות: השכבה הזו נשמרת במטמון כל עוד requirements.txt לא השתנה
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# אחר כך הקוד, שמשתנה כל הזמן
COPY . .

ENV PYTHONUNBUFFERED=1
CMD ["python", "-m", "pipeline.run"]</code></pre>
  <ul>
    <li>כל הוראה יוצרת שכבה. אם שכבה השתנתה, כל השכבות שאחריה נבנות מחדש. לכן מעתיקים קודם את מה שמשתנה לעיתים רחוקות.</li>
    <li><code>RUN</code> רץ <strong>בזמן הבנייה</strong>, למשל התקנת חבילות. <code>CMD</code> היא פקודת ברירת המחדל <strong>בזמן ההרצה</strong>.</li>
    <li>קובץ <code>.dockerignore</code> מוציא מה־build את <code>.git</code>, <code>.venv</code>, <code>.env</code> וקבצי נתונים, כדי שה־image יהיה קטן ושסודות לא ייכנסו אליו.</li>
    <li>image בסיס <code>slim</code> במקום הגרסה המלאה. ולמי שרוצה להרשים: multi-stage build.</li>
  </ul>
</section>

<section>
  <h2>הרצה</h2>
<pre><code>docker build -t laliga-pipeline .
docker run --rm \
  -e DATABASE_URL="postgresql://..." \
  -v "$(pwd)/raw:/app/raw" \
  -p 8501:8501 \
  laliga-pipeline
# -e      = משתנה סביבה
# -v      = volume: תיקייה במארח שממופה לתיקייה בתוך ה־container
# -p a:b  = פורט a במארח מופנה לפורט b ב־container</code></pre>
</section>

<section>
  <h2>docker compose</h2>
<pre><code>services:
  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: example
    volumes:
      - pgdata:/var/lib/postgresql/data   # בלי volume, הנתונים נמחקים עם ה־container
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s

  pipeline:
    build: .
    environment:
      DATABASE_URL: postgresql://postgres:example@db:5432/postgres   # השם db, לא localhost
    depends_on:
      db:
        condition: service_healthy

volumes:
  pgdata:</code></pre>
  <p>כל השירותים ב־compose נמצאים באותה רשת, ומגיעים זה לזה <strong>לפי שם השירות</strong>. בתוך ה־container, <code>localhost</code> מצביע על ה־container עצמו.</p>
</section>
`,
  tip: "המשפט שהכי שווה: ״ה־Docker נתן לי סביבה זהה במחשב שלי ובשרת, ו־compose הרים את PostgreSQL ואת הפייפליין יחד, עם volume כדי שהנתונים ישרדו״. אם ישאלו ״למה ה־build איטי?״, תדבר על סדר השכבות ועל ה־cache.",
  questions: [
    {
      q: "מה ההבדל בין image ל־container?",
      choices: ["אין הבדל", "ה־image הוא תבנית לקריאה בלבד, וה־container הוא מופע רץ שלה", "ה־container הוא קובץ, וה־image הוא תהליך", "ה־image רץ בענן, וה־container מקומי"],
      answer: 1,
      explain: "מאותו image אפשר להריץ הרבה containers. האנלוגיה המקובלת: מחלקה ואובייקט."
    },
    {
      q: "למה מעתיקים את <code>requirements.txt</code> ומריצים <code>pip install</code> לפני <code>COPY . .</code>?",
      choices: ["כי Docker דורש את זה", "כדי ששכבת ההתקנה תישמר במטמון: שינוי קוד לא יגרום להתקנה מחדש של כל החבילות", "כדי שה־image יהיה קטן יותר", "כדי שהקוד ירוץ מהר יותר"],
      answer: 1,
      explain: "שינוי בשכבה מבטל את המטמון של כל השכבות שאחריה. אם הקוד מועתק קודם, כל שינוי בשורה אחת יריץ pip install מחדש."
    },
    {
      q: "הרצת PostgreSQL ב־container, מחקת אותו והרמת חדש, וכל הטבלאות נעלמו. למה?",
      choices: ["באג ב־PostgreSQL", "הנתונים נכתבו לשכבה הכתיבה של ה־container, שנמחקת איתו. צריך volume", "צריך להריץ docker commit", "ה־image פגום"],
      answer: 1,
      explain: "volume, בשם או כמיפוי לתיקייה, שומר את הנתונים מחוץ למחזור החיים של ה־container."
    },
    {
      q: "ב־docker compose, שירות הפייפליין מנסה להתחבר ל־<code>localhost:5432</code> ונכשל. מה הבעיה?",
      choices: ["הפורט שגוי", "בתוך container, localhost הוא ה־container עצמו. צריך להתחבר לשם השירות, <code>db:5432</code>", "צריך להוסיף -p", "PostgreSQL לא תומך ב־Docker"],
      answer: 1,
      explain: "ב־compose יש DNS פנימי לפי שם השירות. מיפוי פורטים עם -p רלוונטי רק לגישה מהמארח."
    },
    {
      q: "מה פירוש <code>-p 8080:80</code>?",
      choices: ["פורט 8080 ב־container ממופה לפורט 80 במארח", "פורט 8080 במארח ממופה לפורט 80 ב־container", "שני הפורטים פתוחים ב־container", "הגבלת זיכרון"],
      answer: 1,
      explain: "הסדר הוא host:container. גולשים ל־localhost:8080 במחשב ומגיעים לשירות שמאזין על פורט 80 בתוך ה־container."
    },
    {
      q: "מה ההבדל בין <code>RUN</code> ל־<code>CMD</code> ב־Dockerfile?",
      choices: ["אין הבדל", "RUN רץ בזמן בניית ה־image ויוצר שכבה. CMD היא פקודת ברירת המחדל כשה־container עולה", "CMD רץ בזמן הבנייה", "RUN רץ רק ב־Linux"],
      answer: 1,
      explain: "RUN משמש להתקנות ולהכנות. CMD מגדירה מה רץ בפועל, ואפשר לדרוס אותה בפקודת docker run."
    },
    {
      q: "למה container עולה מהר בהרבה ממכונה וירטואלית?",
      choices: ["כי הוא כתוב ב־Go", "כי הוא חולק את הקרנל של המארח ולא מאתחל מערכת הפעלה שלמה", "כי אין לו מערכת קבצים", "הוא לא באמת מהיר יותר"],
      answer: 1,
      explain: "ה־container הוא תהליך מבודד (namespaces ו־cgroups) על אותו קרנל. מכונה וירטואלית מדמה חומרה ומריצה קרנל משלה."
    }
  ],
  open: [
    { q: "למה בכלל להשתמש ב־Docker לפייפליין?", a: "<p>סביבה זהה בכל מקום, כך שמה שעובד אצלי עובד גם בשרת. התלויות, כולל גרסת Python וספריות מערכת, ארוזות בתוך ה־image. compose מרים את כל המערכת, מסד ופייפליין, בפקודה אחת. וזה גם הבסיס לפריסה בענן או ב־Kubernetes.</p>" },
    { q: "איך היית מקטין image של 1.5GB?", a: "<p>image בסיס slim או alpine, קובץ .dockerignore, <code>--no-cache-dir</code> ב־pip, איחוד פקודות RUN וניקוי באותה שכבה, ו־multi-stage build: שלב אחד בונה עם כלי קומפילציה, ושלב סופי מעתיק רק את התוצרים.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "git",
  group: "de",
  title: "Git",
  cv: ["Git"],
  usedIn: ["laliga", "worldcup", "barca", "xepl"],
  summary: "כולם כותבים Git בקו״ח. ההבדל הוא אם אתה יודע מה ההבדל בין merge ל־rebase, ומה עושים כשדחפת סוד.",
  html: `
<section>
  <h2>שלושת האזורים</h2>
<pre><code>working directory  --git add-->  staging area (index)  --git commit-->  repository
         ^                                                                   |
         +--------------------------- git restore ---------------------------+</code></pre>
  <ul>
    <li><strong>Commit</strong>: תמונת מצב של כל הפרויקט, עם מזהה (hash), הודעה, מחבר ומצביע ל־commit הקודם.</li>
    <li><strong>Branch</strong>: מצביע קל ל־commit, שזז קדימה עם כל commit חדש.</li>
    <li><strong>HEAD</strong>: המצביע ל־branch או ל־commit שאתה נמצא עליו כרגע.</li>
  </ul>
</section>

<section>
  <h2>זרימת העבודה בצוות</h2>
<pre><code>git switch -c feature/retry-logic     # branch חדש מ־main
# ...עבודה...
git add pipeline/fetch.py
git commit -m "Retry transient HTTP errors with exponential backoff"
git push -u origin feature/retry-logic
# פותחים Pull Request, עובר code review ו־CI, ואז מיזוג ל־main</code></pre>
  <p><code>git fetch</code> מוריד את העדכונים מה־remote <strong>בלי לגעת</strong> בקוד שלך. <code>git pull</code> הוא fetch ואחריו merge (או rebase, לפי ההגדרות).</p>
</section>

<section>
  <h2>merge מול rebase</h2>
  <ul>
    <li><strong>merge</strong> יוצר commit מיזוג שמחבר את שני הענפים. ההיסטוריה נשמרת כמו שהייתה, ושום commit לא משתנה.</li>
    <li><strong>rebase</strong> ״מעביר״ את ה־commits שלך כך שיתחילו מקצה ה־main. ההיסטוריה ליניארית ונקייה, אבל <strong>נוצרים commits חדשים עם hash חדש</strong>.</li>
  </ul>
  <p>כלל הזהב: <strong>לא עושים rebase ל־branch שאחרים כבר עובדים עליו</strong>, כי שכתוב ההיסטוריה ישבור להם את העבודה. על branch פרטי שעוד לא שותף, rebase הוא בסדר גמור.</p>
  <p><strong>קונפליקט</strong> קורה כששני הענפים שינו את אותן שורות. Git מסמן את הקטעים עם <code>&lt;&lt;&lt;&lt;&lt;&lt;&lt;</code>, <code>=======</code> ו־<code>&gt;&gt;&gt;&gt;&gt;&gt;&gt;</code>. עורכים ידנית, ואז <code>git add</code> ו־commit (או <code>git rebase --continue</code>).</p>
</section>

<section>
  <h2>ביטול שינויים</h2>
  <div class="tbl-scroll"><table>
    <tr><th>מצב</th><th>פקודה</th></tr>
    <tr><td>לבטל שינוי בקובץ שלא נוסף ל־staging</td><td><code>git restore file.py</code></td></tr>
    <tr><td>להוציא קובץ מ־staging</td><td><code>git restore --staged file.py</code></td></tr>
    <tr><td>לבטל commit שכבר נדחף ל־main משותף</td><td><code>git revert &lt;hash&gt;</code>, שיוצר commit חדש הפוך</td></tr>
    <tr><td>לזרוק commits מקומיים שעוד לא נדחפו</td><td><code>git reset --hard HEAD~1</code></td></tr>
    <tr><td>לשמור עבודה בצד לרגע</td><td><code>git stash</code> ואחר כך <code>git stash pop</code></td></tr>
  </table></div>
  <p><code>revert</code> בטוח על ענף משותף, כי הוא מוסיף היסטוריה. <code>reset</code> משכתב את ההיסטוריה.</p>
</section>

<section>
  <h2>סודות ב־Git</h2>
  <p>קובץ <code>.gitignore</code> מונע מקבצים כמו <code>.env</code>, <code>__pycache__/</code>, <code>.venv/</code> וקבצי נתונים גדולים להיכנס ל־repo. אם סיסמה כבר נדחפה: <strong>קודם כול מחליפים (rotate) את הסוד</strong>, כי הוא כבר נחשף. רק אחרי זה מנקים את ההיסטוריה (<code>git filter-repo</code>), כי מחיקה ב־commit חדש משאירה את הסוד בהיסטוריה.</p>
</section>
`,
  tip: "תראה הרגלים טובים: branch לכל פיצ׳ר, commits קטנים עם הודעות שמסבירות את הסיבה לשינוי, PR עם CI, ו־.env ב־.gitignore. אם יש לך repos ציבוריים ב־GitHub, המראיין אולי יסתכל על היסטוריית ה־commits, אז תדאג שתהיה מסודרת.",
  questions: [
    {
      q: "מה ההבדל בין <code>git fetch</code> ל־<code>git pull</code>?",
      choices: ["אין הבדל", "fetch מוריד עדכונים מה־remote בלי לשנות את ה־branch שלך. pull הוא fetch ואחריו merge או rebase", "pull מעלה שינויים, ו־fetch מוריד", "fetch מוחק branches"],
      answer: 1,
      explain: "fetch בטוח תמיד, ומאפשר לבדוק מה השתנה (למשל עם git log origin/main) לפני המיזוג."
    },
    {
      q: "commit עם באג כבר נדחף ל־main, ושלושה מפתחים משכו אותו. איך מבטלים?",
      choices: ["<code>git reset --hard</code> ו־push --force", "<code>git revert &lt;hash&gt;</code>, שיוצר commit חדש שמבטל את השינוי", "מוחקים את ה־repo", "<code>git stash</code>"],
      answer: 1,
      explain: "פקודת revert לא משכתבת היסטוריה, ולכן היא בטוחה על ענף משותף. reset עם force push ישבור את העבודה של שלושת המפתחים."
    },
    {
      q: "מתי לא עושים rebase?",
      choices: ["על branch מקומי שעוד לא נדחף", "על branch משותף שאחרים כבר עובדים עליו", "לפני פתיחת PR", "אף פעם לא עושים rebase"],
      answer: 1,
      explain: "פקודת rebase יוצרת commits חדשים עם hash אחר. מי שבנה על הישנים יקבל היסטוריה שלא מתיישבת."
    },
    {
      q: "דחפת בטעות קובץ <code>.env</code> עם סיסמת מסד הנתונים ל־repo ציבורי. מה הצעד הראשון?",
      choices: ["למחוק את הקובץ ב־commit חדש", "להחליף מיד את הסיסמה, ואז לנקות את ההיסטוריה ולהוסיף את הקובץ ל־.gitignore", "להפוך את ה־repo לפרטי", "לעשות revert"],
      answer: 1,
      explain: "ברגע שהסוד נדחף, צריך להניח שהוא נחשף. בוטים סורקים את GitHub תוך דקות. מחיקה ב־commit חדש משאירה אותו בהיסטוריה."
    },
    {
      q: "אתה באמצע עבודה, ומבקשים ממך לתקן באג דחוף ב־branch אחר. השינויים שלך עוד לא מוכנים ל־commit. מה עושים?",
      choices: ["<code>git stash</code>, מחליפים branch, מתקנים, חוזרים ומריצים <code>git stash pop</code>", "<code>git reset --hard</code>", "commit עם הודעה ״wip״ ל־main", "מעתיקים את הקבצים לתיקייה אחרת"],
      answer: 0,
      explain: "פקודת stash שומרת את השינויים בצד. גם commit של WIP על ה־branch הפרטי שלך הוא אפשרות לגיטימית, אבל לא על main."
    },
    {
      q: "מה זה merge conflict?",
      choices: ["שגיאת רשת", "שני ענפים שינו את אותן שורות באותו קובץ, ו־Git לא יכול להחליט לבד איזה שינוי לקחת", "branch שנמחק", "commit בלי הודעה"],
      answer: 1,
      explain: "פותרים ידנית: עורכים את האזורים המסומנים, מריצים בדיקות, ואז add ו־commit."
    },
    {
      q: "מה זה <code>HEAD</code>?",
      choices: ["ה־commit הראשון ב־repo", "המצביע למיקום הנוכחי שלך, בדרך כלל ל־branch שעליו אתה נמצא", "ה־branch הראשי", "השרת המרוחק"],
      answer: 1,
      explain: "הסימון HEAD~1 הוא ה־commit שלפני הנוכחי. מצב detached HEAD פירושו ש־HEAD מצביע ישירות ל־commit ולא ל־branch."
    }
  ],
  open: [
    { q: "תאר את זרימת העבודה שלך עם Git.", a: "<p>branch לכל פיצ׳ר מתוך main. commits קטנים עם הודעות שמסבירות את הסיבה. לפני PR אני עושה rebase או merge מ־main ומריץ בדיקות. PR עם תיאור ו־CI, ומיזוג אחרי review. סודות תמיד ב־.env שנמצא ב־.gitignore, ובפרודקשן כמשתני סביבה.</p>" }
  ]
}
);
