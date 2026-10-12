/* CV bootcamp content: Languages (Python, Java, SQL). */
(window.BOOTCAMP_TOPICS = window.BOOTCAMP_TOPICS || []).push(

/* ======================================================================= */
{
  id: "python",
  group: "lang",
  title: "Python",
  cv: ["Python"],
  usedIn: ["laliga", "worldcup", "barca", "xepl"],
  summary: "השפה הראשית שלך. כל ארבעת הפרויקטים כתובים בה, אז ישאלו עליה לעומק: מבני נתונים, פונקציות, חריגות ומקביליות.",
  html: `
<section>
  <h2>מבני הנתונים המובנים</h2>
  <p>ארבעה מבנים שכדאי להכיר בעל־פה, כולל מתי משתמשים בכל אחד ומה המחיר של כל פעולה:</p>
  <div class="tbl-scroll"><table>
    <tr><th>מבנה</th><th>ניתן לשינוי?</th><th>מתי משתמשים</th><th>חיפוש איבר</th></tr>
    <tr><td><code>list</code></td><td>כן</td><td>רצף מסודר, למשל רשימת משחקים</td><td>סריקה מלאה, <code>O(n)</code></td></tr>
    <tr><td><code>tuple</code></td><td>לא</td><td>רשומה קבועה, או מפתח של מילון</td><td>סריקה מלאה, <code>O(n)</code></td></tr>
    <tr><td><code>dict</code></td><td>כן</td><td>מיפוי ממפתח לערך, למשל מזהה שחקן לנתונים</td><td>טבלת גיבוב, <code>O(1)</code> בממוצע</td></tr>
    <tr><td><code>set</code></td><td>כן</td><td>ערכים ייחודיים, למשל מזהים שכבר נאספו</td><td>טבלת גיבוב, <code>O(1)</code> בממוצע</td></tr>
  </table></div>
  <p>בסקרייפר, כדי לבדוק אם משחק כבר נאסף, שומרים את המזהים ב־<code>set</code> ולא ב־<code>list</code>. עם עשרות אלפי מזהים ההבדל מורגש.</p>
</section>

<section>
  <h2>ערכים שניתנים לשינוי, והמלכודת הקלאסית</h2>
  <p>ב־Python משתנה הוא שם שמצביע על אובייקט. כשמעבירים רשימה לפונקציה, הפונקציה מקבלת את <strong>אותו אובייקט</strong>, ולא עותק שלו. מכאן מגיעה המלכודת הכי מפורסמת בראיונות, ערך ברירת מחדל שניתן לשינוי:</p>
<pre><code>def add_goal(scorer, goals=[]):   # הרשימה נוצרת פעם אחת בלבד, בזמן הגדרת הפונקציה
    goals.append(scorer)
    return goals

add_goal("Yamal")
print(add_goal("Lewandowski"))    # ['Yamal', 'Lewandowski']  ← הפתעה

def add_goal(scorer, goals=None): # התיקון המקובל
    if goals is None:
        goals = []
    goals.append(scorer)
    return goals</code></pre>
  <p>עוד הבדל שאוהבים לשאול: האופרטור <code>==</code> בודק שוויון ערכים, והאופרטור <code>is</code> בודק אם זה אותו אובייקט בזיכרון. משווים ל־<code>None</code> עם <code>is</code>.</p>
</section>

<section>
  <h2>קומפרהנשן וגנרטורים</h2>
<pre><code>goals = [s["xg"] for s in shots if s["is_goal"]]      # list comprehension, נבנה מיד בזיכרון
total = sum(s["xg"] for s in shots)                   # generator expression, ערך אחד בכל פעם

def read_matches(path):          # פונקציית גנרטור
    with open(path) as f:
        for line in f:
            yield json.loads(line)   # מחזיר שורה, "מקפיא" את הפונקציה, וממשיך בקריאה הבאה</code></pre>
  <p>גנרטור הוא <strong>עצל</strong>: הוא מחשב כל ערך רק כשמבקשים אותו. כך אפשר לעבור על קובץ של מיליוני ציוצים בלי לטעון את כולו לזיכרון.</p>
</section>

<section>
  <h2>פונקציות ודקורטורים</h2>
  <p>הסימון <code>*args</code> אוסף ארגומנטים לפי מיקום לתוך tuple, והסימון <code>**kwargs</code> אוסף ארגומנטים בעלי שם לתוך dict. דקורטור הוא פונקציה שמקבלת פונקציה ומחזירה גרסה עטופה שלה. זו בדיוק הדרך לממש את ה־<strong>retry logic</strong> שכתבת בקו״ח על הפייפליין של לה ליגה:</p>
<pre><code>import time, functools

def retry(times=3, base_delay=1.0):
    def decorator(fn):
        @functools.wraps(fn)                 # שומר על השם והתיעוד של הפונקציה המקורית
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except requests.RequestException:
                    if attempt == times:
                        raise                # נגמרו הניסיונות, מעבירים את השגיאה הלאה
                    time.sleep(base_delay * 2 ** (attempt - 1))   # המתנה של 1, 2, 4 שניות
        return wrapper
    return decorator

@retry(times=4)
def fetch_match(match_id): ...</code></pre>
</section>

<section>
  <h2>חריגות ומנהלי הקשר</h2>
<pre><code>try:
    data = fetch_match(42)
except requests.Timeout:
    log.warning("timeout")       # תופסים רק את מה שיודעים לטפל בו
else:
    save(data)                    # רץ רק אם לא הייתה חריגה
finally:
    conn.close()                  # רץ תמיד

with open("matches.json") as f:   # with מבטיח שהקובץ ייסגר, גם אם נזרקה חריגה
    matches = json.load(f)</code></pre>
  <p>הרגל רע שאוהבים לתפוס בראיונות הוא <code>except:</code> ריק, כי הוא בולע כל שגיאה ומסתיר באגים.</p>
</section>

<section>
  <h2>ה־GIL, תהליכונים ותהליכים</h2>
  <p>ה־<strong>GIL</strong> (Global Interpreter Lock) הוא מנעול במפרש הסטנדרטי, ולכן רק תהליכון אחד מריץ קוד Python בכל רגע נתון. המשמעות המעשית:</p>
  <ul>
    <li><strong>עבודה שמחכה לרשת או לדיסק</strong>, כמו סקרייפינג או קריאה ל־API: תהליכונים (<code>threading</code>, <code>ThreadPoolExecutor</code>) או <code>asyncio</code> עובדים טוב, כי ה־GIL משתחרר בזמן ההמתנה.</li>
    <li><strong>חישוב כבד על המעבד</strong>, כמו אימון מודל בלולאות Python: צריך תהליכים נפרדים (<code>multiprocessing</code>), או להעביר את החישוב ל־NumPy שרץ ב־C.</li>
  </ul>
</section>

<section>
  <h2>מחלקות וסביבות עבודה</h2>
<pre><code>from dataclasses import dataclass

@dataclass
class Shot:
    player: str
    minute: int
    xg: float
    is_goal: bool = False      # dataclass מייצר לבד __init__, __repr__ ו־__eq__</code></pre>
  <p>לכל פרויקט יוצרים סביבה וירטואלית (<code>python -m venv .venv</code>) ושומרים את התלויות ב־<code>requirements.txt</code>, כדי שהגרסאות לא יתנגשו בין פרויקטים וכדי שה־Docker image ייבנה בדיוק אותו דבר בכל פעם.</p>
</section>
`,
  tip: "כשישאלו על Python, תחבר כל תשובה לקוד שכתבת. במקום להגדיר דקורטור בצורה יבשה, תגיד: ״מימשתי retry עם exponential backoff כדקורטור בפייפליין של לה ליגה, כי האתר החזיר לפעמים timeouts״. תשובה כזו שווה יותר מכל הגדרה.",
  questions: [
    {
      q: "מה יודפס?",
      code: "def add(x, items=[]):\n    items.append(x)\n    return items\n\nadd(1)\nprint(add(2))",
      choices: ["<code>[2]</code>", "<code>[1, 2]</code>", "שגיאת <code>TypeError</code>", "<code>[[1], [2]]</code>"],
      answer: 1,
      explain: "ערך ברירת המחדל נוצר פעם אחת, בזמן הגדרת הפונקציה, וכל הקריאות חולקות את אותה רשימה. התיקון הוא <code>items=None</code> ויצירת רשימה חדשה בתוך הפונקציה."
    },
    {
      q: "יש לך 200 אלף מזהי משחקים שכבר נאספו, ואתה בודק עבור כל משחק חדש אם הוא כבר קיים. באיזה מבנה כדאי להחזיק את המזהים?",
      choices: ["<code>list</code>, כי היא שומרת על הסדר", "<code>set</code>, כי בדיקת שייכות היא O(1) בממוצע", "<code>tuple</code>, כי היא לא ניתנת לשינוי", "זה לא משנה, הביצועים זהים"],
      answer: 1,
      explain: "הבדיקה <code>x in my_set</code> משתמשת בטבלת גיבוב, ולכן היא מהירה. ברשימה אותה בדיקה סורקת את כל האיברים."
    },
    {
      q: "אתה צריך להוריד 500 דפי משחקים מאתר. איזו גישה תאיץ את זה הכי הרבה?",
      choices: ["להשתמש ב־multiprocessing, כי ה־GIL חוסם תהליכונים", "להשתמש בתהליכונים או ב־asyncio, כי רוב הזמן הוא המתנה לרשת וה־GIL משתחרר בזמן הזה", "לולאה רגילה, כי Python לא תומכת במקביליות", "להמיר את הקוד ל־NumPy"],
      answer: 1,
      explain: "זו עבודה שמחכה לרשת (I/O bound). בזמן ההמתנה ה־GIL משתחרר, ולכן תהליכונים או asyncio נותנים האצה גדולה. כדאי לשלב גם הגבלת קצב כדי לא להיחסם."
    },
    {
      q: "מה ההבדל בין <code>[x*x for x in data]</code> לבין <code>(x*x for x in data)</code>?",
      choices: ["אין הבדל, אלה שני סימונים לאותו דבר", "הראשון בונה רשימה שלמה בזיכרון, והשני הוא גנרטור שמחשב ערך אחד בכל פעם", "השני מהיר יותר תמיד", "השני מחזיר tuple"],
      answer: 1,
      explain: "סוגריים עגולים יוצרים generator expression, שהוא עצל וחוסך זיכרון. סוגריים מרובעים בונים רשימה מלאה מיד."
    },
    {
      q: "מה מבטיח בלוק <code>with open(path) as f:</code>?",
      choices: ["שהקובץ ייפתח מהר יותר", "שהקובץ ייסגר בסוף הבלוק, גם אם נזרקה חריגה באמצע", "שהקובץ ייקרא כולו לזיכרון", "שלא ייזרקו חריגות"],
      answer: 1,
      explain: "זהו מנהל הקשר (context manager). הוא קורא ל־<code>__exit__</code> בכל מקרה, ובקובץ זה סוגר את הקובץ. אותו דפוס משמש גם לחיבורים למסד נתונים ולטרנזקציות."
    },
    {
      q: "מה ההבדל בין <code>a == b</code> לבין <code>a is b</code>?",
      choices: ["אין הבדל", "האופרטור == בודק שוויון ערכים, והאופרטור is בודק אם שני השמות מצביעים לאותו אובייקט", "האופרטור is מהיר יותר ולכן עדיף תמיד", "האופרטור == עובד רק על מספרים"],
      answer: 1,
      explain: "שתי רשימות עם אותו תוכן הן שוות לפי ==, אבל הן לא אותו אובייקט לפי is. משתמשים ב־is בעיקר להשוואה ל־None."
    },
    {
      q: "מה מחזיר <code>stats.get(\"assists\", 0)</code> כשהמפתח לא קיים במילון?",
      choices: ["נזרקת שגיאת <code>KeyError</code>", "מוחזר <code>None</code>", "מוחזר <code>0</code>, והמילון לא משתנה", "מוחזר <code>0</code>, והמפתח נוסף למילון"],
      answer: 2,
      explain: "המתודה get מחזירה את ערך ברירת המחדל בלי לשנות את המילון. מי שמוסיף את המפתח הוא <code>setdefault</code>, או <code>defaultdict</code>."
    },
    {
      q: "מה תפקיד <code>functools.wraps</code> בתוך דקורטור?",
      choices: ["הוא מאיץ את הפונקציה העטופה", "הוא מעתיק לפונקציה העוטפת את השם ואת התיעוד של הפונקציה המקורית", "הוא חובה, ובלעדיו הדקורטור לא ירוץ", "הוא תופס חריגות"],
      answer: 1,
      explain: "בלעדיו, הפונקציה המעוטרת תיקרא wrapper בלוגים ובכלי דיבוג. זה לא חובה, אבל זה נחשב לפרקטיקה נכונה."
    }
  ],
  open: [
    { q: "מה זה ה־GIL, ומתי הוא מפריע לך?", a: "<p>מנעול במפרש הסטנדרטי של Python שמאפשר רק לתהליכון אחד להריץ קוד Python בכל רגע. הוא מפריע בחישובים כבדים על המעבד, ושם עוברים ל־multiprocessing או ל־NumPy. בעבודה שמחכה לרשת, כמו הסקרייפרים שלי, הוא כמעט לא מפריע, כי הוא משתחרר בזמן ההמתנה.</p>" },
    { q: "איך היית מממש retry לקריאת רשת?", a: "<p>דקורטור שעוטף את הפונקציה, תופס רק שגיאות זמניות (timeout, שגיאת חיבור, קודים 429 או 5xx), ומחכה זמן שגדל אקספוננציאלית בין ניסיון לניסיון, עם תוספת אקראית קטנה (jitter) כדי שכל הבקשות לא יחזרו באותו רגע. אחרי מספר ניסיונות מקסימלי זורקים את השגיאה הלאה, כדי שהיא תופיע בלוגים ולא תיבלע בשקט.</p>" },
    { q: "מה ההבדל בין list ל־tuple, ולמה בכלל צריך tuple?", a: "<p>רשימה ניתנת לשינוי, ו־tuple לא. בגלל זה tuple אפשר לגבב (hashable), ולכן אפשר להשתמש בו כמפתח במילון, למשל <code>(home_team, away_team, date)</code> כמפתח של משחק. הוא גם מבטא כוונה: זו רשומה קבועה ולא אוסף שגדל.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "java",
  group: "lang",
  title: "Java",
  cv: ["Java"],
  usedIn: [],
  risk: "אף פרויקט בקו״ח לא כתוב ב־Java. אם ישאלו, התשובה תהיה מהקורסים באוניברסיטה, אז צריך להכיר היטב את יסודות התכנות מונחה העצמים ואת ה־Collections.",
  dropAdvice: "אם אתה מוריד, שקול להשאיר אותה כ״היכרות אקדמית״ ולא כשפה שאתה עובד בה",
  summary: "שפה עם טיפוסים סטטיים שרצה על JVM. בראיון לדאטה ישאלו בעיקר על OOP, על Collections ועל ההבדלים מ־Python.",
  html: `
<section>
  <h2>איך Java רצה</h2>
  <p>קוד Java מתקמפל ל־<strong>bytecode</strong> (קבצי <code>.class</code>), ואותו מריצה המכונה הווירטואלית, ה־JVM. מכאן הסלוגן ״כתוב פעם אחת, הרץ בכל מקום״. ה־JVM כולל מהדר JIT שמתרגם קוד חם לקוד מכונה בזמן ריצה, ולכן Java מהירה בהרבה מ־Python בלולאות.</p>
  <p>יש בה <strong>טיפוסים סטטיים</strong>: לכל משתנה יש טיפוס קבוע שנבדק בזמן קומפילציה, ושגיאות טיפוס נתפסות לפני הריצה. רוב כלי ה־Big Data הקלאסיים (Hadoop, Kafka, Spark) כתובים ב־Java או ב־Scala ורצים על ה־JVM, ולכן היא רלוונטית גם לדאטה.</p>
</section>

<section>
  <h2>ארבעת עקרונות ה־OOP</h2>
  <ul>
    <li><strong>כימוס</strong> (Encapsulation): שדות פרטיים (<code>private</code>), וגישה דרך מתודות. כך המחלקה שולטת במצב שלה.</li>
    <li><strong>הורשה</strong> (Inheritance): מחלקה יורשת ממחלקה אחת בלבד, עם <code>extends</code>.</li>
    <li><strong>פולימורפיזם</strong>: אותה קריאה מתנהגת אחרת לפי הטיפוס האמיתי של האובייקט בזמן ריצה.</li>
    <li><strong>הפשטה</strong> (Abstraction): חושפים ממשק ומסתירים את המימוש, עם <code>interface</code> או <code>abstract class</code>.</li>
  </ul>
<pre><code>interface Scraper {
    List&lt;Match&gt; fetch(String season);
}

class LaLigaScraper implements Scraper {
    private final HttpClient client;          // כימוס: שדה פרטי וסופי

    LaLigaScraper(HttpClient client) { this.client = client; }

    @Override
    public List&lt;Match&gt; fetch(String season) { /* ... */ }
}

Scraper s = new LaLigaScraper(client);        // פולימורפיזם: הטיפוס המוצהר הוא הממשק
List&lt;Match&gt; matches = s.fetch("2025-26");</code></pre>
  <p><strong>ממשק לעומת מחלקה מופשטת</strong>: מחלקה יכולה לממש הרבה ממשקים, אבל לרשת רק ממחלקה אחת. מחלקה מופשטת יכולה להחזיק מצב (שדות) וקונסטרקטור. ממשק מגדיר חוזה, ומאז Java 8 הוא יכול לכלול גם מתודות <code>default</code>.</p>
</section>

<section>
  <h2>אוספים</h2>
  <div class="tbl-scroll"><table>
    <tr><th>מחלקה</th><th>מה זה</th><th>שווה ערך ב־Python</th></tr>
    <tr><td><code>ArrayList</code></td><td>מערך דינמי, גישה לפי אינדקס ב־<code>O(1)</code></td><td><code>list</code></td></tr>
    <tr><td><code>LinkedList</code></td><td>רשימה מקושרת, גישה לפי אינדקס ב־<code>O(n)</code></td><td>אין שווה ערך ישיר</td></tr>
    <tr><td><code>HashMap</code></td><td>מיפוי מפתח לערך, בלי סדר מובטח</td><td><code>dict</code></td></tr>
    <tr><td><code>HashSet</code></td><td>ערכים ייחודיים</td><td><code>set</code></td></tr>
    <tr><td><code>TreeMap</code></td><td>מיפוי ממוין לפי מפתח, <code>O(log n)</code></td><td>מילון ממוין</td></tr>
  </table></div>
</section>

<section>
  <h2>המלכודות שאוהבים לשאול עליהן</h2>
  <h3>השוואת מחרוזות</h3>
<pre><code>String a = new String("Barca");
String b = new String("Barca");
a == b        // false: משווה הפניות, כלומר אם זה אותו אובייקט
a.equals(b)   // true:  משווה תוכן</code></pre>
  <h3>החוזה של equals ו־hashCode</h3>
  <p>אם דורסים את <code>equals</code>, חייבים לדרוס גם את <code>hashCode</code>: שני אובייקטים שווים חייבים להחזיר אותו hash. אחרת <code>HashMap</code> ו־<code>HashSet</code> ״יאבדו״ אובייקטים, כי הם מחפשים בדלי הלא נכון.</p>
  <h3>מחרוזות הן immutable</h3>
  <p>כל שרשור עם <code>+</code> בתוך לולאה יוצר מחרוזת חדשה. בלולאות משתמשים ב־<code>StringBuilder</code>.</p>
  <h3>חריגות מסומנות ולא מסומנות</h3>
  <p>חריגה מסומנת (checked), כמו <code>IOException</code>, חייבים לתפוס או להצהיר עליה עם <code>throws</code>, והקומפיילר אוכף את זה. חריגה לא מסומנת (unchecked) יורשת מ־<code>RuntimeException</code>, למשל <code>NullPointerException</code>, ואין חובה לטפל בה.</p>
  <h3>המילה final</h3>
  <p>משתנה <code>final</code> אי אפשר להציב מחדש, אבל אם הוא מצביע לאובייקט, את האובייקט עצמו עדיין אפשר לשנות. מחלקה <code>final</code> אי אפשר לרשת, ומתודה <code>final</code> אי אפשר לדרוס.</p>
</section>

<section>
  <h2>זרמים, הגרסה של Java לקומפרהנשן</h2>
<pre><code>double totalXg = shots.stream()
    .filter(s -&gt; s.getMinute() &gt; 75)
    .mapToDouble(Shot::getXg)
    .sum();</code></pre>
</section>
`,
  tip: "תהיה כן: ״השתמשתי ב־Java בקורסים באוניברסיטה, בעיקר במבני נתונים ובתכנות מונחה עצמים. את הפרויקטים שלי כתבתי ב־Python כי שם האקוסיסטם של הדאטה״. אחרי זה תראה שאתה מכיר את העקרונות. אל תעמיד פנים שעבדת איתה בפרודקשן.",
  questions: [
    {
      q: "מה יחזיר הביטוי <code>new String(\"a\") == new String(\"a\")</code>?",
      choices: ["<code>true</code>", "<code>false</code>", "שגיאת קומפילציה", "תלוי בגרסת ה־JVM"],
      answer: 1,
      explain: "האופרטור == משווה הפניות, ואלה שני אובייקטים שונים. כדי להשוות תוכן משתמשים ב־<code>equals</code>."
    },
    {
      q: "דרסת את <code>equals</code> במחלקה <code>Player</code> אבל לא את <code>hashCode</code>. מה יקרה כששמים שחקנים ב־<code>HashSet</code>?",
      choices: ["שום דבר, הכול יעבוד", "שגיאת קומפילציה", "ייתכן ששני שחקנים ״שווים״ ייכנסו פעמיים, ו־contains יחזיר false על שחקן שקיים", "ה־HashSet ימיין אותם"],
      answer: 2,
      explain: "החוזה דורש שאובייקטים שווים יחזירו אותו hashCode. בלי זה, ה־HashSet מחפש בדלי הלא נכון ולא מוצא את האובייקט."
    },
    {
      q: "מה נכון לגבי ממשק לעומת מחלקה מופשטת?",
      choices: ["מחלקה יכולה לרשת מכמה מחלקות מופשטות", "מחלקה יכולה לממש כמה ממשקים, אבל לרשת רק ממחלקה אחת", "לממשק יש קונסטרקטור", "אין ביניהם הבדל"],
      answer: 1,
      explain: "ב־Java אין ירושה מרובה של מחלקות, אבל אפשר לממש כמה ממשקים. מחלקה מופשטת יכולה להחזיק שדות וקונסטרקטור, וממשק לא."
    },
    {
      q: "איזו מהחריגות הבאות היא checked, כלומר הקומפיילר מחייב לטפל בה?",
      choices: ["<code>NullPointerException</code>", "<code>IOException</code>", "<code>ArrayIndexOutOfBoundsException</code>", "<code>IllegalArgumentException</code>"],
      answer: 1,
      explain: "החריגה IOException לא יורשת מ־RuntimeException, ולכן היא מסומנת: חובה לתפוס אותה או להצהיר <code>throws</code>. שלוש האחרות יורשות מ־RuntimeException."
    },
    {
      q: "בונים מחרוזת CSV גדולה בלולאה של 100 אלף איטרציות. מה עדיף?",
      choices: ["שרשור עם <code>+=</code>", "<code>StringBuilder</code> ו־<code>append</code>", "<code>String.format</code> בכל איטרציה", "אין הבדל"],
      answer: 1,
      explain: "המחלקה String היא immutable, ולכן כל += יוצר מחרוזת חדשה ומעתיק את כל התוכן. מכאן זמן ריצה ריבועי. StringBuilder משנה באפר אחד."
    },
    {
      q: "מה המשמעות של <code>final List&lt;String&gt; teams = new ArrayList&lt;&gt;();</code>?",
      choices: ["אי אפשר להוסיף איברים לרשימה", "אי אפשר להציב רשימה אחרת במשתנה teams, אבל אפשר להוסיף ולהסיר איברים", "הרשימה ממוינת", "הרשימה thread-safe"],
      answer: 1,
      explain: "המילה final נועלת את ההפניה, לא את האובייקט. לרשימה שבאמת אי אפשר לשנות משתמשים ב־<code>List.of(...)</code>."
    },
    {
      q: "מה ההבדל המרכזי באופן הריצה בין Java ל־Python הסטנדרטית?",
      choices: ["Java מפורשת שורה אחרי שורה", "Java מתקמפלת ל־bytecode שרץ על ה־JVM עם JIT, וטיפוסים נבדקים בזמן קומפילציה", "Python מתקמפלת לקוד מכונה", "שתיהן זהות"],
      answer: 1,
      explain: "גם Python מתקמפלת ל־bytecode, אבל המפרש הסטנדרטי שלה לא כולל JIT, והטיפוסים בה דינמיים. ב־Java הטיפוסים סטטיים, וה־JIT מהדר קוד חם לקוד מכונה."
    }
  ],
  open: [
    { q: "הסבר פולימורפיזם עם דוגמה.", a: "<p>משתנה מטיפוס הממשק <code>Scraper</code> יכול להחזיק <code>LaLigaScraper</code> או <code>PremierLeagueScraper</code>. הקריאה <code>s.fetch()</code> מפעילה את המימוש של הטיפוס האמיתי בזמן ריצה. כך הפייפליין לא צריך לדעת מאיזו ליגה הוא מושך, ואפשר להוסיף ליגה חדשה בלי לגעת בו.</p>" },
    { q: "למה Java ולא Python, או להפך?", a: "<p>Java מהירה יותר, הטיפוסים הסטטיים תופסים שגיאות מוקדם, והיא מתאימה למערכות גדולות עם הרבה מפתחים. Python מהירה לכתיבה, ויש לה את האקוסיסטם של הדאטה וה־ML (Pandas, PyTorch). לכן בחרתי ב־Python לפרויקטים, ובשירות backend בעומס גבוה הייתי שוקל Java.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "sql",
  group: "lang",
  title: "SQL",
  cv: ["SQL"],
  usedIn: ["laliga"],
  summary: "כמעט בטוח שיהיה תרגיל SQL בראיון לתפקיד דאטה. JOIN, GROUP BY ופונקציות חלון הם החובה.",
  html: `
<section>
  <h2>הסכמה שנעבוד איתה</h2>
<pre><code>teams   (team_id, name)
matches (match_id, match_date, home_id, away_id, home_goals, away_goals)
players (player_id, name, team_id)
goals   (goal_id, match_id, player_id, minute)</code></pre>
</section>

<section>
  <h2>סדר הביצוע, ולא סדר הכתיבה</h2>
  <p>כותבים <code>SELECT</code> ראשון, אבל מסד הנתונים מבצע את השאילתה בסדר הזה:</p>
<pre><code>FROM / JOIN  →  WHERE  →  GROUP BY  →  HAVING  →  SELECT  →  ORDER BY  →  LIMIT</code></pre>
  <p>מכאן נובעות שתי תשובות לראיון:</p>
  <ul>
    <li>אי אפשר להשתמש בכינוי (alias) מה־SELECT בתוך WHERE, כי WHERE רץ קודם. ב־ORDER BY אפשר.</li>
    <li>השלב <strong>WHERE</strong> מסנן שורות לפני הקיבוץ. השלב <strong>HAVING</strong> מסנן קבוצות אחרי הקיבוץ, ולכן רק בו אפשר לסנן לפי <code>COUNT</code> או <code>SUM</code>.</li>
  </ul>
<pre><code>-- שחקנים עם יותר מ־10 שערים אחרי הדקה ה־75
SELECT p.name, COUNT(*) AS late_goals
FROM goals g
JOIN players p ON p.player_id = g.player_id
WHERE g.minute &gt; 75            -- מסנן שורות
GROUP BY p.name
HAVING COUNT(*) &gt; 10           -- מסנן קבוצות
ORDER BY late_goals DESC;</code></pre>
</section>

<section>
  <h2>סוגי צירופים</h2>
  <div class="tbl-scroll"><table>
    <tr><th>סוג</th><th>מה מוחזר</th></tr>
    <tr><td><code>INNER JOIN</code></td><td>רק שורות שיש להן התאמה בשני הצדדים</td></tr>
    <tr><td><code>LEFT JOIN</code></td><td>כל השורות מהטבלה השמאלית, ו־NULL בעמודות הימניות כשאין התאמה</td></tr>
    <tr><td><code>FULL OUTER JOIN</code></td><td>כל השורות משני הצדדים</td></tr>
    <tr><td><code>CROSS JOIN</code></td><td>כל הצירופים האפשריים, מכפלה קרטזית</td></tr>
  </table></div>
<pre><code>-- כל השחקנים, כולל אלה שלא הבקיעו אף פעם
SELECT p.name, COUNT(g.goal_id) AS goals   -- COUNT(עמודה) לא סופר NULL
FROM players p
LEFT JOIN goals g ON g.player_id = p.player_id
GROUP BY p.name;</code></pre>
  <p>מלכודת נפוצה: תנאי על הטבלה הימנית שנכתב ב־WHERE הופך את ה־LEFT JOIN בפועל ל־INNER JOIN, כי השורות עם NULL מסוננות. תנאי כזה שמים בתוך ה־<code>ON</code>.</p>
</section>

<section>
  <h2>ערכי NULL</h2>
  <ul>
    <li>התנאי <code>x = NULL</code> אף פעם לא אמת, ולכן כותבים <code>x IS NULL</code>.</li>
    <li>הביטוי <code>COUNT(*)</code> סופר שורות, ו־<code>COUNT(col)</code> סופר רק ערכים שאינם NULL.</li>
    <li>הפונקציה <code>COALESCE(x, 0)</code> מחליפה NULL בערך ברירת מחדל.</li>
  </ul>
</section>

<section>
  <h2>טבלאות זמניות עם CTE</h2>
<pre><code>WITH team_goals AS (
    SELECT home_id AS team_id, home_goals AS gf, away_goals AS ga FROM matches
    UNION ALL
    SELECT away_id, away_goals, home_goals FROM matches
)
SELECT t.name, SUM(gf) AS scored, SUM(ga) AS conceded, SUM(gf - ga) AS diff
FROM team_goals tg JOIN teams t USING (team_id)
GROUP BY t.name
ORDER BY diff DESC;</code></pre>
  <p>כך בונים טבלת ליגה. <code>UNION ALL</code> משאיר כפילויות ולכן הוא מהיר, בעוד <code>UNION</code> מסיר כפילויות ודורש מיון או גיבוב. כאן חייבים UNION ALL, אחרת שני משחקים עם אותה תוצאה יימחקו.</p>
</section>

<section>
  <h2>פונקציות חלון</h2>
  <p>פונקציית חלון מחשבת ערך על קבוצת שורות <strong>בלי לכווץ אותן</strong> לשורה אחת, בניגוד ל־GROUP BY. זה הנושא שהכי מבדיל בין מועמדים.</p>
<pre><code>-- מלך השערים של כל קבוצה
WITH scorers AS (
    SELECT p.team_id, p.name, COUNT(*) AS goals,
           ROW_NUMBER() OVER (PARTITION BY p.team_id ORDER BY COUNT(*) DESC) AS rn
    FROM goals g JOIN players p USING (player_id)
    GROUP BY p.team_id, p.name
)
SELECT * FROM scorers WHERE rn = 1;

-- הפרש שערים מצטבר לאורך העונה, והתוצאה של המשחק הקודם
SELECT match_date,
       SUM(home_goals - away_goals) OVER (ORDER BY match_date) AS running_diff,
       LAG(home_goals) OVER (ORDER BY match_date)              AS prev_home_goals
FROM matches WHERE home_id = 1;</code></pre>
  <p>כשיש תיקו בערכים: <code>ROW_NUMBER</code> נותן 1, 2, 3, ו־<code>RANK</code> נותן 1, 1, 3, ו־<code>DENSE_RANK</code> נותן 1, 1, 2.</p>
</section>
`,
  tip: "בתרגיל SQL חי תחשוב בקול: ״קודם אני מחליט מה הגרעיניות של התוצאה, שורה לכל קבוצה או לכל משחק, ואז אני יודע במה לקבץ״. אם צריך ״הכי טוב בכל קבוצה״, תגיד מיד ROW_NUMBER עם PARTITION BY. זה מה שהמראיין מחפש.",
  questions: [
    {
      q: "צריך את הקבוצות שהבקיעו יותר מ־50 שערים בבית. איפה התנאי על הסכום?",
      choices: ["ב־<code>WHERE SUM(home_goals) &gt; 50</code>", "ב־<code>HAVING SUM(home_goals) &gt; 50</code>", "ב־<code>ON</code> של ה־JOIN", "ב־<code>ORDER BY</code>"],
      answer: 1,
      explain: "השלב WHERE רץ לפני הקיבוץ ולא מכיר אגרגציות. סינון לפי SUM או COUNT נעשה ב־HAVING."
    },
    {
      q: "מה יחזיר <code>SELECT * FROM players WHERE team_id = NULL</code>?",
      choices: ["את כל השחקנים בלי קבוצה", "אפס שורות, תמיד", "שגיאה", "את כל השחקנים"],
      answer: 1,
      explain: "השוואה ל־NULL מחזירה UNKNOWN ולא TRUE, ולכן אף שורה לא עוברת. הצורה הנכונה היא <code>IS NULL</code>."
    },
    {
      q: "בטבלת players יש 500 שחקנים, ו־120 מהם לא הבקיעו אף פעם. כמה שורות יחזיר <code>players LEFT JOIN goals</code> עם GROUP BY לפי שחקן?",
      choices: ["380", "500", "120", "תלוי במספר השערים"],
      answer: 1,
      explain: "צירוף LEFT שומר את כל השורות מהצד השמאלי. 120 השחקנים יופיעו עם <code>COUNT(g.goal_id) = 0</code>."
    },
    {
      q: "מה ההבדל בין <code>COUNT(*)</code> ל־<code>COUNT(assist_id)</code>?",
      choices: ["אין הבדל", "הראשון סופר את כל השורות, והשני רק שורות שבהן assist_id אינו NULL", "השני מהיר יותר", "הראשון לא סופר NULL"],
      answer: 1,
      explain: "בעזרת זה אפשר לספור בשאילתה אחת גם את כל השערים וגם את השערים שהיה להם בישול."
    },
    {
      q: "שלושה שחקנים עם 20, 20 ו־15 שערים. מה יחזיר <code>RANK() OVER (ORDER BY goals DESC)</code>?",
      choices: ["1, 2, 3", "1, 1, 2", "1, 1, 3", "1, 2, 2"],
      answer: 2,
      explain: "הפונקציה RANK נותנת דירוג זהה לערכים שווים, ומדלגת על המקום הבא. התוצאה 1, 1, 2 היא של DENSE_RANK, והתוצאה 1, 2, 3 היא של ROW_NUMBER."
    },
    {
      q: "למה השאילתה הזו נכשלת ב־PostgreSQL?",
      code: "SELECT home_goals + away_goals AS total\nFROM matches\nWHERE total > 4;",
      choices: ["אסור לחבר עמודות", "השלב WHERE רץ לפני SELECT, ולכן הכינוי total עוד לא קיים", "חסר GROUP BY", "חסר LIMIT"],
      answer: 1,
      explain: "בגלל סדר הביצוע, צריך לחזור על הביטוי ב־WHERE או לעטוף את השאילתה ב־CTE. ב־ORDER BY מותר להשתמש בכינוי."
    },
    {
      q: "בונים טבלת ליגה בעזרת איחוד של משחקי בית ומשחקי חוץ. למה <code>UNION ALL</code> ולא <code>UNION</code>?",
      choices: ["אין סיבה, שניהם זהים", "האופרטור UNION מסיר שורות כפולות, ושני משחקים עם אותה קבוצה ותוצאה ייספרו פעם אחת", "האופרטור UNION לא עובד עם GROUP BY", "האופרטור UNION ALL ממיין את התוצאה"],
      answer: 1,
      explain: "האופרטור UNION מבצע DISTINCT, וזה גם איטי יותר וגם שגוי כאן. UNION ALL פשוט מחבר את התוצאות."
    },
    {
      q: "איך מוצאים את השחקן המוביל בשערים בכל קבוצה?",
      choices: ["<code>MAX(goals)</code> עם GROUP BY לפי קבוצה, וזה מחזיר גם את שם השחקן", "<code>ROW_NUMBER() OVER (PARTITION BY team ORDER BY goals DESC)</code> ואז סינון של rn = 1", "<code>ORDER BY goals DESC LIMIT 1</code>", "<code>DISTINCT team</code>"],
      answer: 1,
      explain: "הפונקציה MAX מחזירה את המספר, אבל לא את השחקן שהשיג אותו. פונקציית חלון שומרת על השורה המלאה. LIMIT 1 מחזיר שחקן אחד לכל הליגה."
    }
  ],
  open: [
    { q: "כתוב שאילתה שמחזירה את 3 הקבוצות עם הכי הרבה ניצחונות בבית.", a: "<pre><code>SELECT t.name, COUNT(*) AS home_wins\nFROM matches m\nJOIN teams t ON t.team_id = m.home_id\nWHERE m.home_goals &gt; m.away_goals\nGROUP BY t.name\nORDER BY home_wins DESC\nLIMIT 3;</code></pre><p>שים לב: אם יש תיקו במקום השלישי, LIMIT יחתוך אותו באופן שרירותי. אם רוצים את כל הקבוצות שנמצאות בתיקו, משתמשים ב־RANK ומסננים לפי דירוג שלוש ומטה.</p>" },
    { q: "מה ההבדל בין פונקציית חלון ל־GROUP BY?", a: "<p>הפקודה GROUP BY מכווצת כל קבוצה לשורה אחת. פונקציית חלון מחשבת ערך על קבוצת שורות, אבל מחזירה אותו בכל שורה ושומרת על כולן. לכן היא מתאימה לדירוג, לסכום מצטבר ולהשוואה לשורה הקודמת עם LAG.</p>" }
  ]
}
);
