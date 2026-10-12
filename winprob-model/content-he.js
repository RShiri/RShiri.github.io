/* Hebrew version of the win-probability training story. Blocks are matched by their
   English text (see /assets/brand/pages-he.js); RS_I18N covers short labels and the
   table text the page script writes after loading model_params.json. */
window.RS_HE_BLOCKS = [
  ["XEPL · XLALIGA · XWORLDCUPTWIT · live-pipeline — how the win-prob model was trained",
   "XEPL · XLALIGA · XWORLDCUPTWIT · live-pipeline – איך אומן מודל הסתברות הניצחון"],
  ["One model, four sites", "מודל אחד,<br><span class=\"num\">ארבעה</span> אתרים"],
  ["The in-play win-probability model behind the live pipeline and all three dashboards",
   "מודל הסתברות הניצחון בזמן משחק, שמאחורי ה־Pipeline החי ושלושת הדשבורדים, אומן על כל משחק שאי פעם גרדתי: <b style=\"color:var(--paper)\">3,272 משחקים ו־82,310 בעיטות</b> – ארבע עונות של הפרמייר ליג ולה ליגה, ועוד מונדיאל 2018, 2022 ו־2026. העמוד הזה מספר את סיפור ההתאמה: הנתונים, השיטה, ובדיקת העבר (back-test) הכנה."],
  ["the whole idea in 20 seconds", "כל הרעיון ב־20 שניות"],
  ["Before kick-off, the model expects a goals rate for each team",
   "לפני שריקת הפתיחה, המודל מצפה ל<b>קצב שערים</b> לכל קבוצה – שנלמד מכל 82,310 הבעיטות, במשקל גבוה יותר לכושר האחרון."],
  ["During the match, the score, the clock and recent xG turn that rate into",
   "במהלך המשחק, <b>התוצאה, השעון וה־xG (שערים צפויים) האחרון</b> הופכים את הקצב הזה ל־P(בית) / P(תיקו) / P(חוץ), דקה אחר דקה."],
  ["One fit ships everywhere: the pipeline demo, this site, and the EPL, La Liga",
   "התאמה אחת יוצאת לכל מקום: הדמו של ה־Pipeline, האתר הזה, והדשבורדים של הפרמייר ליג, לה ליגה והמונדיאל – כולם קוראים את <b>אותם מספרים</b>."],
  ["3,272 matches", "<b>3,272</b> משחקים"],
  ["82,310 shots", "<b>82,310</b> בעיטות"],
  ["109 teams fitted", "<b>109</b> קבוצות בהתאמה"],
  ["3 competitions, never mixed", "<b>3</b> מסגרות, אף פעם לא מעורבבות"],

  ["01 the data", "<span class=\"stage-no\">01</span> הנתונים"],
  ["Five corpora, one schema", "חמישה קורפוסים, סכמה אחת"],
  ["Each of my scrapers writes one small JS file per match, and they all share one schema.",
   "כל אחד מהסקרייפרים שלי כותב קובץ JS קטן אחד לכל משחק, וכולם חולקים סכמה אחת. המקריות הזו של עקביות היא מה שמאפשר מודל אחד: טוען הקורפוס יכול לקרוא משחק של ברנלי מ־2022 וחצי גמר מונדיאל 2026 עם אותו קוד. כל אחת מ־82,310 הבעיטות נושאת את שני הדברים שהמודל צריך – <b>דקה</b> ו<b>ערך xG</b> (מ<a href=\"../xg-model/\">מודל ה־xG שלי, שמוסבר בעמוד האח</a>)."],
  ["corpus", "קורפוס"], ["coverage", "כיסוי"], ["matches", "משחקים"], ["shots", "בעיטות"],
  ["seasons 2022-23 → 2025-26", "עונות 2022-23 עד 2025-26"],
  ["full tournament", "הטורניר המלא"],
  ["WC World Cup 2018", "<span class=\"chip wc\">WC</span><b>מונדיאל 2018</b>"],
  ["WC World Cup 2022", "<span class=\"chip wc\">WC</span><b>מונדיאל 2022</b>"],
  ["WC World Cup 2026", "<span class=\"chip wc\">WC</span><b>מונדיאל 2026</b>"],
  ["5,666(three editions)", "5,666<br><span style=\"font-size:11px; color:var(--paper-faint);\">(שלוש מהדורות)</span>"],
  ["total", "סה״כ"],
  ["Source repos: github.com/RShiri/XEPL",
   "מאגרי מקור: <a href=\"https://github.com/RShiri/XEPL\" rel=\"noopener\">github.com/RShiri/XEPL</a> · <a href=\"https://github.com/RShiri/XLALIGA\" rel=\"noopener\">github.com/RShiri/XLALIGA</a> · <a href=\"https://github.com/RShiri/XWORLDCUPTWIT\" rel=\"noopener\">github.com/RShiri/XWORLDCUPTWIT</a> (מונדיאל 2018 ו־2022 נמצאים תחת <span class=\"mono\">editions/</span> בתוך הדשבורד של 2026)."],

  ["02 data flow", "<span class=\"stage-no\">02</span> זרימת הנתונים"],
  ["From three repos to four live sites", "משלושה מאגרים לארבעה אתרים חיים"],
  ["One script, calibrate.py, reads every corpus, fits the model,",
   "סקריפט אחד, <span class=\"mono\" style=\"color:var(--paper)\">calibrate.py</span>, קורא כל קורפוס, מתאים את המודל וכותב את הפרמטרים לכל מקום שבו משתמשים בהם. התאמה מחדש אחרי נתוני משחקים חדשים היא פקודה אחת."],
  ["refit: python3 live-pipeline/tradepipe/calibrate.py",
   "התאמה מחדש: <span style=\"color:var(--paper)\">python3 live-pipeline/tradepipe/calibrate.py</span> – התאמה אחת, ארבעה צרכנים"],

  ["03 the method", "<span class=\"stage-no\">03</span> השיטה"],
  ["Six decisions, step by step", "שש החלטות, צעד אחר צעד"],
  ["The fit is a Dixon-Coles-lite: nothing exotic, every piece checkable.",
   "ההתאמה היא Dixon-Coles מקוצר: שום דבר אקזוטי, כל חלק ניתן לבדיקה. כל החלטה למטה קיימת כי הנתונים הכריחו אותה."],
  ["Each competition gets its own baseline μ.", "לכל מסגרת יש בסיס μ משלה."],
  ["An EPL goal habitat is not a World Cup goal habitat",
   "בית הגידול של שערים בפרמייר ליג אינו זה של המונדיאל – הגנה שונה, מה שעל הכף שונה, קצבי כיבוש שונים. לכן המודל אף פעם לא משווה קבוצה ל„כדורגל באופן כללי”, אלא רק לבסיס של המסגרת שלה: ה־xG הממוצע המשוקלל של קבוצה אחת ל־90 דקות. בהתאמה: <b>פרמייר ליג 1.42</b>, <b>לה ליגה 1.29</b>, <b>מונדיאל 1.37</b>."],
  ["Team rates are shrunk toward that baseline.", "קצבי הקבוצות מכווצים לעבר הבסיס הזה."],
  ["A club seen for 152 matches earns its rate.",
   "מועדון שנצפה ב־152 משחקים מרוויח את הקצב שלו. נבחרת מונדיאל שנצפתה שלוש פעמים – לא. לכן קצב ההתקפה של כל קבוצה נמשך לעבר μ בעזרת <b>k משחקים מדומים</b> של ראיות ממוצעות (כיווץ אמפירי־בייסיאני). k כוונן על {1, 2, 4, 8, 16} לפי ציון Brier על נתונים שהוחזקו בצד: <b>k&nbsp;=&nbsp;1</b> ניצח. הקבוצות מופרדות לפי מסגרת – <span class=\"mono\">EPL/Arsenal</span> ו־<span class=\"mono\">WC/Argentina</span> אף פעם לא מתערבבות."],
  ["Old seasons fade at 0.8 per season.", "עונות ישנות דועכות בקצב 0.8 לעונה."],
  ["Every match is weighted 0.8 seasons ago, so 2025-26",
   "כל משחק מקבל משקל <b>0.8<sup>מספר העונות שעברו</sup></b>, כך שהכושר של 2025-26 שולט בקצב של מועדון, ו־2022-23 עוד לוחשת. מהדורות המונדיאל מזדקנות בצעדים של 4 שנים – מונדיאל 2022 נמצא עונה אחת אחרי מונדיאל 2026, לא ארבע."],
  ["Home advantage is measured, not assumed.", "יתרון הבית נמדד, לא מונח."],
  ["Fitted as sqrt(mean home xG / mean away xG) over league matches only:",
   "מותאם כ־<span class=\"mono\">sqrt(mean home xG / mean away xG)</span> על משחקי ליגה בלבד: <b>×1.13</b> לקצב של הקבוצה המארחת. מגרשי המונדיאל ניטרליים, ולכן שם התוספת כבויה לגמרי."],
  ["The clock is the market's clock, not the referee's.", "השעון הוא השעון של השוק, לא של השופט."],
  ["The model prices the 1X2 (90 min) market.",
   "המודל מתמחר את שוק ה־<b>1X2 (90 דקות)</b>. תוספת הזמן נחשבת: שער ניצחון ב־90+4′ מכריע את השוק, ולכן האירועים האלה מקופלים לדקה 90. הארכה בשלבי הנוקאאוט של המונדיאל אף פעם לא נכנסת – משחק שקול אחרי 90′ מוכרע כתיקו, לא משנה מה קורה אחר כך."],
  ["Pre-match rates hand off to the live model.", "הקצבים שלפני המשחק עוברים למודל החי."],
  ["The fitted rates set each team's pre-match expectation,",
   "הקצבים המותאמים קובעים את הציפייה של כל קבוצה לפני המשחק, ואז הנוסחה החיה משקללת אותה עם המומנטום במשחק (קצב ה־xG ב־15 הדקות האחרונות, משקל w&nbsp;=&nbsp;0.35) ומכפילה לפי הדקות שנותרו. הטיפול המלא בזמן משחק – רשת Poisson, יחסים, הכרעה – מוסבר ב<a href=\"../live-pipeline/\">דמו ה־Pipeline החי</a>, אז לא נלמד אותו כאן שוב."],

  ["04 fitted values", "<span class=\"stage-no\">04</span> הערכים המותאמים"],
  ["What the fit actually learned", "מה ההתאמה למדה בפועל"],
  ["These numbers load live from assets/data/winprob/model_params.json",
   "המספרים האלה נטענים בזמן אמת מ־<span class=\"mono\" style=\"color:var(--paper); overflow-wrap:anywhere;\">assets/data/winprob/model_params.json</span> – בדיוק הקובץ שה־Pipeline קורא. att &gt; 1 כובשת יותר מהבסיס של המסגרת שלה; def &lt; 1 סופגת פחות."],
  ["μ EPLxG per team per match", "μ פרמייר ליג<br>xG לקבוצה למשחק"],
  ["μ La Liga", "μ לה ליגה"],
  ["μ World Cup", "μ מונדיאל"],
  ["home advantage(leagues only)", "יתרון בית<br>(ליגות בלבד)"],
  ["top 5 attacks · all competitions", "5 ההתקפות המובילות · כל המסגרות"],
  ["top 5 defences · lowest def", "5 ההגנות המובילות · def הנמוך ביותר"],
  ["team", "קבוצה"],
  ["Small-sample World Cup sides can post extreme rates",
   "נבחרות מונדיאל עם מדגם קטן יכולות להציג קצבים קיצוניים – ה־2.14 של טורקיה מגיע משלושה משחקים, ה־1.94 של ליברפול מ־152. זה מחיר הכיווץ, גלוי לעין: k&nbsp;=&nbsp;1 שומר על קצבים רגישים, ועמודת ה־<span class=\"mono\">n</span> אומרת כמה לסמוך על כל אחד. בסך הכול הותאמו <span id=\"f-count\">109</span> קבוצות."],

  ["05 the honest benchmark", "<span class=\"stage-no\">05</span> מבחן ההשוואה הכן"],
  ["Tested blind on 864 matches it never saw", "נבדק בעיוורון על 864 משחקים שלא ראה מעולם"],
  ["The design in one sentence: train on 2,408 matches",
   "התכנון במשפט אחד: <b>אימון על 2,408 משחקים</b> (עונות הליגה 2022-23 עד 2024-25 ועוד מונדיאל 2018 ו־2022), ואז <b>בדיקה עיוורת על 864</b> (עונות הליגה 2025-26 ועוד מונדיאל 2026). ציון Brier מול תוצאת 90 הדקות, נבדק בשבע נקודות במשחק – נמוך יותר עדיף."],
  ["variant", "גרסה"],
  ["Both model variants beat always quoting the base rates, at every checkpoint.",
   "שתי גרסאות המודל מנצחות ציטוט קבוע של שיעורי הבסיס, בכל נקודת בדיקה. והחלק הכן: <b>הגרסה בלי מומנטום (w&nbsp;=&nbsp;0) עוקפת קצת את שקלול המומנטום</b> בקנה המידה הזה. חמש־עשרה דקות של xG הן אות רועש – קבוצה יכולה להיראות דומיננטית רבע שעה ולא להראות כלום בסיום – ו־w&nbsp;=&nbsp;0.35 נותן לו משקל יתר. פרמטרי הייצור שומרים על w&nbsp;=&nbsp;0.35 כדי שהמומנטום יישאר גלוי בדמו החי, אבל הטבלה מציגה את שתיהן כדי שהמספר לא יימכר ביותר ממה שהוא."],

  ["06 where it runs", "<span class=\"stage-no\">06</span> איפה הוא רץ"],
  ["The same numbers, live in four places", "אותם מספרים, חיים בארבעה מקומות"],
  ["Live pipeline demo", "דמו ה־Pipeline החי"],
  ["Prices the 1X2 market minute by minute as recorded World Cup matches replay",
   "מתמחר את שוק ה־1X2 דקה אחר דקה, בזמן שמשחקי מונדיאל מוקלטים מתנגנים מחדש דרך פיד יחסים בסגנון סוכנות הימורים."],
  ["EPL dashboard", "דשבורד הפרמייר ליג"],
  ["Drives the in-play win-probability strip on every Premier League match page,",
   "מפעיל את רצועת הסתברות הניצחון בזמן משחק בכל עמוד משחק של הפרמייר ליג, כולל יתרון הבית."],
  ["La Liga dashboard", "דשבורד לה ליגה"],
  ["Same model, La Liga's own baseline μ", "אותו מודל, עם בסיס μ של לה ליגה – ציר הזמן של הסתברות הניצחון בכל עמוד משחק."],
  ["World Cup dashboard", "דשבורד המונדיאל"],
  ["Win probability on every WC match page", "הסתברות ניצחון בכל עמוד משחק במונדיאל – מגרשים ניטרליים, וההארכה נשארת מחוץ לשוק 90 הדקות."],
  ["fit on 3,272 matches · 82,310 shots", "התאמה על <b>3,272</b> משחקים · <b>82,310</b> בעיטות"],
  ["shrinkage k = 1", "כיווץ <b>k = 1</b>"],
  ["recency 0.8/season", "דעיכה <b>0.8</b>/עונה"],
  ["holdout n = 864", "בדיקה <b>n = 864</b>"],
  ["One fit, never two competing sets of numbers:",
   "התאמה אחת, אף פעם לא שתי קבוצות מספרים מתחרות: דמו ה־Pipeline, העמוד הזה ושלושת הדשבורדים קוראים את אותם פרמטרים, שמופקים מחדש בסקריפט אחד. עמוד אח: <a href=\"../xg-model/\">איך עובד מודל ה־xG שמאחורי כל ערך בעיטה</a> · חזרה ל<a href=\"../\">תיק העבודות</a>."]
];

window.RS_I18N = Object.assign(window.RS_I18N || {}, {
  /* data-flow diagram (SVG text) */
  "normalize · dedup": "נרמול · הסרת כפילויות",
  "market clock (90′)": "שעון השוק (90′)",
  "competition from directory": "מסגרת לפי תיקייה",
  "fit μ, att/def, hfa": "התאמת μ, att/def, hfa",
  "tune k by holdout Brier": "כוונון k לפי Brier על holdout",
  "back-test, then refit on all": "בדיקת עבר, ואז התאמה על הכול",
  "→ live-pipeline demo": "← דמו live-pipeline",
  "→ this page's tables": "← הטבלאות בעמוד הזה",
  "one JSON, versioned v2": "JSON אחד, גרסה v2",
  "→ XEPL match pages": "← עמודי משחק XEPL",
  "→ XLALIGA match pages": "← עמודי משחק XLALIGA",
  "→ XWORLDCUPTWIT match pages": "← עמודי משחק XWORLDCUPTWIT",
  /* tables written by the page script */
  "model (w = 0.35)": "מודל (w = 0.35)",
  "no momentum (w = 0)": "בלי מומנטום (w = 0)",
  "constant base-rate": "שיעור בסיס קבוע",
  "La Liga": "לה ליגה"
});

window.RS_ABOUT = {
  en: {
    title: "How the win-probability model was trained",
    intro: "The story of one fit: the in-play win-probability model shared by the live pipeline and the EPL, La Liga and World Cup dashboards.",
    sections: [
      { h: "Data", p: "3,272 matches and 82,310 shots from five corpora with one schema: four EPL and La Liga seasons (2022-23 to 2025-26) and the 2018, 2022 and 2026 World Cups." },
      { h: "Method", p: "A Dixon-Coles-lite fit: a baseline μ per competition, team attack/defence rates shrunk toward it (k = 1), seasons weighted 0.8 per year, a measured home advantage (×1.13, leagues only), and the 90-minute market clock." },
      { h: "Honest test", p: "Trained on 2,408 matches, tested blind on 864. Both model variants beat the constant base rate at every checkpoint; the no-momentum variant edges out the momentum blend, and the page reports both." }
    ]
  },
  he: {
    title: "איך אומן מודל הסתברות הניצחון",
    intro: "הסיפור של התאמה אחת: מודל הסתברות הניצחון בזמן משחק, שמשותף ל־Pipeline החי ולדשבורדים של הפרמייר ליג, לה ליגה והמונדיאל.",
    sections: [
      { h: "נתונים", p: "3,272 משחקים ו־82,310 בעיטות מחמישה קורפוסים עם סכמה אחת: ארבע עונות של הפרמייר ליג ולה ליגה (2022-23 עד 2025-26) ומונדיאל 2018, 2022 ו־2026." },
      { h: "שיטה", p: "התאמה בסגנון Dixon-Coles מקוצר: בסיס μ לכל מסגרת, קצבי התקפה/הגנה של קבוצות שמכווצים לעברו (k = 1), משקל 0.8 לכל עונה אחורה, יתרון בית שנמדד (×1.13, בליגות בלבד) ושעון השוק של 90 דקות." },
      { h: "בדיקה כנה", p: "אימון על 2,408 משחקים ובדיקה עיוורת על 864. שתי גרסאות המודל מנצחות את שיעור הבסיס הקבוע בכל נקודת בדיקה; הגרסה בלי מומנטום עוקפת קצת את שקלול המומנטום, והעמוד מציג את שתיהן." }
    ]
  }
};
