"""
Generate a 1000-question Japanese practice test for Quizbee.
- Prompts are in hiragana / katakana / kanji only
- English / romaji appears only in answer options and explanations
- draw_count = 5, randomize_questions = true  → 5 random questions per session

Run:  python3 gen_japanese.py
Output: japanese_practice.json  (import via Tests → ↑ Import)
"""

import json, random

# ---------------------------------------------------------------------------
# Question bank data
# ---------------------------------------------------------------------------

# (kanji_or_kana, reading_romaji, english)
VOCAB = [
    # N5 vocabulary
    ("あ行", None, None),  # section headers — skipped below
    ("あ", "a", "ah / the vowel A"),
    ("あい", "ai", "love"),
    ("あお", "ao", "blue / green"),
    ("あか", "aka", "red"),
    ("あき", "aki", "autumn / fall"),
    ("あく", "aku", "to open"),
    ("あける", "akeru", "to open (something)"),
    ("あさ", "asa", "morning"),
    ("あし", "ashi", "leg / foot"),
    ("あした", "ashita", "tomorrow"),
    ("あそぶ", "asobu", "to play"),
    ("あたたかい", "atatakai", "warm"),
    ("あたま", "atama", "head"),
    ("あたらしい", "atarashii", "new"),
    ("あちら", "achira", "over there"),
    ("あつい", "atsui", "hot"),
    ("あに", "ani", "older brother"),
    ("あね", "ane", "older sister"),
    ("あの", "ano", "that (over there)"),
    ("あびる", "abiru", "to take a shower"),
    ("あぶない", "abunai", "dangerous"),
    ("あまい", "amai", "sweet"),
    ("あめ", "ame", "rain / candy"),
    ("あらう", "arau", "to wash"),
    ("ある", "aru", "to exist (inanimate)"),
    ("あるく", "aruku", "to walk"),
    ("いい", "ii", "good"),
    ("いいえ", "iie", "no"),
    ("いう", "iu", "to say"),
    ("いえ", "ie", "house"),
    ("いく", "iku", "to go"),
    ("いくら", "ikura", "how much"),
    ("いし", "ishi", "stone"),
    ("いす", "isu", "chair"),
    ("いそがしい", "isogashii", "busy"),
    ("いつ", "itsu", "when"),
    ("いつも", "itsumo", "always"),
    ("いぬ", "inu", "dog"),
    ("いま", "ima", "now"),
    ("いもうと", "imouto", "younger sister"),
    ("いる", "iru", "to exist (animate)"),
    ("いれる", "ireru", "to put in"),
    ("うえ", "ue", "above / up"),
    ("うごく", "ugoku", "to move"),
    ("うた", "uta", "song"),
    ("うたう", "utau", "to sing"),
    ("うち", "uchi", "home / inside"),
    ("うまい", "umai", "delicious / skillful"),
    ("うみ", "umi", "sea / ocean"),
    ("うる", "uru", "to sell"),
    ("えいが", "eiga", "movie"),
    ("えき", "eki", "train station"),
    ("おいしい", "oishii", "delicious"),
    ("おおい", "ooi", "many"),
    ("おおきい", "ookii", "big"),
    ("おかあさん", "okaasan", "mother"),
    ("おかね", "okane", "money"),
    ("おきる", "okiru", "to wake up"),
    ("おく", "oku", "to put / place"),
    ("おくる", "okuru", "to send"),
    ("おさけ", "osake", "alcohol / sake"),
    ("おしえる", "oshieru", "to teach"),
    ("おとうさん", "otousan", "father"),
    ("おとうと", "otouto", "younger brother"),
    ("おとこ", "otoko", "man / male"),
    ("おとな", "otona", "adult"),
    ("おなか", "onaka", "stomach / belly"),
    ("おねえさん", "oneesan", "older sister (polite)"),
    ("おにいさん", "oniisan", "older brother (polite)"),
    ("おぼえる", "oboeru", "to remember / memorize"),
    ("おもい", "omoi", "heavy"),
    ("おもしろい", "omoshiroi", "interesting / funny"),
    ("およぐ", "oyogu", "to swim"),
    ("おわる", "owaru", "to finish / end"),
    ("かう", "kau", "to buy"),
    ("かえす", "kaesu", "to return (something)"),
    ("かえる", "kaeru", "to go home"),
    ("かお", "kao", "face"),
    ("かがく", "kagaku", "science / chemistry"),
    ("かく", "kaku", "to write"),
    ("かける", "kakeru", "to hang / make (a call)"),
    ("かさ", "kasa", "umbrella"),
    ("かぜ", "kaze", "wind / cold (illness)"),
    ("かぞく", "kazoku", "family"),
    ("かた", "kata", "person (polite)"),
    ("がっこう", "gakkou", "school"),
    ("かなしい", "kanashii", "sad"),
    ("かばん", "kaban", "bag"),
    ("かみ", "kami", "paper / hair / god"),
    ("からだ", "karada", "body"),
    ("かるい", "karui", "light (weight)"),
    ("かわ", "kawa", "river"),
    ("かわいい", "kawaii", "cute"),
    ("きいろ", "kiiro", "yellow"),
    ("きく", "kiku", "to listen / to ask"),
    ("きた", "kita", "north"),
    ("きっさてん", "kissaten", "café / coffee shop"),
    ("きって", "kitte", "stamp (postage)"),
    ("きのう", "kinou", "yesterday"),
    ("きもの", "kimono", "kimono"),
    ("きる", "kiru", "to cut / to wear"),
    ("きれい", "kirei", "pretty / clean"),
    ("ぎんこう", "ginkou", "bank"),
    ("くだもの", "kudamono", "fruit"),
    ("くに", "kuni", "country"),
    ("くらい", "kurai", "dark / gloomy"),
    ("くる", "kuru", "to come"),
    ("くるま", "kuruma", "car"),
    ("けいさつ", "keisatsu", "police"),
    ("げんき", "genki", "healthy / energetic"),
    ("こうえん", "kouen", "park"),
    ("こうこう", "koukou", "high school"),
    ("こえ", "koe", "voice"),
    ("ここ", "koko", "here"),
    ("こたえる", "kotaeru", "to answer"),
    ("こどもの", "kodomo", "child"),
    ("ことば", "kotoba", "word / language"),
    ("こむ", "komu", "to be crowded"),
    ("ごみ", "gomi", "garbage / trash"),
    ("こわい", "kowai", "scary"),
    ("さかな", "sakana", "fish"),
    ("さく", "saku", "to bloom"),
    ("さむい", "samui", "cold (weather)"),
    ("さんぽ", "sanpo", "a walk / stroll"),
    ("しごと", "shigoto", "work / job"),
    ("しずか", "shizuka", "quiet"),
    ("した", "shita", "below / under"),
    ("じてんしゃ", "jitensha", "bicycle"),
    ("しぬ", "shinu", "to die"),
    ("しまる", "shimaru", "to close (intrans.)"),
    ("しめる", "shimeru", "to close (trans.)"),
    ("しゃしん", "shashin", "photograph"),
    ("じゅぎょう", "jugyou", "class / lesson"),
    ("しろ", "shiro", "white"),
    ("しんせつ", "shinsetsu", "kind / generous"),
    ("すき", "suki", "like / fond of"),
    ("すくない", "sukunai", "few / little"),
    ("すむ", "sumu", "to live (in a place)"),
    ("する", "suru", "to do"),
    ("せ", "se", "height / stature"),
    ("せんせい", "sensei", "teacher"),
    ("そこ", "soko", "there"),
    ("そと", "soto", "outside"),
    ("そば", "soba", "near / soba noodles"),
    ("たかい", "takai", "expensive / tall"),
    ("たつ", "tatsu", "to stand up"),
    ("たのしい", "tanoshii", "fun / enjoyable"),
    ("たべる", "taberu", "to eat"),
    ("たまご", "tamago", "egg"),
    ("だれ", "dare", "who"),
    ("ちかい", "chikai", "near / close"),
    ("ちかてつ", "chikatetsu", "subway"),
    ("ちず", "chizu", "map"),
    ("ちいさい", "chiisai", "small"),
    ("つかう", "tsukau", "to use"),
    ("つかれる", "tsukareru", "to get tired"),
    ("つき", "tsuki", "moon / month"),
    ("つくる", "tsukuru", "to make / create"),
    ("つめたい", "tsumetai", "cold (to the touch)"),
    ("てがみ", "tegami", "letter (mail)"),
    ("でかける", "dekakeru", "to go out"),
    ("でる", "deru", "to leave / go out"),
    ("どうぶつ", "doubutsu", "animal"),
    ("とおい", "tooi", "far"),
    ("とける", "tokeru", "to melt"),
    ("とし", "toshi", "year / age / city"),
    ("としょかん", "toshokan", "library"),
    ("とぶ", "tobu", "to fly / jump"),
    ("ともだち", "tomodachi", "friend"),
    ("とる", "toru", "to take"),
    ("なおす", "naosu", "to fix / heal"),
    ("なく", "naku", "to cry / to sing (animal)"),
    ("なつ", "natsu", "summer"),
    ("なまえ", "namae", "name"),
    ("にし", "nishi", "west"),
    ("にほん", "nihon", "Japan"),
    ("にもつ", "nimotsu", "luggage / baggage"),
    ("ぬぐ", "nugu", "to take off (clothes)"),
    ("ねこ", "neko", "cat"),
    ("ねる", "neru", "to sleep"),
    ("のる", "noru", "to ride / get on"),
    ("のむ", "nomu", "to drink"),
    ("はなす", "hanasu", "to speak / talk"),
    ("はる", "haru", "spring (season)"),
    ("はれる", "hareru", "to clear up (weather)"),
    ("ひがし", "higashi", "east"),
    ("ひく", "hiku", "to pull / to play (instrument)"),
    ("ひくい", "hikui", "low"),
    ("びょうき", "byouki", "illness / sickness"),
    ("ひろい", "hiroi", "wide / spacious"),
    ("ふく", "fuku", "to blow / clothes"),
    ("ふとい", "futoi", "thick / fat"),
    ("ふゆ", "fuyu", "winter"),
    ("へた", "heta", "bad at / unskillful"),
    ("べんきょう", "benkyou", "study"),
    ("ほしい", "hoshii", "want / desire"),
    ("ほん", "hon", "book"),
    ("まえ", "mae", "front / before"),
    ("まがる", "magaru", "to turn"),
    ("まち", "machi", "town / city"),
    ("まつ", "matsu", "to wait"),
    ("みじかい", "mijikai", "short"),
    ("みず", "mizu", "water"),
    ("みせ", "mise", "shop / store"),
    ("みせる", "miseru", "to show"),
    ("みち", "michi", "road / path"),
    ("みなみ", "minami", "south"),
    ("みる", "miru", "to see / watch"),
    ("むずかしい", "muzukashii", "difficult"),
    ("むすこ", "musuko", "son"),
    ("むすめ", "musume", "daughter"),
    ("めがね", "megane", "glasses / spectacles"),
    ("もつ", "motsu", "to hold / have"),
    ("もらう", "morau", "to receive"),
    ("やさしい", "yasashii", "kind / easy"),
    ("やすい", "yasui", "cheap / easy"),
    ("やすむ", "yasumu", "to rest"),
    ("やま", "yama", "mountain"),
    ("ゆうめい", "yuumei", "famous"),
    ("ゆき", "yuki", "snow"),
    ("よい", "yoi", "good"),
    ("よむ", "yomu", "to read"),
    ("よる", "yoru", "night"),
    ("りょうり", "ryouri", "cooking / cuisine"),
    ("りょこう", "ryokou", "travel / trip"),
    ("わかい", "wakai", "young"),
    ("わかる", "wakaru", "to understand"),
    ("わすれる", "wasureru", "to forget"),
    ("わたし", "watashi", "I / me"),
]

# Kanji with readings and meanings
KANJI = [
    ("日", "にち／ひ", "nichi / hi", "day / sun"),
    ("月", "げつ／つき", "getsu / tsuki", "month / moon"),
    ("火", "か／ひ", "ka / hi", "fire / Tuesday"),
    ("水", "すい／みず", "sui / mizu", "water / Wednesday"),
    ("木", "もく／き", "moku / ki", "tree / Thursday"),
    ("金", "きん／かね", "kin / kane", "gold / money / Friday"),
    ("土", "ど／つち", "do / tsuchi", "earth / soil / Saturday"),
    ("山", "さん／やま", "san / yama", "mountain"),
    ("川", "かわ", "kawa", "river"),
    ("田", "た／でん", "ta / den", "rice field"),
    ("人", "じん／ひと", "jin / hito", "person"),
    ("口", "こう／くち", "kou / kuchi", "mouth"),
    ("手", "しゅ／て", "shu / te", "hand"),
    ("目", "もく／め", "moku / me", "eye"),
    ("耳", "じ／みみ", "ji / mimi", "ear"),
    ("足", "そく／あし", "soku / ashi", "foot / leg"),
    ("力", "りょく／ちから", "ryoku / chikara", "power / strength"),
    ("大", "だい／おお", "dai / oo", "big / large"),
    ("小", "しょう／ちい", "shou / chii", "small"),
    ("中", "ちゅう／なか", "chuu / naka", "middle / inside"),
    ("上", "じょう／うえ", "jou / ue", "above / up"),
    ("下", "か／した", "ka / shita", "below / down"),
    ("左", "さ／ひだり", "sa / hidari", "left"),
    ("右", "う／みぎ", "u / migi", "right"),
    ("前", "ぜん／まえ", "zen / mae", "front / before"),
    ("後", "ご／あと", "go / ato", "after / behind"),
    ("東", "とう／ひがし", "tou / higashi", "east"),
    ("西", "せい／にし", "sei / nishi", "west"),
    ("南", "なん／みなみ", "nan / minami", "south"),
    ("北", "ほく／きた", "hoku / kita", "north"),
    ("国", "こく／くに", "koku / kuni", "country"),
    ("語", "ご", "go", "language"),
    ("字", "じ", "ji", "character / letter"),
    ("文", "ぶん／もん", "bun / mon", "sentence / text"),
    ("本", "ほん", "hon", "book / origin"),
    ("名", "めい／な", "mei / na", "name"),
    ("年", "ねん／とし", "nen / toshi", "year"),
    ("時", "じ／とき", "ji / toki", "time / hour"),
    ("間", "かん／ま", "kan / ma", "interval / space"),
    ("分", "ふん／ぶん", "fun / bun", "minute / part"),
    ("半", "はん", "han", "half"),
    ("毎", "まい", "mai", "every"),
    ("週", "しゅう", "shuu", "week"),
    ("今", "こん／いま", "kon / ima", "now / this"),
    ("先", "せん／さき", "sen / saki", "ahead / before / tip"),
    ("来", "らい／く", "rai / ku", "come / next"),
    ("行", "こう／い", "kou / i", "go / conduct"),
    ("帰", "き／かえ", "ki / kae", "return home"),
    ("食", "しょく／た", "shoku / ta", "eat / food"),
    ("飲", "いん／の", "in / no", "drink"),
    ("見", "けん／み", "ken / mi", "see / look"),
    ("聞", "ぶん／き", "bun / ki", "hear / listen"),
    ("読", "どく／よ", "doku / yo", "read"),
    ("書", "しょ／か", "sho / ka", "write"),
    ("話", "わ／はな", "wa / hana", "talk / speak"),
    ("言", "げん／い", "gen / i", "say / word"),
    ("来", "らい／き", "rai / ki", "come"),
    ("出", "しゅつ／で", "shutsu / de", "exit / go out"),
    ("入", "にゅう／はい", "nyuu / hai", "enter"),
    ("立", "りつ／た", "ritsu / ta", "stand"),
    ("休", "きゅう／やす", "kyuu / yasu", "rest"),
    ("買", "ばい／か", "bai / ka", "buy"),
    ("売", "ばい／う", "bai / u", "sell"),
    ("使", "し／つか", "shi / tsuka", "use"),
    ("作", "さく／つく", "saku / tsuku", "make / create"),
    ("思", "し／おも", "shi / omo", "think"),
    ("知", "ち／し", "chi / shi", "know"),
    ("白", "はく／しろ", "haku / shiro", "white"),
    ("黒", "こく／くろ", "koku / kuro", "black"),
    ("赤", "せき／あか", "seki / aka", "red"),
    ("青", "せい／あお", "sei / ao", "blue / green"),
    ("学", "がく／まな", "gaku / mana", "study / learn"),
    ("校", "こう", "kou", "school"),
    ("先生", "せんせい", "sensei", "teacher"),
    ("学生", "がくせい", "gakusei", "student"),
    ("会社", "かいしゃ", "kaisha", "company"),
    ("電車", "でんしゃ", "densha", "train (electric)"),
    ("飛行機", "ひこうき", "hikouki", "airplane"),
    ("病院", "びょういん", "byouin", "hospital"),
    ("図書館", "としょかん", "toshokan", "library"),
    ("郵便局", "ゆうびんきょく", "yuubinkyoku", "post office"),
    ("大学", "だいがく", "daigaku", "university"),
    ("小学校", "しょうがっこう", "shougakkou", "elementary school"),
    ("中学校", "ちゅうがっこう", "chuugakkou", "middle school"),
    ("高校", "こうこう", "koukou", "high school"),
    ("新聞", "しんぶん", "shinbun", "newspaper"),
    ("雑誌", "ざっし", "zasshi", "magazine"),
    ("電話", "でんわ", "denwa", "telephone"),
    ("携帯", "けいたい", "keitai", "mobile phone"),
    ("食堂", "しょくどう", "shokudou", "cafeteria / dining hall"),
    ("銀行", "ぎんこう", "ginkou", "bank"),
    ("薬局", "やっきょく", "yakkyoku", "pharmacy"),
]

# Katakana words (katakana, romaji, english)
KATAKANA = [
    ("アイスクリーム", "aisu kuriimu", "ice cream"),
    ("アパート", "apaato", "apartment"),
    ("アルバイト", "arubaito", "part-time job"),
    ("インターネット", "intaanetto", "internet"),
    ("ウイスキー", "uisukii", "whisky"),
    ("エアコン", "eakon", "air conditioner"),
    ("エレベーター", "erebeetaa", "elevator"),
    ("オレンジ", "orenji", "orange"),
    ("カメラ", "kamera", "camera"),
    ("カレー", "karee", "curry"),
    ("ギター", "gitaa", "guitar"),
    ("コーヒー", "koohii", "coffee"),
    ("コンビニ", "konbini", "convenience store"),
    ("サッカー", "sakkaa", "soccer / football"),
    ("シャワー", "shawaa", "shower"),
    ("スーパー", "suupaa", "supermarket"),
    ("スキー", "sukii", "skiing"),
    ("スポーツ", "supootsu", "sports"),
    ("ストレス", "sutoresu", "stress"),
    ("セーター", "seetaa", "sweater"),
    ("テレビ", "terebi", "television"),
    ("デパート", "depaato", "department store"),
    ("ドア", "doa", "door"),
    ("トイレ", "toire", "toilet / restroom"),
    ("ノート", "nooto", "notebook"),
    ("バス", "basu", "bus"),
    ("パソコン", "pasokon", "personal computer"),
    ("ビール", "biiru", "beer"),
    ("ピアノ", "piano", "piano"),
    ("ファックス", "fakkusu", "fax"),
    ("プール", "puuru", "swimming pool"),
    ("ペン", "pen", "pen"),
    ("ホテル", "hoteru", "hotel"),
    ("ボールペン", "boorupen", "ballpoint pen"),
    ("マクドナルド", "makudonarudo", "McDonald's"),
    ("メニュー", "menyuu", "menu"),
    ("レストラン", "resutoran", "restaurant"),
    ("ロビー", "robii", "lobby"),
    ("ワイン", "wain", "wine"),
    ("アルコール", "arukooru", "alcohol"),
    ("シャツ", "shatsu", "shirt"),
    ("ジュース", "juusu", "juice"),
    ("タクシー", "takushii", "taxi"),
    ("チケット", "chiketto", "ticket"),
    ("テーブル", "teebu ru", "table"),
    ("ナイフ", "naifu", "knife"),
    ("フォーク", "fooku", "fork"),
    ("ミルク", "miruku", "milk"),
    ("ヨーロッパ", "yooroppa", "Europe"),
    ("アメリカ", "Amerika", "America / USA"),
    ("イギリス", "Igirisu", "UK / England"),
    ("フランス", "Furansu", "France"),
    ("ドイツ", "Doitsu", "Germany"),
    ("チョコレート", "chokoreeto", "chocolate"),
    ("サンドイッチ", "sandoicchi", "sandwich"),
    ("ハンバーガー", "hanbaagaa", "hamburger"),
    ("ピザ", "piza", "pizza"),
    ("スパゲッティ", "supagetti", "spaghetti"),
    ("アイスティー", "aisu tii", "iced tea"),
    ("コーラ", "koora", "cola"),
    ("ヨーグルト", "yooguruto", "yogurt"),
    ("バナナ", "banana", "banana"),
    ("トマト", "tomato", "tomato"),
    ("ピーマン", "piiman", "green pepper"),
    ("キャベツ", "kyabetsu", "cabbage"),
    ("サラダ", "sarada", "salad"),
    ("スープ", "suupu", "soup"),
    ("パン", "pan", "bread"),
    ("バター", "bataa", "butter"),
    ("チーズ", "chiizu", "cheese"),
    ("ケーキ", "keeki", "cake"),
    ("クッキー", "kukkii", "cookie"),
    ("アイスコーヒー", "aisu koohii", "iced coffee"),
    ("ランチ", "ranchi", "lunch"),
    ("ディナー", "dinaa", "dinner"),
    ("ブランチ", "buranchi", "brunch"),
    ("タオル", "taoru", "towel"),
    ("ベッド", "beddo", "bed"),
    ("ソファ", "sofa", "sofa"),
    ("カーテン", "kaaten", "curtains"),
    ("ランプ", "ranpu", "lamp"),
    ("ラジオ", "rajio", "radio"),
    ("ビデオ", "bideo", "video"),
    ("スクリーン", "sukuriin", "screen"),
    ("キーボード", "kiiboodo", "keyboard"),
    ("マウス", "mausu", "mouse (computer)"),
    ("プリンター", "purintaa", "printer"),
    ("ファイル", "fairu", "file"),
    ("メール", "meeru", "email"),
    ("パスワード", "pasuwaado", "password"),
    ("アプリ", "apuri", "app"),
    ("ゲーム", "geemu", "game"),
    ("アニメ", "anime", "anime"),
    ("マンガ", "manga", "manga"),
    ("コンサート", "konsaato", "concert"),
    ("パーティー", "paatii", "party"),
    ("ジム", "jimu", "gym"),
    ("ヨガ", "yoga", "yoga"),
    ("ダンス", "dansu", "dance"),
    ("スタジオ", "sutajio", "studio"),
    ("コート", "kooto", "coat / court"),
    ("スーツ", "suutsu", "suit"),
    ("ジャケット", "jaketto", "jacket"),
    ("スカート", "sukaato", "skirt"),
    ("ズボン", "zubon", "trousers / pants"),
]

# Particles (hiragana particle in context, english meaning, usage note in english)
PARTICLES = [
    ("は", "wa (topic marker)", "marks the topic of the sentence", "わたし__がくせいです。", "は"),
    ("が", "ga (subject marker)", "marks the grammatical subject", "ねこ__います。", "が"),
    ("を", "wo/o (object marker)", "marks the direct object", "りんご__たべます。", "を"),
    ("に", "ni (direction/time/location)", "indicates direction, time, or location", "がっこう__いきます。", "に"),
    ("で", "de (location of action/means)", "where an action takes place, or means used", "はし__たべます。", "で"),
    ("へ", "e (direction)", "indicates direction of movement", "にほん__いきたい。", "へ"),
    ("と", "to (with/and)", "means 'with' or 'and' (for nouns)", "ともだち__いきます。", "と"),
    ("も", "mo (also/too)", "means 'also' or 'too'", "わたし__がくせいです。", "も"),
    ("の", "no (possessive/connector)", "indicates possession or connects nouns", "わたし__ほん。", "の"),
    ("か", "ka (question marker)", "turns a sentence into a question", "がくせいです__？", "か"),
    ("から", "kara (from/because)", "indicates starting point or reason", "えき__あるきます。", "から"),
    ("まで", "made (until/to)", "indicates ending point", "えき__あるきます。", "まで"),
    ("より", "yori (than/from)", "used in comparisons", "バス__でんしゃがはやい。", "より"),
    ("ね", "ne (confirmation)", "seeks agreement, like 'right?' or 'isn't it?'", "いいてんきです__。", "ね"),
    ("よ", "yo (emphasis)", "adds emphasis or assertion", "もうたべました__。", "よ"),
    ("だけ", "dake (only/just)", "means 'only' or 'just'", "すこし__わかります。", "だけ"),
    ("しか", "shika (only — with negative)", "used with negative to mean 'only'", "ひとつ__ありません。", "しか"),
    ("ても", "temo (even if)", "means 'even if' or 'even though'", "たかく__かいます。", "ても"),
    ("ながら", "nagara (while doing)", "means 'while doing X, doing Y'", "おんがくをきき__べんきょうします。", "ながら"),
    ("ので", "node (because)", "gives a reason (softer than から)", "あめがふる__でかけません。", "ので"),
]

# ---------------------------------------------------------------------------
# Question generators
# ---------------------------------------------------------------------------

def tiptap(text: str) -> dict:
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}

def option(opt_id: str, text: str) -> dict:
    return {"id": opt_id, "content_json": tiptap(text)}

def make_vocab_meaning(entry, all_entries):
    """Given a kana word, choose the English meaning."""
    word, romaji, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[2] and e[2] != english], 3)
    opts = [english] + [d[2] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == english)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"{word}　の意味は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{word} ({romaji}) = {english}"),
        "points": 1,
        "tags": ["vocabulary"],
    }

def make_vocab_romaji(entry, all_entries):
    """Given a kana word, choose the romaji reading."""
    word, romaji, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[1] and e[1] != romaji], 3)
    opts = [romaji] + [d[1] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == romaji)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"{word}　の読み方は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{word} is read as: {romaji}　({english})"),
        "points": 1,
        "tags": ["vocabulary", "reading"],
    }

def make_vocab_reverse(entry, all_entries):
    """Given an English meaning, choose the Japanese word."""
    word, romaji, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[0] != word], 3)
    opts = [word] + [d[0] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == word)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"「{english}」は日本語でどう言いますか？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{english} = {word}　({romaji})"),
        "points": 1,
        "tags": ["vocabulary", "reverse"],
    }

def make_kanji_meaning(entry, all_entries):
    kanji, reading_kana, reading_rom, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[3] != english], 3)
    opts = [english] + [d[3] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == english)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"「{kanji}」の意味は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{kanji}　readings: {reading_rom}　→　{english}"),
        "points": 1,
        "tags": ["kanji"],
    }

def make_kanji_reading(entry, all_entries):
    kanji, reading_kana, reading_rom, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[1] != reading_kana], 3)
    opts = [reading_kana] + [d[1] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == reading_kana)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"「{kanji}」の読み方は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{kanji}　({reading_rom})　=　{english}"),
        "points": 1,
        "tags": ["kanji", "reading"],
    }

def make_katakana_meaning(entry, all_entries):
    kata, romaji, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[2] != english], 3)
    opts = [english] + [d[2] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == english)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"「{kata}」の意味は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{kata}　({romaji})　=　{english}"),
        "points": 1,
        "tags": ["katakana"],
    }

def make_katakana_reading(entry, all_entries):
    kata, romaji, english = entry
    distractors = random.sample([e for e in all_entries if e != entry and e[1] != romaji], 3)
    opts = [romaji] + [d[1] for d in distractors]
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == romaji)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"「{kata}」をローマ字で書くと？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"{kata}　=　{romaji}　({english})"),
        "points": 1,
        "tags": ["katakana", "reading"],
    }

def make_particle(entry, all_entries):
    particle, label, explanation, example, answer = entry
    blanked = example.replace("__", "（　）")
    distractors = [e[0] for e in all_entries if e[0] != particle]
    distractor_sample = random.sample(distractors, 3)
    opts = [particle] + distractor_sample
    random.shuffle(opts)
    correct_id = next(chr(ord('a') + i) for i, o in enumerate(opts) if o == particle)
    return {
        "type": "multiple_choice",
        "prompt_json": tiptap(f"{blanked}　（　）に入る助詞は？"),
        "options_json": [option(chr(ord('a') + i), o) for i, o in enumerate(opts)],
        "correct_answer": correct_id,
        "explanation_json": tiptap(f"Answer: 「{particle}」({label}) — {explanation}"),
        "points": 1,
        "tags": ["grammar", "particles"],
    }

# ---------------------------------------------------------------------------
# Build question pool
# ---------------------------------------------------------------------------

valid_vocab = [e for e in VOCAB if e[1] and e[2]]

questions_pool = []

# Vocab: meaning, reading, reverse
for entry in valid_vocab:
    questions_pool.append(make_vocab_meaning(entry, valid_vocab))
    questions_pool.append(make_vocab_romaji(entry, valid_vocab))
    if len(questions_pool) % 3 == 0:
        questions_pool.append(make_vocab_reverse(entry, valid_vocab))

# Kanji: meaning + reading
for entry in KANJI:
    questions_pool.append(make_kanji_meaning(entry, KANJI))
    questions_pool.append(make_kanji_reading(entry, KANJI))

# Katakana: meaning + reading
for entry in KATAKANA:
    questions_pool.append(make_katakana_meaning(entry, KATAKANA))
    questions_pool.append(make_katakana_reading(entry, KATAKANA))

# Particles
for entry in PARTICLES:
    for _ in range(4):  # repeat each particle 4x with different distractors
        questions_pool.append(make_particle(entry, PARTICLES))

# Sample up to 1000
random.seed(42)
random.shuffle(questions_pool)
questions = questions_pool[:1000]

print(f"Generated {len(questions)} questions from pool of {len(questions_pool)}")

# ---------------------------------------------------------------------------
# Pack into Quizbee export format — one block, all questions
# ---------------------------------------------------------------------------

payload = {
    "quizbee_version": "1.0",
    "exported_at": "2026-04-19T00:00:00+00:00",
    "test": {
        "title": "日本語練習",
        "description": "Japanese vocabulary, kanji, katakana and grammar practice. 5 random questions per session.",
        "mode": "practice",
        "access": "public",
        "time_limit_minutes": None,
        "allow_multiple_attempts": True,
        "max_attempts": None,
        "randomize_questions": True,
        "randomize_options": False,
        "show_correct_answers": "at_end",
        "passing_score_pct": None,
        "multiple_select_scoring": "all_or_nothing",
        "draw_count": 5,
        "blocks": [
            {
                "title": None,
                "order": 0,
                "context_json": None,
                "questions": questions,
            }
        ],
    },
}

out_path = "japanese_practice.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=2)

print(f"Written to {out_path}")
