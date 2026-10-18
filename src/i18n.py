"""Interface-owned translations. TMDB metadata is never machine-invented."""
TRANSLATIONS = {
    "en": {
        "Discover":"Discover", "Recommendations":"Recommendations", "Similar Movies":"Similar Movies", "Upcoming":"Upcoming",
        "Compare":"Compare", "Collections":"Collections", "Watchlist":"Watchlist", "Settings":"Settings",
        "search":"Search movies", "title_search":"Title search", "advanced_discovery":"Advanced discovery", "load_more":"Load more",
        "no_results":"No movies matched. Try broadening the filters.", "watchlist_add":"＋ Watchlist", "details":"Movie details",
        "language":"Interface language", "saved":"Preferences saved.", "filters":"Filters", "sort":"Sort by", "trailer":"Trailer",
        "trending_week":"Trending This Week", "popular_movies":"Popular Movies", "top_rated_movies":"Top Rated Movies",
        "now_playing":"Now Playing", "upcoming_movies":"Upcoming Movies", "browse_genre":"Browse by Genre",
        "view_details":"View details", "view_more":"View more", "show_less":"Show less", "homepage_error":"This section is temporarily unavailable.",
        "explore_movies":"Explore Movies", "gallery_sort_newest":"Newest releases", "gallery_sort_popular":"Most popular", "gallery_sort_rated":"Highest rated",
        "gallery_loading":"Finding movies…", "gallery_retry":"Retry", "gallery_cached":"Showing previously loaded movies.",
        "gallery_config":"Connect TMDB in Streamlit Secrets and turn off demo mode to see real movie posters.",
        "gallery_auth":"TMDB rejected the configured credentials. Check Streamlit Secrets, then retry.",
        "gallery_unavailable":"Movies couldn't load from TMDB. Please retry in a moment.",
        "gallery_genres":"Live genre names couldn't load. Standard TMDB genres are available below.",
    },
    "ur": {
        "Discover":"دریافت کریں", "Recommendations":"تجاویز", "Similar Movies":"ملتی جلتی فلمیں", "Upcoming":"آنے والی فلمیں",
        "Compare":"موازنہ", "Collections":"فلمی مجموعے", "Watchlist":"واچ لسٹ", "Settings":"ترتیبات",
        "search":"فلمیں تلاش کریں", "title_search":"عنوان سے تلاش", "advanced_discovery":"تفصیلی تلاش", "load_more":"مزید دکھائیں",
        "no_results":"کوئی فلم نہیں ملی۔ فلٹرز کو وسیع کریں۔", "watchlist_add":"＋ واچ لسٹ", "details":"فلم کی تفصیلات",
        "language":"انٹرفیس کی زبان", "saved":"ترجیحات محفوظ ہو گئیں۔", "filters":"فلٹرز", "sort":"ترتیب", "trailer":"ٹریلر",
        "trending_week":"اس ہفتے مقبول", "popular_movies":"مقبول فلمیں", "top_rated_movies":"بہترین ریٹنگ والی فلمیں",
        "now_playing":"اب سینما میں", "upcoming_movies":"آنے والی فلمیں", "browse_genre":"صنف کے لحاظ سے دیکھیں",
        "view_details":"تفصیلات دیکھیں", "view_more":"مزید دیکھیں", "show_less":"کم دکھائیں", "homepage_error":"یہ حصہ عارضی طور پر دستیاب نہیں ہے۔",
        "explore_movies":"فلمیں دریافت کریں", "gallery_sort_newest":"نئی ریلیز", "gallery_sort_popular":"سب سے مقبول", "gallery_sort_rated":"بہترین ریٹنگ",
        "gallery_loading":"فلمیں تلاش کی جا رہی ہیں…", "gallery_retry":"دوبارہ کوشش کریں", "gallery_cached":"پہلے سے لوڈ کی گئی فلمیں دکھائی جا رہی ہیں۔",
        "gallery_config":"اصل پوسٹرز کے لیے Streamlit Secrets میں TMDB کی معلومات دیں اور ڈیمو موڈ بند کریں۔",
        "gallery_auth":"TMDB نے اسناد قبول نہیں کیں۔ Streamlit Secrets چیک کر کے دوبارہ کوشش کریں۔",
        "gallery_unavailable":"TMDB سے فلمیں لوڈ نہیں ہو سکیں۔ کچھ دیر بعد دوبارہ کوشش کریں۔",
        "gallery_genres":"اصناف کے نام لوڈ نہیں ہوئے۔ معیاری TMDB اصناف نیچے دستیاب ہیں۔",
    }
}

def tr(key: str, language: str = "en") -> str:
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

