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
    }
}

def tr(key: str, language: str = "en") -> str:
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"].get(key, key))

