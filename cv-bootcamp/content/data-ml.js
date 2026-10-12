/* CV bootcamp content: Data & ML (Pandas, NumPy, Scikit-Learn, PyTorch, XGBoost, Streamlit). */
(window.BOOTCAMP_TOPICS = window.BOOTCAMP_TOPICS || []).push(

/* ======================================================================= */
{
  id: "pandas",
  group: "dataml",
  title: "Pandas",
  cv: ["Pandas"],
  usedIn: ["xepl", "laliga", "barca"],
  summary: "הכלי המרכזי לעיבוד טבלאות ב־Python. ב־XEPL כל טבלת ליגה וסטטיסטיקת משחק עוברת דרכו.",
  html: `
<section>
  <h2>שני האובייקטים</h2>
  <p>אובייקט <strong>Series</strong> הוא עמודה אחת: מערך ערכים עם אינדקס. אובייקט <strong>DataFrame</strong> הוא טבלה: אוסף של Series שחולקות אינדקס אחד. לכל עמודה יש טיפוס (<code>dtype</code>) משלה.</p>
<pre><code>import pandas as pd

matches = pd.read_csv("epl_2025.csv")
matches["date"] = pd.to_datetime(matches["date"])   # מחרוזת לתאריך אמיתי
matches.info()          # עמודות, טיפוסים, ערכים חסרים
matches.describe()      # סטטיסטיקה בסיסית לעמודות מספריות

# JSON מקונן מ־API לטבלה שטוחה
shots = pd.json_normalize(api_response["shots"])</code></pre>
</section>

<section>
  <h2>בחירת נתונים עם loc ו־iloc</h2>
  <ul>
    <li><code>loc</code> בוחר לפי <strong>תווית</strong> (שם השורה ושם העמודה). בחיתוך הקצה העליון <strong>נכלל</strong>.</li>
    <li><code>iloc</code> בוחר לפי <strong>מיקום</strong> (מספר שלם), כמו רשימה ב־Python. הקצה העליון <strong>לא</strong> נכלל.</li>
  </ul>
<pre><code>df.loc[0:2, ["home", "away"]]   # שורות עם התוויות 0, 1, 2
df.iloc[0:2, 0:2]               # שתי השורות הראשונות ושתי העמודות הראשונות

# סינון בוליאני: & ו־| במקום and ו־or, וכל תנאי בסוגריים
big_wins = df[(df["home_goals"] - df["away_goals"] &gt;= 3) &amp; (df["home"] == "Arsenal")]
top6 = df[df["home"].isin(["Arsenal", "Liverpool", "Man City"])]</code></pre>
</section>

<section>
  <h2>קיבוץ ואגרגציה</h2>
  <p>התבנית היא <strong>split, apply, combine</strong>: מפצלים לקבוצות, מחשבים על כל קבוצה, ומחברים חזרה.</p>
<pre><code>team_stats = (
    shots.groupby("team")
         .agg(shots=("xg", "size"),
              xg=("xg", "sum"),
              goals=("is_goal", "sum"))
         .assign(xg_diff=lambda d: d["goals"] - d["xg"])
         .sort_values("xg", ascending=False)
)

# transform מחזיר תוצאה באורך המקורי, למשל אחוז מסך ה־xG של הקבוצה
shots["xg_share"] = shots["xg"] / shots.groupby("team")["xg"].transform("sum")</code></pre>
</section>

<section>
  <h2>חיבור טבלאות עם merge</h2>
  <p>הפונקציה <code>merge</code> היא ה־JOIN של Pandas. הפרמטר <code>how</code> מקבל את הערכים <code>inner</code>, <code>left</code>, <code>right</code> או <code>outer</code>, כמו ב־SQL.</p>
<pre><code>shots_full = shots.merge(players, on="player_id", how="left", validate="many_to_one")
# validate זורק שגיאה אם בטבלת השחקנים יש מזהה כפול, שהיה מכפיל שורות בשקט</code></pre>
  <p>יש גם <code>pd.concat</code>, שמדביק טבלאות זו מתחת לזו (או זו לצד זו) בלי להתאים לפי מפתח.</p>
</section>

<section>
  <h2>ערכים חסרים</h2>
<pre><code>df.isna().sum()                     # כמה ערכים חסרים בכל עמודה
df["attendance"].fillna(df["attendance"].median())
df.dropna(subset=["xg"])            # מוחק רק שורות שחסר בהן xg</code></pre>
  <p>בלי הפרמטר <code>subset</code>, הפונקציה <code>dropna()</code> מוחקת כל שורה שחסר בה ערך כלשהו, וזה יכול למחוק חצי מהנתונים בלי שתשים לב.</p>
</section>

<section>
  <h2>ביצועים, ומלכודת ההעתקה</h2>
  <ul>
    <li><strong>וקטוריזציה</strong>: פעולה על עמודה שלמה (<code>df["a"] * df["b"]</code>) רצה ב־C. לולאה עם <code>iterrows()</code> רצה בקצב של Python, ויכולה להיות איטית פי מאה. הפונקציה <code>apply</code> נמצאת באמצע, כי היא עדיין לולאה של Python.</li>
    <li><strong>האזהרה SettingWithCopyWarning</strong> מופיעה כשמשנים טבלה שנוצרה מסינון. ייתכן שזו הייתה תצוגה (view) של הטבלה המקורית, ואז השינוי לא יחול איפה שציפית. הפתרון הוא <code>.copy()</code> אחרי הסינון, או השמה ישירה עם <code>df.loc[mask, "col"] = value</code>.</li>
    <li>כדי לחסוך זיכרון, עמודה עם מעט ערכים שונים (למשל שם קבוצה) הופכים ל־<code>category</code>.</li>
  </ul>
<pre><code>pd.pivot_table(matches, index="home", columns="season", values="home_goals", aggfunc="mean")</code></pre>
</section>
`,
  tip: "תגיד מה עשית איתו בפועל: ״ב־XEPL בניתי את טבלת הליגה מנתוני משחקים עם groupby ו־merge, וחישבתי לכל קבוצה xG מצטבר מול שערים בפועל״. אם ישאלו על ביצועים, תזכיר וקטוריזציה ותגיד שאתה נמנע מ־iterrows.",
  questions: [
    {
      q: "לטבלה יש אינדקס מספרי רגיל (0, 1, 2…). כמה שורות יחזיר <code>df.loc[0:3]</code>, וכמה יחזיר <code>df.iloc[0:3]</code>?",
      choices: ["3 ו־3", "4 ו־3", "3 ו־4", "4 ו־4"],
      answer: 1,
      explain: "חיתוך עם loc לפי תוויות כולל את הקצה העליון, ולכן חוזרות השורות 0 עד 3. חיתוך עם iloc לפי מיקום לא כולל את הקצה, כמו ב־Python."
    },
    {
      q: "למה השורה הזו זורקת שגיאה?",
      code: "df[df[\"goals\"] > 2 and df[\"team\"] == \"Barca\"]",
      choices: ["אסור לסנן לפי שתי עמודות", "האופרטור and של Python מנסה להמיר Series שלמה ל־True או False. צריך <code>&amp;</code> וסוגריים סביב כל תנאי", "חסר <code>.loc</code>", "צריך להשתמש ב־<code>query</code>"],
      answer: 1,
      explain: "הצורה הנכונה: <code>df[(df.goals &gt; 2) &amp; (df.team == \"Barca\")]</code>. הסוגריים נחוצים כי לאופרטור &amp; יש קדימות גבוהה יותר מאשר להשוואות."
    },
    {
      q: "מה מחזיר <code>shots.groupby(\"team\")[\"xg\"].sum()</code>?",
      choices: ["טבלה עם אותו מספר שורות כמו shots", "אובייקט Series שהאינדקס שלו הוא שמות הקבוצות", "מספר אחד", "רשימה"],
      answer: 1,
      explain: "שורה אחת לכל קבוצה. אם רוצים ערך באורך המקורי, למשל כדי להוסיף אותו כעמודה, משתמשים ב־<code>transform(\"sum\")</code>."
    },
    {
      q: "אחרי <code>shots.merge(players, on=\"player_id\")</code> מספר השורות גדל מ־10,000 ל־10,450. מה הסיבה הכי סבירה?",
      choices: ["באג ב־Pandas", "יש מזהי שחקנים כפולים בטבלת players, ולכן חלק מהבעיטות שוכפלו", "המיזוג הוסיף שחקנים בלי בעיטות", "ערכים חסרים"],
      answer: 1,
      explain: "צירוף על מפתח שאינו ייחודי מכפיל שורות. זו בדיוק הסיבה לפרמטר <code>validate=\"many_to_one\"</code>. האפשרות של שחקנים בלי בעיטות לא נכונה, כי ברירת המחדל היא inner."
    },
    {
      q: "צריך עמודה חדשה של הפרש שערים לכל משחק, בטבלה של מיליון שורות. מה הדרך הנכונה?",
      choices: ["לולאה עם <code>iterrows()</code>", "<code>df[\"diff\"] = df[\"home_goals\"] - df[\"away_goals\"]</code>", "<code>df.apply(lambda r: r.home_goals - r.away_goals, axis=1)</code>", "המרה לרשימה וחזרה"],
      answer: 1,
      explain: "פעולה וקטורית על עמודות שלמות רצה ב־C, ולכן היא מהירה בסדרי גודל. גם apply עם axis=1 הוא לולאה של Python מאחורי הקלעים."
    },
    {
      q: "מה עושה <code>df.dropna()</code> בלי פרמטרים?",
      choices: ["מוחק עמודות ריקות", "מוחק כל שורה שיש בה לפחות ערך חסר אחד", "ממלא ערכים חסרים באפס", "מוחק רק שורות שכולן ריקות"],
      answer: 1,
      explain: "זו ברירת המחדל, <code>how=\"any\"</code>. כדי למחוק רק לפי עמודות מסוימות משתמשים ב־<code>subset</code>."
    },
    {
      q: "סיננת <code>home = df[df.venue == \"H\"]</code>, ואז <code>home[\"pts\"] = 3</code> הקפיץ SettingWithCopyWarning. מה הבעיה?",
      choices: ["אסור להוסיף עמודות", "ייתכן שהטבלה home היא תצוגה של df, ולא ברור איפה השינוי יחול. צריך <code>.copy()</code> אחרי הסינון", "חסר inplace=True", "צריך לאפס את האינדקס"],
      answer: 1,
      explain: "הקריאה <code>df[mask].copy()</code> יוצרת טבלה עצמאית. אם התכוונת לשנות את df עצמה, כותבים <code>df.loc[mask, \"pts\"] = 3</code>."
    },
    {
      q: "למה להריץ <code>pd.to_datetime</code> על עמודת תאריך שנקראה מ־CSV?",
      choices: ["כדי לחסוך זיכרון בלבד", "מ־CSV היא נקראת כמחרוזת. רק אחרי ההמרה אפשר למיין נכון, לחשב הפרשי ימים ולחלץ חודש או יום בשבוע", "Pandas דורש את זה כדי לשמור קבצים", "כדי להמיר לאזור זמן אחר"],
      answer: 1,
      explain: "מחרוזות בפורמט DD/MM/YYYY ממוינות בסדר שגוי. אחרי ההמרה יש גישה ל־<code>.dt.month</code>, <code>.dt.dayofweek</code> וכן הלאה."
    }
  ],
  open: [
    { q: "יש לך טבלת משחקים. איך תבנה ממנה טבלת ליגה?", a: "<p>הופכים כל משחק לשתי שורות, אחת מנקודת המבט של הבית ואחת של החוץ, עם שערי זכות ושערי חובה. מחשבים נקודות עם <code>np.select</code> (3 לניצחון, 1 לתיקו, 0 להפסד). מקבצים לפי קבוצה, סוכמים, וממיינים לפי נקודות, הפרש שערים ושערי זכות.</p><pre><code>home = m.rename(columns={\"home\":\"team\",\"home_goals\":\"gf\",\"away_goals\":\"ga\"})\naway = m.rename(columns={\"away\":\"team\",\"away_goals\":\"gf\",\"home_goals\":\"ga\"})\nt = pd.concat([home, away])[[\"team\",\"gf\",\"ga\"]]\nt[\"pts\"] = np.select([t.gf &gt; t.ga, t.gf == t.ga], [3, 1], 0)\ntable = t.groupby(\"team\").sum().sort_values([\"pts\",\"gf\"], ascending=False)</code></pre>" },
    { q: "Pandas איטי לך על 50 מיליון שורות. מה האפשרויות?", a: "<p>קודם כול: וקטוריזציה במקום apply, טיפוס category לעמודות טקסט, וקריאה של העמודות הנחוצות בלבד (<code>usecols</code>) או בחלקים (<code>chunksize</code>). אם זה לא מספיק, עוברים לפורמט Parquet ולכלים כמו Polars או DuckDB, או מעבירים את הסינון והקיבוץ ל־SQL במסד הנתונים.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "numpy",
  group: "dataml",
  title: "NumPy",
  cv: ["NumPy"],
  usedIn: ["xepl", "barca"],
  summary: "מערכים מספריים מהירים. Pandas, Scikit-Learn ו־PyTorch בנויים עליו או בהשראתו, אז שואלים בעיקר על צורות, צירים ו־broadcasting.",
  html: `
<section>
  <h2>למה הוא מהיר</h2>
  <p>אובייקט <code>ndarray</code> הוא בלוק זיכרון רציף שכל האיברים בו מאותו טיפוס (<code>dtype</code>). רשימה של Python היא מערך של מצביעים לאובייקטים נפרדים. לכן NumPy יכול להריץ לולאה ב־C על הזיכרון ישירות, להשתמש בהוראות SIMD של המעבד, ולא לבדוק טיפוס בכל איבר.</p>
<pre><code>import numpy as np
xg = np.array([0.05, 0.31, 0.76, 0.12])
xg.sum(), xg.mean(), xg.max()
np.array([1, 2.5, 3]).dtype     # float64: כל המערך עובר לטיפוס הרחב ביותר</code></pre>
</section>

<section>
  <h2>צורה וצירים</h2>
<pre><code>m = np.arange(12).reshape(3, 4)   # 3 שורות, 4 עמודות
m.shape          # (3, 4)
m.sum(axis=0)    # סכום לאורך השורות, תוצאה לכל עמודה: צורה (4,)
m.sum(axis=1)    # סכום לאורך העמודות, תוצאה לכל שורה: צורה (3,)
m.reshape(-1)    # שטוח, 12 איברים. הערך -1 אומר ״תחשב לבד״</code></pre>
  <p>דרך לזכור: <code>axis=0</code> הוא הציר ש״נעלם״ מהצורה. מ־<code>(3, 4)</code> נשאר <code>(4,)</code>.</p>
</section>

<section>
  <h2>שידור (broadcasting)</h2>
  <p>כשמבצעים פעולה על שני מערכים בצורות שונות, NumPy משווה את הממדים מימין לשמאל. שני ממדים מתאימים אם הם שווים או שאחד מהם הוא 1, וממד של 1 ״נמתח״ בלי להעתיק זיכרון.</p>
<pre><code>shots = np.array([[16.0, 0.3],      # מרחק, זווית (רדיאנים)
                  [8.0,  0.9],
                  [25.0, 0.2]])     # צורה (3, 2)
mean = shots.mean(axis=0)           # צורה (2,)
std  = shots.std(axis=0)
z = (shots - mean) / std            # (3,2) מול (2,): התיכון "מוכפל" לכל שורה

col = np.ones((3, 1)); row = np.ones((1, 4))
(col + row).shape                   # (3, 4)</code></pre>
</section>

<section>
  <h2>אינדקסים בוליאניים, תצוגות והעתקים</h2>
<pre><code>xg[xg &gt; 0.3]                 # מסכה בוליאנית, מחזירה העתק
np.where(xg &gt; 0.3, "big", "small")

a = np.arange(5)
b = a[1:3]          # חיתוך מחזיר תצוגה (view), כלומר אותו זיכרון
b[0] = 99
a                   # array([ 0, 99,  2,  3,  4]): גם a השתנה
c = a[1:3].copy()   # העתק עצמאי</code></pre>
  <p>חיתוך רגיל מחזיר <strong>תצוגה</strong>. אינדוקס בעזרת מסכה בוליאנית או רשימת אינדקסים (fancy indexing) מחזיר <strong>העתק</strong>.</p>
</section>

<section>
  <h2>כפל מטריצות ואקראיות</h2>
<pre><code>A * B        # כפל איבר־איבר
A @ B        # כפל מטריצות, כמו np.matmul
rng = np.random.default_rng(seed=42)   # מחולל אקראי עם seed, לתוצאות שחוזרות על עצמן
rng.poisson(lam=1.4, size=10_000)      # למשל סימולציה של שערים במשחק</code></pre>
</section>
`,
  tip: "חבר את זה לפרויקטים: ״ב־xG חישבתי מרחק וזווית לבעיטה בצורה וקטורית על כל הבעיטות בבת אחת, עם np.hypot ו־np.arctan2, במקום בלולאה״. מראיינים אוהבים לשמוע ״וקטורי״ ו־״broadcasting״ מתוך דוגמה אמיתית.",
  questions: [
    {
      q: "למערך <code>m</code> יש צורה <code>(3, 4)</code>. מה הצורה של <code>m.sum(axis=0)</code>?",
      choices: ["<code>(3,)</code>", "<code>(4,)</code>", "<code>(3, 4)</code>", "סקלר"],
      answer: 1,
      explain: "ציר 0 (השורות) הוא זה שמתכווץ, ונשאר סכום אחד לכל עמודה, כלומר 4 ערכים."
    },
    {
      q: "מה הצורה של התוצאה כשמחברים מערך בצורה <code>(3, 1)</code> עם מערך בצורה <code>(1, 4)</code>?",
      choices: ["שגיאה, הצורות לא תואמות", "<code>(3, 4)</code>", "<code>(1, 1)</code>", "<code>(4, 3)</code>"],
      answer: 1,
      explain: "בכל ממד אחד הצדדים הוא 1, ולכן הוא נמתח. זה broadcasting."
    },
    {
      q: "מה יהיה ערכו של <code>a</code> בסוף?",
      code: "a = np.array([1, 2, 3, 4])\nb = a[:2]\nb[0] = 100",
      choices: ["<code>[1, 2, 3, 4]</code>", "<code>[100, 2, 3, 4]</code>", "שגיאה", "<code>[100, 100, 3, 4]</code>"],
      answer: 1,
      explain: "חיתוך מחזיר תצוגה שחולקת זיכרון עם a. כדי לקבל העתק עצמאי משתמשים ב־<code>.copy()</code>."
    },
    {
      q: "למה פעולה וקטורית ב־NumPy מהירה בהרבה מלולאת Python על רשימה?",
      choices: ["כי NumPy משתמש בכרטיס מסך", "בגלל זיכרון רציף מטיפוס אחיד, ולולאות שרצות ב־C בלי בדיקת טיפוס לכל איבר", "כי NumPy מקבילי תמיד על כל הליבות", "כי רשימות ב־Python מוגבלות בגודל"],
      answer: 1,
      explain: "זה גם מאפשר שימוש בהוראות SIMD וב־cache של המעבד בצורה טובה. NumPy לא רץ על GPU, ובזה PyTorch שונה ממנו."
    },
    {
      q: "מה ה־dtype של <code>np.array([1, 2.5, 3])</code>?",
      choices: ["<code>int64</code>", "<code>float64</code>", "<code>object</code>", "מעורב, int ו־float"],
      answer: 1,
      explain: "מערך NumPy הוא הומוגני, ולכן כל האיברים מומרים לטיפוס הרחב ביותר שמכיל את כולם."
    },
    {
      q: "שני מערכים <code>A</code> ו־<code>B</code> בצורה <code>(3, 3)</code>. מה ההבדל בין <code>A * B</code> לבין <code>A @ B</code>?",
      choices: ["אין הבדל", "הראשון הוא כפל איבר־איבר, והשני כפל מטריצות", "הראשון הוא כפל מטריצות, והשני כפל איבר־איבר", "האופרטור @ לא קיים ב־NumPy"],
      answer: 1,
      explain: "האופרטור @ שווה ל־<code>np.matmul</code>. זו טעות נפוצה למי שמגיע מ־MATLAB, ששם * הוא כפל מטריצות."
    },
    {
      q: "מה עושה <code>arr.reshape(-1, 2)</code> על מערך עם 10 איברים?",
      choices: ["שגיאה", "מחזיר צורה <code>(5, 2)</code>", "מחזיר צורה <code>(2, 5)</code>", "הופך את סדר האיברים"],
      answer: 1,
      explain: "הערך -1 אומר ל־NumPy לחשב לבד את הממד החסר: 10 חלקי 2 שווה 5."
    }
  ],
  open: [
    { q: "מה זה broadcasting? תן דוגמה מהעבודה שלך.", a: "<p>זו הדרך של NumPy לבצע פעולה בין מערכים בצורות שונות. הוא משווה ממדים מימין לשמאל, וממד בגודל 1 נמתח בלי העתקה. דוגמה: נרמול של מטריצת פיצ׳רים בצורה (n, k) על ידי חיסור וקטור ממוצעים בצורה (k,) וחלוקה בווקטור סטיות תקן. בשורה אחת, בלי לולאה.</p>" },
    { q: "מתי חיתוך מחזיר view ומתי copy, ולמה זה חשוב?", a: "<p>חיתוך בסיסי (<code>a[1:5]</code>) מחזיר תצוגה. אינדוקס עם מסכה בוליאנית או רשימת אינדקסים מחזיר העתק. זה חשוב כי שינוי של תצוגה משנה גם את המקור, ויכול לייצר באג שקט, למשל כשמנרמלים ״עותק״ ובפועל דורסים את נתוני האימון.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "sklearn",
  group: "dataml",
  title: "Scikit-Learn",
  cv: ["Scikit-Learn"],
  usedIn: ["barca", "xepl"],
  summary: "הספרייה של למידת מכונה קלאסית. כאן ישאלו על המושגים עצמם: דליפת מידע, התאמת יתר, מדדים ואימות צולב.",
  html: `
<section>
  <h2>סוגי בעיות</h2>
  <ul>
    <li><strong>למידה מונחית</strong>, כשיש תווית: <strong>סיווג</strong> (האם הבעיטה תהיה גול) או <strong>רגרסיה</strong> (כמה שערים יהיו במשחק).</li>
    <li><strong>למידה לא מונחית</strong>, בלי תווית: אשכולות (clustering), למשל קיבוץ שחקנים לפי סגנון משחק עם KMeans, או הורדת ממדים עם PCA.</li>
  </ul>
  <p>שים לב: <strong>רגרסיה לוגיסטית היא מודל סיווג</strong>, למרות השם. היא מחזירה הסתברות בין 0 ל־1, ולכן היא הבסיס הקלאסי למודלי xG.</p>
</section>

<section>
  <h2>ה־API האחיד</h2>
<pre><code>from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)                 # לומד מנתוני האימון בלבד
proba = model.predict_proba(X_test)[:, 1]   # הסתברות למחלקה 1, כלומר גול
pred  = model.predict(X_test)               # 0 או 1, לפי סף של 0.5</code></pre>
  <p>לכל מודל יש <code>fit</code> ו־<code>predict</code>. לכל ממיר (scaler, encoder) יש <code>fit</code> ו־<code>transform</code>.</p>
</section>

<section>
  <h2>דליפת מידע ו־Pipeline</h2>
  <p><strong>דליפת מידע</strong> (data leakage) קורית כשמידע מקבוצת המבחן נכנס לאימון. התוצאה: מדדים מצוינים במחשב שלך, ומודל גרוע בעולם האמיתי. הדוגמה הקלאסית היא להריץ <code>StandardScaler().fit</code> על כל הנתונים לפני הפיצול. הדוגמה הספורטיבית: לאמן על משחקים מעונה 2025 ולבדוק על משחקים מ־2024, כלומר ללמוד מהעתיד.</p>
  <p>הפתרון הוא <code>Pipeline</code>, שמבטיח שכל שלב עיבוד לומד מנתוני האימון בלבד, גם בתוך אימות צולב:</p>
<pre><code>from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

pre = ColumnTransformer([
    ("num", StandardScaler(), ["distance", "angle"]),
    ("cat", OneHotEncoder(handle_unknown="ignore"), ["body_part", "situation"]),
])
clf = Pipeline([("pre", pre), ("model", LogisticRegression(max_iter=1000))])
clf.fit(X_train, y_train)</code></pre>
</section>

<section>
  <h2>התאמת יתר ואימות צולב</h2>
  <ul>
    <li><strong>התאמת יתר</strong> (overfitting): ציון אימון גבוה מאוד וציון מבחן נמוך. המודל שינן רעש. פותרים עם מודל פשוט יותר, רגולריזציה או יותר נתונים.</li>
    <li><strong>התאמת חסר</strong> (underfitting): ציון נמוך בשניהם. המודל פשוט מדי.</li>
    <li><strong>אימות צולב</strong> (k-fold): מחלקים את הנתונים ל־k חלקים, מאמנים k פעמים, ובכל פעם בודקים על חלק אחר. מקבלים הערכה יציבה יותר מפיצול בודד.</li>
    <li>בנתוני זמן, כמו משחקים לאורך עונה, משתמשים ב־<code>TimeSeriesSplit</code>, שתמיד מאמן על העבר ובודק על העתיד.</li>
  </ul>
<pre><code>from sklearn.model_selection import cross_val_score, GridSearchCV
cross_val_score(clf, X, y, cv=5, scoring="neg_log_loss")
GridSearchCV(clf, {"model__C": [0.01, 0.1, 1, 10]}, cv=5, scoring="neg_log_loss").fit(X_train, y_train)</code></pre>
</section>

<section>
  <h2>מדדים</h2>
  <div class="tbl-scroll"><table>
    <tr><th>מדד</th><th>מה הוא אומר</th><th>מתי</th></tr>
    <tr><td>דיוק (accuracy)</td><td>אחוז החיזויים הנכונים</td><td>רק כשהמחלקות מאוזנות</td></tr>
    <tr><td>Precision</td><td>מתוך מה שחזיתי ״גול״, כמה באמת היו גול</td><td>כשאזעקת שווא יקרה</td></tr>
    <tr><td>Recall</td><td>מתוך כל הגולים, כמה תפסתי</td><td>כשפספוס יקר</td></tr>
    <tr><td>F1</td><td>ממוצע הרמוני של שני הקודמים</td><td>איזון ביניהם</td></tr>
    <tr><td>ROC-AUC</td><td>כמה טוב המודל מדרג חיובי מעל שלילי</td><td>מחלקות לא מאוזנות</td></tr>
    <tr><td>Log-loss, Brier</td><td>כמה ההסתברויות מדויקות ומכוילות</td><td>כשהפלט הוא הסתברות, כמו xG</td></tr>
    <tr><td>MAE, RMSE</td><td>גודל השגיאה הממוצע ברגרסיה</td><td>חיזוי מספר</td></tr>
  </table></div>
  <p>רק כ־10% מהבעיטות הן גול. מודל שתמיד חוזה ״לא גול״ יקבל דיוק של 90% ויהיה חסר תועלת לגמרי. לכן ב־xG לא מסתכלים על דיוק.</p>
</section>
`,
  tip: "המשפט שהכי עובד בראיון: ״הדבר הראשון שאני בודק הוא דליפת מידע. במודל של ברצלונה פיצלתי לפי זמן ולא אקראית, כדי שהמודל לא ילמד ממשחקים עתידיים״. זה מראה בגרות, יותר מכל אלגוריתם.",
  questions: [
    {
      q: "הרצת <code>StandardScaler().fit_transform(X)</code> על כל הנתונים, ורק אחרי זה פיצלת לאימון ומבחן. מה הבעיה?",
      choices: ["אין בעיה", "דליפת מידע: הממוצע וסטיית התקן חושבו גם על קבוצת המבחן", "ה־scaler לא עובד על נתוני מבחן", "זה רק איטי יותר"],
      answer: 1,
      explain: "צריך לאמן את ה־scaler על האימון בלבד, ואז להריץ transform על המבחן. Pipeline עושה את זה אוטומטית."
    },
    {
      q: "דיוק על האימון 99%, דיוק על המבחן 61%. מה האבחנה?",
      choices: ["התאמת חסר", "התאמת יתר", "מודל מצוין", "באג בנתוני המבחן"],
      answer: 1,
      explain: "פער גדול בין האימון למבחן אומר שהמודל שינן את האימון. פותרים עם מודל פשוט יותר, רגולריזציה, יותר נתונים, או בעצים עם עומק מוגבל."
    },
    {
      q: "במודל xG רק 10% מהבעיטות הן גול. מודל שתמיד אומר ״לא גול״ מקבל דיוק של 90%. איזה מדד מתאים יותר?",
      choices: ["דיוק (accuracy)", "Log-loss או Brier score, שבודקים את איכות ההסתברויות", "מספר העצים", "אחוז הזמן של האימון"],
      answer: 1,
      explain: "מודל xG צריך להחזיר הסתברות מכוילת, ולכן מודדים אותו לפי log-loss או Brier. גם ROC-AUC טוב, כדי לבדוק את איכות הדירוג."
    },
    {
      q: "מה ההגדרה של Precision?",
      choices: ["מתוך כל הגולים, כמה המודל זיהה", "מתוך מה שהמודל סימן כגול, כמה באמת היו גול", "אחוז החיזויים הנכונים", "השטח מתחת לעקומת ROC"],
      answer: 1,
      explain: "האפשרות הראשונה היא Recall. כדי לזכור: Precision שואל ״כשאמרתי כן, צדקתי?״, ו־Recall שואל ״כמה מכל הכן תפסתי?״"
    },
    {
      q: "על קבוצת המבחן קוראים ל־scaler עם:",
      choices: ["<code>fit_transform</code>", "<code>transform</code> בלבד", "<code>fit</code> בלבד", "לא צריך לנרמל את קבוצת המבחן"],
      answer: 1,
      explain: "הפרמטרים נלמדים מהאימון בלבד, ועל המבחן רק מפעילים אותם. קריאה ל־fit על המבחן היא דליפה."
    },
    {
      q: "מודל שחוזה תוצאת משחק מנתוני עונות קודמות. איך נכון לפצל?",
      choices: ["פיצול אקראי של 80/20", "לפי זמן: מאמנים על העבר ובודקים על משחקים מאוחרים יותר, למשל עם TimeSeriesSplit", "לפי קבוצות בית", "לא צריך לפצל"],
      answer: 1,
      explain: "פיצול אקראי מערבב עתיד בתוך האימון, למשל כשהדירוג של הקבוצה כבר כולל תוצאות של משחקים ״עתידיים״. המדדים ייראו טובים מהמציאות."
    },
    {
      q: "רגרסיה לוגיסטית היא מודל של:",
      choices: ["רגרסיה, כי הוא חוזה מספר רציף", "סיווג, כי הוא מחזיר הסתברות למחלקה", "אשכולות", "הורדת ממדים"],
      answer: 1,
      explain: "המודל מעביר צירוף לינארי דרך פונקציה סיגמואידית ומחזיר הסתברות בין 0 ל־1. זה הבסיס הקלאסי ל־xG."
    },
    {
      q: "מה המטרה של אימות צולב (k-fold)?",
      choices: ["להאיץ את האימון", "לקבל הערכה יציבה יותר לביצועים, כי כל נקודה משמשת פעם אחת לבדיקה", "להגדיל את כמות הנתונים", "למנוע ערכים חסרים"],
      answer: 1,
      explain: "בפיצול יחיד אפשר ״להתמזל״ עם קבוצת מבחן קלה. ממוצע על k קיפולים, וגם הפיזור שלו, אמינים יותר. משתמשים בזה גם לבחירת היפר־פרמטרים."
    }
  ],
  open: [
    { q: "איך היית בונה מודל שחוזה אם בעיטה תהיה גול?", a: "<p>פיצ׳רים: מרחק, זווית, חלק הגוף, סוג המצב (משחק פתוח, כדור נייח, פנדל) וסוג המסירה. מודל בסיס של רגרסיה לוגיסטית בתוך Pipeline, ואחריו מודל עצים כמו XGBoost להשוואה. פיצול לפי עונות. הערכה עם log-loss, Brier ועקומת כיול, ולא עם דיוק. בסוף בודקים שסך ה־xG לקבוצה קרוב לסך השערים לאורך עונה.</p>" },
    { q: "מה ההבדל בין bias ל־variance?", a: "<p>Bias הוא שגיאה שנובעת מהנחות פשטניות מדי, וזו התאמת חסר. Variance הוא רגישות יתר לנתוני האימון הספציפיים, וזו התאמת יתר. מודל מורכב יותר מוריד bias ומעלה variance. רגולריזציה, יותר נתונים ושיטות ensemble עוזרים למצוא את האיזון.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "pytorch",
  group: "dataml",
  title: "PyTorch",
  cv: ["PyTorch"],
  usedIn: [],
  risk: "אף פרויקט בקו״ח לא משתמש ב־PyTorch. אם תשאיר, תהיה מוכן לכתוב לולאת אימון מאפס ולהסביר כל שורה בה.",
  dropAdvice: "אם אתה לא מכיר את לולאת האימון בעל־פה, עדיף להוריד. ממילא אין פרויקט שמגבה את זה",
  summary: "ספריית הלמידה העמוקה. השאלה הקלאסית היא ״תכתוב לולאת אימון ותסביר כל שורה״.",
  html: `
<section>
  <h2>טנזורים ו־autograd</h2>
  <p><strong>טנזור</strong> הוא כמו מערך NumPy, עם שני הבדלים: הוא יכול לרוץ על GPU, והוא יודע לחשב נגזרות אוטומטית (<strong>autograd</strong>).</p>
<pre><code>import torch
w = torch.tensor(2.0, requires_grad=True)
loss = (w * 3 - 5) ** 2
loss.backward()          # מחשב dloss/dw ושומר אותו ב־w.grad
w.grad                   # tensor(6.)

device = "cuda" if torch.cuda.is_available() else "cpu"
x = torch.randn(64, 10).to(device)   # המודל והנתונים חייבים להיות על אותו device</code></pre>
  <p>במהלך החישוב PyTorch בונה גרף חישוב דינמי, ו־<code>backward()</code> עובר עליו אחורה לפי כלל השרשרת. זה האלגוריתם <strong>backpropagation</strong>.</p>
</section>

<section>
  <h2>הגדרת מודל</h2>
<pre><code>import torch.nn as nn

class OutcomeNet(nn.Module):              # חוזה ניצחון בית, תיקו או ניצחון חוץ
    def __init__(self, n_features):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 3),             # 3 לוגיטים, בלי softmax
        )

    def forward(self, x):
        return self.net(x)</code></pre>
</section>

<section>
  <h2>לולאת האימון, שורה אחרי שורה</h2>
<pre><code>from torch.utils.data import DataLoader, TensorDataset

loader = DataLoader(TensorDataset(X_train, y_train), batch_size=64, shuffle=True)
model = OutcomeNet(X_train.shape[1]).to(device)
loss_fn = nn.CrossEntropyLoss()           # מקבל לוגיטים גולמיים
opt = torch.optim.Adam(model.parameters(), lr=1e-3)

for epoch in range(20):                   # epoch = מעבר אחד על כל הנתונים
    model.train()                         # מצב אימון: dropout פעיל
    for xb, yb in loader:                 # batch = 64 דוגמאות
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()                   # 1. איפוס גרדיאנטים, כי הם מצטברים
        logits = model(xb)                # 2. מעבר קדימה
        loss = loss_fn(logits, yb)        # 3. חישוב השגיאה
        loss.backward()                   # 4. חישוב גרדיאנטים
        opt.step()                        # 5. עדכון משקלים

    model.eval()                          # מצב הערכה: dropout כבוי
    with torch.no_grad():                 # בלי גרף חישוב, חוסך זיכרון וזמן
        val_loss = loss_fn(model(X_val.to(device)), y_val.to(device))</code></pre>
</section>

<section>
  <h2>פונקציות שגיאה, ומה שחשוב לזכור</h2>
  <ul>
    <li><code>CrossEntropyLoss</code> לסיווג מרובה מחלקות. הוא מפעיל softmax בעצמו, ולכן <strong>לא שמים softmax בסוף המודל</strong>.</li>
    <li><code>BCEWithLogitsLoss</code> לסיווג בינארי. הוא מקבל לוגיט ומפעיל סיגמואיד בפנים, בצורה יציבה נומרית.</li>
    <li><code>MSELoss</code> לרגרסיה.</li>
    <li><strong>קצב למידה</strong> גבוה מדי גורם לשגיאה לקפוץ או להתבדר, ונמוך מדי גורם להתכנסות איטית מאוד.</li>
    <li>שגיאה שמתחילה ב־<code>Expected all tensors</code> ומדברת על device אומרת שהמודל על GPU והנתונים על CPU, או להפך.</li>
  </ul>
</section>
`,
  tip: "אם תשאיר את זה, תגיד בכנות איפה השתמשת: קורס, תרגיל או ניסוי. אחר כך תראה שאתה יודע לכתוב לולאת אימון מהזיכרון. אם תתבקש לכתוב אותה על הלוח, תגיד את חמשת השלבים בקול: zero_grad, forward, loss, backward, step.",
  questions: [
    {
      q: "למה קוראים ל־<code>optimizer.zero_grad()</code> בכל איטרציה?",
      choices: ["כדי לאתחל את המשקלים", "כי ב־PyTorch גרדיאנטים מצטברים (נסכמים) מקריאה לקריאה של backward", "כדי לשחרר זיכרון של GPU", "זה לא באמת נחוץ"],
      answer: 1,
      explain: "בלי האיפוס, הגרדיאנט של ה־batch הנוכחי יתווסף לגרדיאנטים של כל ה־batches הקודמים, והעדכונים יהיו שגויים."
    },
    {
      q: "מודל סיווג לשלוש מחלקות עם <code>nn.CrossEntropyLoss</code>. מה צריך להיות בסוף ה־forward?",
      choices: ["שכבת <code>nn.Softmax</code>", "לוגיטים גולמיים מתוך <code>nn.Linear</code>, בלי softmax", "שכבת <code>nn.Sigmoid</code>", "פונקציית argmax"],
      answer: 1,
      explain: "הפונקציה CrossEntropyLoss מפעילה log-softmax בעצמה. softmax נוסף ״ישטח״ את הפלט ויפגע באימון. בזמן חיזוי מפעילים softmax ידנית אם צריך הסתברויות."
    },
    {
      q: "מה עושה <code>model.eval()</code>?",
      choices: ["מריץ את המודל על נתוני המבחן", "מעביר שכבות כמו Dropout ו־BatchNorm להתנהגות של זמן חיזוי", "מכבה את חישוב הגרדיאנטים", "שומר את המודל לקובץ"],
      answer: 1,
      explain: "הפונקציה eval לא מכבה גרדיאנטים. בשביל זה משתמשים ב־<code>torch.no_grad()</code>. בזמן הערכה משתמשים בשניהם."
    },
    {
      q: "מה הסדר הנכון בתוך לולאת האימון?",
      choices: ["forward, backward, zero_grad, step", "zero_grad, forward, loss, backward, step", "step, forward, loss, backward", "forward, step, loss, backward"],
      answer: 1,
      explain: "מאפסים, מחשבים פלט ושגיאה, מחשבים גרדיאנטים, ורק אז מעדכנים. אפשר גם לאפס בסוף האיטרציה, העיקר שהאיפוס יקרה לפני ה־backward הבא."
    },
    {
      q: "מה ההבדל בין epoch ל־batch?",
      choices: ["אלה מילים נרדפות", "ה־batch הוא קבוצה קטנה של דוגמאות לעדכון אחד, וה־epoch הוא מעבר מלא על כל נתוני האימון", "ה־epoch קטן מה־batch", "ה־batch הוא מספר השכבות"],
      answer: 1,
      explain: "עם 6,400 דוגמאות ו־batch בגודל 64, כל epoch כולל 100 עדכוני משקלים."
    },
    {
      q: "השגיאה בזמן האימון קופצת בפראות ולפעמים הופכת ל־NaN. מה החשוד הראשון?",
      choices: ["קצב למידה גבוה מדי", "batch גדול מדי", "יותר מדי epochs", "המודל קטן מדי"],
      answer: 0,
      explain: "קצב למידה גבוה גורם לצעדים שמדלגים מעבר למינימום ומתבדרים. מורידים אותו פי 10 ובודקים שוב, ואפשר גם להוסיף gradient clipping."
    },
    {
      q: "למה עוטפים את חלק ההערכה ב־<code>with torch.no_grad():</code>?",
      choices: ["כדי שהמודל לא ישתנה", "כדי לא לבנות גרף חישוב: חוסך זיכרון וזמן כשלא צריך גרדיאנטים", "כדי להפעיל dropout", "זה חובה, אחרת תהיה שגיאה"],
      answer: 1,
      explain: "המשקלים לא משתנים גם בלעדיו, כי אין קריאה ל־step. אבל ללא no_grad, PyTorch שומר את כל ערכי הביניים בשביל backward שלא יקרה."
    }
  ],
  open: [
    { q: "תכתוב לולאת אימון בסיסית ותסביר כל שורה.", a: "<p>ראה את הקוד בחלק של לולאת האימון למעלה. הנקודות שחייבים להזכיר: model.train() ו־model.eval(), איפוס גרדיאנטים, העברה ל־device, שימוש ב־no_grad בזמן הערכה, ומעקב אחרי שגיאת הוולידציה כדי לעצור מוקדם (early stopping) כשהיא מפסיקה לרדת.</p>" },
    { q: "מתי תבחר ברשת נוירונים ומתי ב־XGBoost?", a: "<p>בנתונים טבלאיים, כמו סטטיסטיקות משחק, XGBoost בדרך כלל מנצח או משתווה, הוא מהיר יותר לאמן וקל יותר להסביר. רשת נוירונים עדיפה בנתונים לא מובנים: טקסט (למשל סנטימנט של ציוצים), תמונות ווידאו, רצפים ארוכים כמו נתוני מעקב אחרי שחקנים, או כשיש הרבה מאוד נתונים.</p>" }
  ]
},

/* ======================================================================= */
{
  id: "xgboost",
  group: "dataml",
  title: "XGBoost",
  cv: ["XGBoost"],
  usedIn: ["barca"],
  summary: "המודל שמנצח בנתונים טבלאיים, ומופיע בפרויקט של ברצלונה. ישאלו מה זה boosting ואיך מכוונים אותו.",
  html: `
<section>
  <h2>מעץ החלטה ליער ול־boosting</h2>
  <p><strong>עץ החלטה</strong> מפצל את הנתונים בכל צומת לפי פיצ׳ר וסף, למשל ״מרחק קטן מ־12 מטר?״, ובוחר את הפיצול שמשפר הכי הרבה את טוהר הקבוצות. עץ עמוק לבד נוטה מאוד להתאמת יתר. יש שתי דרכים לשלב הרבה עצים:</p>
  <div class="tbl-scroll"><table>
    <tr><th>שיטה</th><th>איך</th><th>דוגמה</th></tr>
    <tr><td><strong>Bagging</strong></td><td>עצים עמוקים שנבנים במקביל, כל אחד על מדגם אקראי. מצביעים או ממצעים. מוריד variance.</td><td>Random Forest</td></tr>
    <tr><td><strong>Boosting</strong></td><td>עצים רדודים שנבנים <strong>ברצף</strong>, וכל עץ לומד לתקן את השגיאות של העצים הקודמים. מוריד bias.</td><td>XGBoost, LightGBM</td></tr>
  </table></div>
</section>

<section>
  <h2>איך gradient boosting עובד</h2>
  <ol>
    <li>מתחילים מחיזוי בסיסי, למשל אחוז הניצחונות הממוצע.</li>
    <li>מחשבים לכל דוגמה את הגרדיאנט של פונקציית השגיאה. ברגרסיה עם MSE זו פשוט השארית: האמת פחות החיזוי.</li>
    <li>מאמנים עץ קטן שחוזה את הגרדיאנטים האלה.</li>
    <li>מוסיפים את העץ לחיזוי, מוכפל ב־<strong>learning rate</strong> קטן.</li>
    <li>חוזרים על זה מאות פעמים.</li>
  </ol>
  <p>מה ש־XGBoost מוסיף על זה: <strong>רגולריזציה</strong> מובנית על מבנה העצים, שימוש בנגזרת שנייה, טיפול מובנה בערכים חסרים (הוא לומד לאיזה צד לשלוח אותם), דגימת שורות ועמודות, ובניית עצים מקבילית ומהירה.</p>
</section>

<section>
  <h2>היפר־פרמטרים חשובים</h2>
<pre><code>from xgboost import XGBClassifier

model = XGBClassifier(
    n_estimators=2000,        # מקסימום עצים. early stopping יעצור לפני
    learning_rate=0.03,       # נמוך יותר = צריך יותר עצים, אבל בדרך כלל מכליל טוב יותר
    max_depth=4,              # עומק כל עץ. הפרמטר הראשי נגד התאמת יתר
    subsample=0.8,            # אחוז השורות לכל עץ
    colsample_bytree=0.8,     # אחוז הפיצ'רים לכל עץ
    reg_lambda=1.0,           # רגולריזציית L2
    eval_metric="logloss",
    early_stopping_rounds=50, # עוצר אם 50 עצים ברצף לא שיפרו את הוולידציה
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
model.best_iteration</code></pre>
  <p>מודלי עצים <strong>לא צריכים נרמול</strong> של פיצ׳רים, כי פיצול לפי סף לא מושפע מקנה מידה.</p>
</section>

<section>
  <h2>חשיבות פיצ׳רים, והזהירות שבה</h2>
  <p>המאפיין <code>feature_importances_</code> מבוסס על gain, כלומר כמה כל פיצ׳ר שיפר את הפיצולים. יש לזה שתי בעיות: הוא מוטה לפיצ׳רים עם הרבה ערכים שונים, וכשיש שני פיצ׳רים מתואמים, כמו בעיטות ובעיטות למסגרת, החשיבות מתחלקת ביניהם באופן שרירותי. כלי טוב יותר הוא <strong>SHAP</strong>, שנותן לכל חיזוי בנפרד את התרומה של כל פיצ׳ר.</p>
</section>
`,
  tip: "תסביר את ההבדל בין bagging ל־boosting במשפט אחד, ותגיד מה עשית: ״בפרויקט של ברצלונה השתמשתי ב־XGBoost עם early stopping על סט ולידציה, ובדקתי את החשיבות עם SHAP ולא רק עם feature_importances_, כי חלק מהפיצ׳רים היו מתואמים״.",
  questions: [
    {
      q: "מה ההבדל המהותי בין Random Forest ל־XGBoost?",
      choices: ["אין הבדל, שניהם יערות", "ב־Random Forest העצים נבנים במקביל וממוצעים. ב־XGBoost הם נבנים ברצף, וכל עץ מתקן את השגיאות של הקודמים", "ב־XGBoost יש רק עץ אחד", "ב־Random Forest אין עצים"],
      answer: 1,
      explain: "שיטת bagging מורידה variance, ושיטת boosting מורידה bias. לכן ב־boosting משתמשים בעצים רדודים, וב־Random Forest בעצים עמוקים."
    },
    {
      q: "הורדת את <code>learning_rate</code> מ־0.3 ל־0.03. מה צפוי לקרות?",
      choices: ["יידרשו פחות עצים", "יידרשו בערך פי 10 עצים, ולרוב ההכללה תשתפר", "המודל יתאים יותר מדי", "אין השפעה"],
      answer: 1,
      explain: "כל עץ תורם פחות, ולכן צריך יותר מהם. הצעדים הקטנים מקטינים בדרך כלל התאמת יתר. early stopping ימצא את מספר העצים המתאים."
    },
    {
      q: "המודל מתאים יותר מדי לנתוני האימון. מה <strong>לא</strong> יעזור?",
      choices: ["הקטנת <code>max_depth</code>", "הגדלת <code>max_depth</code> ל־15", "הוספת <code>subsample=0.8</code>", "שימוש ב־early stopping"],
      answer: 1,
      explain: "עצים עמוקים יותר מגדילים את המורכבות ומחריפים את התאמת היתר. שלוש האפשרויות האחרות הן כלים מקובלים נגדה."
    },
    {
      q: "האם צריך לנרמל פיצ׳רים (StandardScaler) לפני XGBoost?",
      choices: ["כן, תמיד", "לא. פיצולים לפי סף לא מושפעים מקנה המידה של הפיצ׳ר", "רק לפיצ׳רים קטגוריאליים", "רק אם יש ערכים חסרים"],
      answer: 1,
      explain: "בשביל עץ, הסף ״מרחק קטן מ־12״ שקול לסף ״מרחק מנורמל קטן מ־0.4״. נרמול חשוב לרגרסיה לוגיסטית, לרשתות נוירונים ולמודלים מבוססי מרחק כמו KNN."
    },
    {
      q: "איך XGBoost מטפל בערכים חסרים?",
      choices: ["זורק שגיאה", "לומד בכל פיצול כיוון ברירת מחדל (שמאל או ימין) לשורות עם ערך חסר", "ממלא אותם באפס", "מוחק את השורות"],
      answer: 1,
      explain: "זו אחת התכונות שהפכו את XGBoost לפופולרי. לפעמים העובדה שערך חסר היא בעצמה מידע."
    },
    {
      q: "על מה מבוסס early stopping?",
      choices: ["על השגיאה בנתוני האימון", "על השגיאה בסט ולידציה נפרד: עוצרים כשהיא מפסיקה להשתפר", "על זמן ריצה", "על מספר הפיצ׳רים"],
      answer: 1,
      explain: "שגיאת האימון ממשיכה לרדת כמעט תמיד. רק סט ולידציה מגלה מתי התחילה התאמת יתר."
    },
    {
      q: "שני פיצ׳רים מתואמים מאוד, ״בעיטות״ ו״בעיטות למסגרת״. מה יקרה ל־<code>feature_importances_</code>?",
      choices: ["שניהם יקבלו חשיבות גבוהה", "החשיבות עלולה להתחלק ביניהם באופן שרירותי, וכל אחד ייראה פחות חשוב ממה שהוא", "אחד מהם יימחק אוטומטית", "אין השפעה"],
      answer: 1,
      explain: "לכן מתייחסים לחשיבות הזו בזהירות, ומשתמשים ב־SHAP או ב־permutation importance כדי לקבל תמונה אמינה יותר."
    }
  ],
  open: [
    { q: "הסבר gradient boosting למישהו שלא מכיר.", a: "<p>מתחילים מניחוש פשוט. מסתכלים איפה טעינו, ובונים עץ קטן שלומד לתקן בדיוק את הטעויות האלה. מוסיפים חלק קטן מהתיקון שלו לניחוש, ושוב מסתכלים איפה טועים. אחרי מאות סבבים, הסכום של כל התיקונים הקטנים הוא מודל חזק מאוד.</p>" },
    { q: "איך כיוונת את המודל בפרויקט של ברצלונה?", a: "<p>תבנית תשובה: התחלתי ממודל בסיס של רגרסיה לוגיסטית. אחר כך XGBoost עם learning rate נמוך ו־early stopping, וחיפוש קטן על max_depth ועל subsample בתוך אימות צולב לפי זמן. השוויתי log-loss מול המודל הבסיסי, ובדקתי SHAP כדי לוודא שהמודל לומד דברים הגיוניים ולא דליפה. <strong>תתאים את זה למה שבאמת עשית.</strong></p>" }
  ]
},

/* ======================================================================= */
{
  id: "streamlit",
  group: "dataml",
  title: "Streamlit",
  cv: ["Streamlit"],
  usedIn: [],
  riskPill: "לא מופיע בקו״ח",
  risk: "בקו״ח אין פרויקט שמזכיר Streamlit, אבל באתר שלך יש דשבורד NBA שבנוי בו (nba-dashboard-ramshiri.streamlit.app). תוסיף אותו לקו״ח כפרויקט, וזה כבר לא סיכון. זה גם פרויקט כדורסל, ו־Marquee מתרחבת לכדורסל.",
  dropAdvice: "לפני שאתה מוריד, זכור שיש לך דשבורד NBA ב־Streamlit. עדיף להוסיף אותו לקו״ח מאשר להוריד את המיומנות",
  summary: "דרך מהירה להפוך סקריפט Python לאפליקציית דאטה אינטראקטיבית. העיקר להבין את מודל ההרצה מחדש ואת ה־caching.",
  html: `
<section>
  <h2>מודל ההרצה, וזה כל הסוד</h2>
  <p>אפליקציית Streamlit היא סקריפט Python רגיל. <strong>בכל אינטראקציה של משתמש, כמו הזזת סליידר או לחיצה על כפתור, כל הסקריפט רץ מחדש מלמעלה למטה.</strong> כל ווידג׳ט פשוט מחזיר את הערך הנוכחי שלו.</p>
<pre><code>import streamlit as st
import pandas as pd

st.title("EPL xG Explorer")
team = st.sidebar.selectbox("Team", teams)          # מחזיר את הבחירה הנוכחית
min_xg = st.slider("Minimum xG", 0.0, 1.0, 0.1)

df = load_shots()                                   # ירוץ שוב בכל אינטראקציה, אלא אם עושים cache
view = df[(df.team == team) &amp; (df.xg &gt;= min_xg)]

col1, col2 = st.columns(2)
col1.metric("Shots", len(view))
col2.metric("Total xG", round(view.xg.sum(), 2))
st.dataframe(view)
st.plotly_chart(make_shot_map(view))</code></pre>
  <p>מריצים עם <code>streamlit run app.py</code>.</p>
</section>

<section>
  <h2>מטמון</h2>
  <p>בגלל שהכול רץ מחדש, טעינת נתונים כבדה תקרה בכל קליק. לכן יש שני דקורטורים של cache:</p>
<pre><code>@st.cache_data(ttl=600)          # לנתונים: DataFrame, תוצאת API, JSON
def load_shots():                # מחזיר העתק בכל קריאה, ולכן בטוח לשנות אותו
    return pd.read_sql("SELECT * FROM shots", engine)

@st.cache_resource               # למשאבים משותפים: חיבור למסד, מודל ML טעון
def get_model():                 # מחזיר את אותו אובייקט לכל המשתמשים
    return joblib.load("xg_model.pkl")</code></pre>
  <p>המטמון נשמר לפי הארגומנטים של הפונקציה ולפי הקוד שלה. <code>ttl</code> קובע אחרי כמה שניות הנתונים נחשבים ישנים, וזה חשוב לנתונים חיים.</p>
</section>

<section>
  <h2>מצב בין הרצות</h2>
  <p>משתנה רגיל מתאפס בכל הרצה. כדי לזכור משהו בין הרצות, למשל אילו משחקים המשתמש סימן, משתמשים ב־<code>st.session_state</code>, שהוא מילון ששייך לכל משתמש בנפרד.</p>
<pre><code>if "favorites" not in st.session_state:
    st.session_state.favorites = []
if st.button("Add to favorites"):
    st.session_state.favorites.append(match_id)</code></pre>
</section>

<section>
  <h2>מתי כן ומתי לא</h2>
  <ul>
    <li><strong>מתאים</strong>: דשבורדים פנימיים, הדגמת מודל, כלי ניתוח לצוות, אבטיפוס מהיר. בלי HTML ובלי JavaScript.</li>
    <li><strong>פחות מתאים</strong>: אתר ציבורי עם הרבה משתמשים, עיצוב מותאם אישית מאוד, או לוגיקה מורכבת של ממשק. כל משתמש מחזיק חיבור ותהליך בשרת, וההרצה מחדש של כל הסקריפט לא יעילה בקנה מידה גדול.</li>
  </ul>
</section>
`,
  tip: "הדבר הראשון שתגיד: ״כל אינטראקציה מריצה את הסקריפט מחדש, ולכן cache_data לנתונים, cache_resource לחיבורים ולמודלים, ו־session_state למצב של המשתמש״. אם יש לך אפליקציית Streamlit מהפרויקטים, תציין אותה. אם אין, שקול להוסיף קישור לאחת לקו״ח.",
  questions: [
    {
      q: "מה קורה כשמשתמש מזיז סליידר באפליקציית Streamlit?",
      choices: ["רק הפונקציה שקשורה לסליידר רצה", "כל הסקריפט רץ מחדש מלמעלה למטה, עם הערך החדש של הסליידר", "הדף נטען מחדש בדפדפן", "שום דבר עד שלוחצים על כפתור שליחה"],
      answer: 1,
      explain: "זה מודל ההרצה של Streamlit, ולכן חייבים cache לפעולות כבדות. מגרסה 1.37 אפשר להגביל הרצה מחדש לחלק מהדף עם <code>st.fragment</code>."
    },
    {
      q: "פונקציה שמושכת DataFrame ממסד נתונים. איזה דקורטור מתאים?",
      choices: ["<code>@st.cache_resource</code>", "<code>@st.cache_data</code>", "<code>@st.session_state</code>", "אין צורך בדקורטור"],
      answer: 1,
      explain: "הדקורטור cache_data מיועד לנתונים שאפשר להעתיק, והוא מחזיר העתק לכל קריאה. כך משתמש אחד לא ישנה בטעות את הנתונים של משתמש אחר."
    },
    {
      q: "מודל ML כבד שנטען מקובץ, או חיבור למסד נתונים. איזה דקורטור מתאים?",
      choices: ["<code>@st.cache_data</code>", "<code>@st.cache_resource</code>", "<code>@functools.lru_cache</code> בלבד", "שום דקורטור, כי זה איטי בכל מקרה"],
      answer: 1,
      explain: "הדקורטור cache_resource מחזיק אובייקט אחד משותף בלי להעתיק אותו. זה בדיוק מה שצריך למשאבים שלא אמורים להשתכפל."
    },
    {
      q: "המשתמש לוחץ על ״הוסף למועדפים״, אבל הרשימה מתרוקנת בכל קליק. מה הפתרון?",
      choices: ["משתנה גלובלי", "לשמור את הרשימה ב־<code>st.session_state</code>", "להשתמש ב־<code>@st.cache_data</code>", "לכתוב לקובץ"],
      answer: 1,
      explain: "משתנה רגיל מאותחל בכל הרצה. המילון session_state נשמר בין הרצות, ונפרד לכל משתמש. משתנה גלובלי היה משותף לכל המשתמשים."
    },
    {
      q: "בדשבורד של תוצאות חיות, הנתונים ב־cache מתעדכנים רק אחרי ריסטרט. מה לשנות?",
      choices: ["להוריד את ה־cache לגמרי", "להוסיף <code>ttl</code> לדקורטור, למשל ttl=30", "להשתמש ב־cache_resource", "להריץ שוב את streamlit run"],
      answer: 1,
      explain: "הפרמטר ttl גורם לערך במטמון לפוג אחרי מספר השניות שנקבע. כך יש איזון בין עדכניות לעומס על המקור."
    },
    {
      q: "לאיזה שימוש Streamlit הכי פחות מתאים?",
      choices: ["דשבורד פנימי לצוות", "הדגמה של מודל xG", "אתר ציבורי עם עשרות אלפי משתמשים בו־זמנית ועיצוב מותאם לחלוטין", "כלי ניתוח לסקאוטים"],
      answer: 2,
      explain: "הוא מצוין לאפליקציות דאטה פנימיות ולאבטיפוסים. לאתר ציבורי בקנה מידה גדול בונים backend עם API ו־frontend נפרד."
    }
  ],
  open: [
    { q: "מה ההבדל בין cache_data ל־cache_resource?", a: "<p>הדקורטור cache_data שומר תוצאה שאפשר לבצע לה serialization, כמו DataFrame או JSON, ומחזיר העתק בכל קריאה. הדקורטור cache_resource שומר אובייקט אחד משותף לכל המשתמשים והסשנים, כמו חיבור למסד או מודל טעון, בלי להעתיק אותו.</p>" }
  ]
}
);
