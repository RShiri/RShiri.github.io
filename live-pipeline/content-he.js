/* Hebrew version of the MatchFeed live-pipeline page. Blocks are matched by their English
   text (see /assets/brand/pages-he.js); RS_I18N covers short labels and the strings the
   replay script writes while it runs. Team/player names, numbers and code stay as they are. */
window.RS_HE_BLOCKS = [
  ["MatchFeed · live odds pipeline", "MatchFeed · Pipeline יחסים חי"],
  ["One match feed in, live 1X2 prices out.", "פיד משחק אחד נכנס, <span class=\"grad\">מחירי 1X2 חיים יוצאים.</span>"],
  ["A real-time sports data pipeline built like a sportsbook odds feed.",
   "Pipeline נתוני ספורט בזמן אמת, שבנוי כמו פיד יחסים של סוכנות הימורים. Producer מנגן מחדש משחקי מונדיאל כהודעות בסגנון RabbitMQ. Consumer בונה מחדש את מצב המשחק מההודעות ומתמחר את שוק ה־1X2 בזמן אמת, דקה אחר דקה, עם מודל מבוסס xG (שערים צפויים) שכויל על 82,000 בעיטות מארבע עונות של הפרמייר ליג ולה ליגה ועוד שלושה מונדיאלים."],
  ["Python, stdlib-only core, runnable locally — source on GitHub.",
   "Python, ליבה בספרייה הסטנדרטית בלבד, רץ מקומית – <a href=\"https://github.com/RShiri/RShiri.github.io/tree/main/live-pipeline\">הקוד ב־GitHub</a>."],

  ["01 · architecture", "01 · ארכיטקטורה"],
  ["How the messages flow", "איך ההודעות זורמות"],
  ["Everything is a JSON envelope on a topic exchange.",
   "הכול הוא מעטפת JSON על topic exchange. ה־Producer מפרסם את פיד המשחק, ה־Consumer מתמחר אותו ומפרסם בחזרה שווקים. אם Consumer מצטרף באיחור, הוא מזהה את הפער במספרי הרצף של ההודעות ומבקש מה־Producer תמונת מצב (snapshot) – ואז ממשיך כאילו היה שם כל הזמן."],

  ["02 · live replay", "02 · הילוך חוזר חי"],
  ["Watch the consumer price a match", "צפו ב־Consumer מתמחר משחק"],
  ["These are the exact timelines the pipeline produced for eight recorded World Cup matches.",
   "אלה בדיוק צירי הזמן שה־Pipeline הפיק לשמונה משחקי מונדיאל מוקלטים. בחרו משחק ולחצו נגן: קווי הסתברות הניצחון מתקדמים על שעון המשחק האמיתי – דרך תוספת הזמן של המחצית השנייה ועד שריקת הסיום, והלאה עד 120' כשמשחק נוקאאוט הלך להארכה. היחסים ההוגנים מצוטטים מחדש כל דקה כל עוד שוק ה־1X2 (90 דקות) פתוח; הוא מוכרע בשריקה, או בדקה 90' כשיש הארכה."],
  ["1 · home", "1 · בית"],
  ["X · draw", "X · תיקו"],
  ["2 · away", "2 · חוץ"],
  ["Event feed", "פיד אירועים"],
  ["Full time", "סיום"],
  ["Couldn't load the match data.",
   "לא הצלחנו לטעון את נתוני המשחק. אם פתחתם את הקובץ ישירות (כתובת <code>file://</code>), דפדפנים חוסמים טעינות מקומיות – הריצו <code>python3 -m http.server</code> מתיקיית השורש של המאגר ופתחו את <code>http://localhost:8000/live-pipeline/</code>. שאר העמוד עובד גם בלי זה."],

  ["03 · the model", "03 · המודל"],
  ["One formula, repriced every minute", "נוסחה אחת, תמחור מחדש כל דקה"],
  ["The consumer keeps a running estimate of how many goals each team is",
   "ה־Consumer מחזיק הערכה שוטפת של כמה שערים כל קבוצה עוד צפויה לכבוש, ואז הופך אותה להסתברויות 1X2 בעזרת רשת Poisson."],
  ["λ_prematch is what we expected before kick-off,",
   "<b>λ_prematch</b> הוא מה שציפינו לו לפני שריקת הפתיחה, מקצבי ההתקפה וההגנה המותאמים של כל קבוצה – מכויל לכל מסגרת על 3,272 משחקים (פרמייר ליג + לה ליגה 2022–26 ועוד מונדיאל 2018/22/26), במשקל לפי עדכניות כך שהכושר הנוכחי שולט."],
  ["pace is what's actually happening: the team's xG over the last 15 minutes,",
   "<b>pace</b> הוא מה שקורה בפועל: ה־xG של הקבוצה ב־15 הדקות האחרונות, לדקה. קבוצה שמפציצה את השער מקבלת הערכת שערים נותרים גבוהה יותר; „אוטובוס חונה” מוריד אותה."],
  ["w = 0.35 blends the two. The (90 − t)/90 factor", "<b>w = 0.35</b> משקלל בין השניים. המקדם (90 − t)/90 רק מתאים אותו לדקות שנותרו."],
  ["With a remaining-goals rate for each side, a small Poisson grid",
   "עם קצב שערים נותרים לכל צד, <b>רשת Poisson</b> קטנה סוכמת P(ניצחון), P(תיקו), P(הפסד) על כל תוצאה אפשרית שנותרה, מעל התוצאה הנוכחית."],
  ["Home advantage is a fitted ×1.13 boost", "<b>יתרון בית</b> הוא תוספת מותאמת של <span id=\"hfaVal\" class=\"mono\">×1.13</span> לקצב של הקבוצה המארחת, שנלמדה ממשחקי ליגה. מגרשי המונדיאל ניטרליים, ולכן ההילוכים החוזרים בעמוד הזה לא משתמשים בה."],
  ["90-minute market convention: stoppage time counts",
   "<b>מוסכמת שוק 90 הדקות</b>: תוספת הזמן נחשבת – כל משחק ליגה ומשחק בית במונדיאל מקפלים אירועי 90+' לדקה 90 – אבל הארכה אף פעם לא. משחק נוקאאוט שקול אחרי 90' מוכרע כ־X, לא משנה מה קורה אחר כך."],
  ["Full training story - how the model was fit on 82k shots ↗",
   "<a href=\"../winprob-model/\">סיפור האימון המלא – איך המודל הותאם על 82 אלף בעיטות ↗</a>"],
  ["Fitted team rates — top 3 attacks per competition", "קצבי קבוצות מותאמים – 3 ההתקפות המובילות בכל מסגרת"],
  ["team", "קבוצה"],
  ["A curated slice of the 109 fitted teams.", "מבחר מתוך <span id=\"teamCount\">109</span> הקבוצות המותאמות. att &gt; 1 כובשת יותר מהבסיס של המסגרת שלה (<span id=\"muLine\" class=\"mono\">μ: EPL 1.42 · La Liga 1.29 · WC 1.37</span> שערים לקבוצה למשחק), def &lt; 1 סופגת פחות. הקצבים משוקללים לפי עדכניות (0.8 לעונה) עם כיווץ אמפירי־בייסיאני, כך שקבוצות ליגה עם 152 משחקים מוערכות הרבה יותר טוב מנבחרות מונדיאל עם קומץ משחקים."],
  ["Held-out Brier score by checkpoint", "ציון Brier על נתונים שהוחזקו בצד, לפי נקודת בדיקה"],
  ["Lower is better. Honest holdout:",
   "נמוך יותר עדיף. בדיקה כנה: אימון על 2022–25 ועוד מונדיאל 2018/22, בדיקה עיוורת על 2025–26 ומונדיאל 2026 – <span id=\"brierN\">864</span> משחקים. שתי הגרסאות מנצחות בבירור ציטוט קבוע של שיעורי הבסיס, וההסתייגות הכנה: בקנה המידה הזה הגרסה בלי מומנטום (w = 0) עוקפת קצת את שקלול המומנטום ברוב נקודות הבדיקה – xG של 15 דקות הוא רועש. הדמו החי שומר על w = 0.35 כדי שהמומנטום יישאר גלוי."],

  ["04 · on the wire", "04 · על הקו"],
  ["What a message looks like", "איך נראית הודעה"],
  ["Every message is the same envelope: a Header with a type,",
   "כל הודעה היא אותה מעטפת: Header עם סוג, מספר רצף לכל משחק וחותמות זמן, ו־Body של אירועים. אלה דוגמאות מייצגות."],

  ["05 · run it yourself", "05 · הריצו בעצמכם"],
  ["Same pipeline, in your terminal", "אותו Pipeline, בטרמינל שלכם"],
  ["Stdlib only — no installs needed for the in-memory broker.",
   "ספרייה סטנדרטית בלבד – לא צריך להתקין כלום בשביל ה־broker שבזיכרון. הבדיקות מכסות את המודל, את חוזי ההודעות ואת מסלול השחזור מ־snapshot."],
  ["Want the real broker? docker run -p",
   "רוצים broker אמיתי? <code>docker run -p 5672:5672 rabbitmq:3</code>, <code>pip install pika</code>, ואז הוסיפו <code>--broker rabbit</code> לכל הרצה – אותן הודעות, הפעם על topic exchange אמיתי של RabbitMQ."]
];

window.RS_I18N = Object.assign(window.RS_I18N || {}, {
  /* match picker meta, written by the script */
  "Jun 17 · Group Stage": "17 ביוני · שלב הבתים", "Jun 22 · Group Stage": "22 ביוני · שלב הבתים",
  "Jun 28 · Group Stage": "28 ביוני · שלב הבתים", "Jul 3 · Round of 32": "3 ביולי · שלב ה־32",
  "Jul 7 · Round of 16": "7 ביולי · שמינית הגמר", "Jul 12 · Quarterfinal": "12 ביולי · רבע הגמר",
  "Jul 15 · Semifinal": "15 ביולי · חצי הגמר", "Jul 19 · Final": "19 ביולי · הגמר",
  /* replay controls + panels */
  "▶ Play": "▶ נגן", "⏸ Pause": "⏸ השהה", "↺ Replay": "↺ שוב",
  "Play replay": "נגן הילוך חוזר", "Pause replay": "השהה הילוך חוזר",
  "Choose a match to replay": "בחרו משחק להילוך חוזר", "Playback speed": "מהירות ניגון", "Scrub match minute": "גלילה לדקת משחק",
  "draw": "תיקו", "Draw": "תיקו",
  "Kick-off pending — press play.": "לפני שריקת הפתיחה – לחצו נגן.",
  "No events yet.": "עוד אין אירועים.",
  "The market settles at the final whistle.": "השוק מוכרע בשריקת הסיום.",
  "90' · market settles": "90' · השוק מוכרע",
  /* model table + Brier legend/chart */
  "model (w = 0.35)": "מודל (w = 0.35)", "no momentum (w = 0)": "בלי מומנטום (w = 0)", "constant base-rate": "שיעור בסיס קבוע",
  "La Liga": "לה ליגה",
  /* architecture diagram (SVG text) */
  "match JSON replay, min 0→90": "הילוך חוזר של JSON, דקות 0–90",
  "also serves snapshots (RPC)": "מגיש גם snapshots (RPC)",
  "in-memory broker or RabbitMQ": "broker בזיכרון או RabbitMQ",
  "MatchState + xG-driven model": "MatchState + מודל מבוסס xG",
  "reprices 1X2 every minute": "מתמחר 1X2 מחדש כל דקה",
  "late joiner detects MsgSeq gap → GetSnapshot RPC": "מצטרף מאוחר מזהה פער MsgSeq ← GetSnapshot RPC",
  "snapshot.<fixture> → replies with current state → consumer resumes": "snapshot.<fixture> ← מחזיר את המצב הנוכחי ← ה־Consumer ממשיך",
  "message types on the feed:": "סוגי ההודעות בפיד:",
  /* message samples */
  "Type 2 · score, xG, incidents": "סוג 2 · תוצאה, xG, אירועים",
  "Type 3 · the consumer's output": "סוג 3 · הפלט של ה־Consumer",
  "Type 35 · match over, market resolved": "סוג 35 · המשחק נגמר, השוק הוכרע",
  /* footer */
  "← Back to projects": "← חזרה לפרויקטים",
  "Ram Shiri · MatchFeed, a live odds pipeline": "Ram Shiri · MatchFeed, Pipeline יחסים חי"
});

window.RS_ABOUT = {
  en: {
    title: "MatchFeed, a live odds pipeline",
    intro: "A real-time sports data pipeline modelled on a sportsbook odds feed, written in Python with a stdlib-only core.",
    sections: [
      { h: "Pipeline", p: "A producer replays recorded World Cup matches as JSON messages on a topic exchange (in-memory or RabbitMQ). A consumer rebuilds match state, prices the 1X2 market every minute and publishes market updates; a late joiner recovers with a snapshot RPC." },
      { h: "Model", p: "Each team's remaining goals blend a pre-match rate (fitted on 3,272 matches) with the last 15 minutes of xG (w = 0.35), scaled to the minutes left; a Poisson grid turns them into home/draw/away probabilities. The market is the 90-minute one: extra time never counts." },
      { h: "How to read the replay", p: "Pick a match and press play: the lines are win probabilities over the real match clock, the cards show fair decimal odds, the feed lists goals and shots, and the market settles at the whistle (or at 90' before extra time)." }
    ]
  },
  he: {
    title: "MatchFeed, Pipeline יחסים חי",
    intro: "Pipeline נתוני ספורט בזמן אמת, שבנוי כמו פיד יחסים של סוכנות הימורים, כתוב ב־Python עם ליבה בספרייה הסטנדרטית בלבד.",
    sections: [
      { h: "ה־Pipeline", p: "Producer מנגן מחדש משחקי מונדיאל מוקלטים כהודעות JSON על topic exchange (בזיכרון או RabbitMQ). Consumer בונה מחדש את מצב המשחק, מתמחר את שוק ה־1X2 כל דקה ומפרסם עדכוני שוק; מצטרף מאוחר משתחזר בעזרת snapshot RPC." },
      { h: "המודל", p: "השערים הנותרים של כל קבוצה משקללים קצב שלפני המשחק (שהותאם על 3,272 משחקים) עם ה־xG של 15 הדקות האחרונות (w = 0.35), מותאם לדקות שנותרו; רשת Poisson הופכת אותם להסתברויות בית/תיקו/חוץ. זה שוק 90 הדקות: הארכה אף פעם לא נחשבת." },
      { h: "איך לקרוא את ההילוך החוזר", p: "בחרו משחק ולחצו נגן: הקווים הם הסתברויות ניצחון על שעון המשחק האמיתי, הכרטיסים מראים יחסים עשרוניים הוגנים, הפיד מציג שערים ובעיטות, והשוק מוכרע בשריקה (או בדקה 90' לפני הארכה)." }
    ]
  }
};
