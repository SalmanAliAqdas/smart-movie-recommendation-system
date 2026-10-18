"""HTML for an accessible, responsive poster gallery using only owned CSS classes."""
from html import escape
from urllib.parse import urlencode
import math

from src.tmdb_client import TMDBClient


GALLERY_STYLE = """
<style>
.movie-gallery{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:22px 14px;padding:4px 0 18px;font-family:'DM Sans',sans-serif}
.movie-gallery *{box-sizing:border-box}.gallery-card{min-width:0}
.gallery-link{display:block;color:#f4f3f8!important;text-decoration:none!important;border-radius:10px;outline-offset:5px}
.gallery-link:focus-visible{outline:2px solid #ffb547}.gallery-art{position:relative;aspect-ratio:2/3;overflow:hidden;border-radius:10px;background:#171821;box-shadow:0 8px 20px #0005;border:1px solid #ffffff0c}
.gallery-art img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .2s ease,opacity .2s ease}
.gallery-link:hover img{transform:scale(1.035);opacity:.85}.gallery-open{position:absolute;inset:auto 8px 10px;background:#0c0d12de;border:1px solid #ffffff30;padding:7px;text-align:center;border-radius:7px;font-size:12px;opacity:0;transition:opacity .2s ease}.gallery-link:hover .gallery-open,.gallery-link:focus-visible .gallery-open{opacity:1}
.gallery-name{font-size:13px;font-weight:600;line-height:1.4;margin:8px 0 3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gallery-meta{display:flex;justify-content:space-between;gap:6px;font-size:12px;color:#9698a7}.gallery-score{color:#edc07b}
@media(max-width:1100px){.movie-gallery{grid-template-columns:repeat(5,minmax(0,1fr))}}
@media(max-width:900px){.movie-gallery{grid-template-columns:repeat(4,minmax(0,1fr));gap:18px 12px}}
@media(max-width:680px){.movie-gallery{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:520px){.movie-gallery{grid-template-columns:repeat(2,minmax(0,1fr));gap:18px 10px}.gallery-name{font-size:12px}.gallery-open{display:none}}
@media(prefers-reduced-motion:reduce){.gallery-art img,.gallery-open{transition:none}}
</style>
"""


def gallery_html(movies, sort="newest", language="en"):
    cards = []
    action = "تفصیلات دیکھیں" if language == "ur" else "View details"
    for index, movie in enumerate(movies):
        title = escape(movie["title"])
        href = escape("?" + urlencode({"gallery_movie": movie["id"], "gallery_sort": sort}), quote=True)
        rating = movie.get("vote_average")
        score = f"★ {rating:.1f}" if isinstance(rating, (int, float)) and math.isfinite(rating) and 0 <= rating <= 10 else "—"
        image = escape(TMDBClient.poster_url(movie["poster_path"]), quote=True)
        loading = "eager" if index < 6 else "lazy"
        cards.append(f'''<article class="gallery-card"><a class="gallery-link" href="{href}" target="_self" aria-label="{action}: {title}">
<div class="gallery-art"><img src="{image}" alt="{title}" width="300" height="450" loading="{loading}" decoding="async"><span class="gallery-open">{action}</span></div>
<div class="gallery-name" title="{title}">{title}</div><div class="gallery-meta"><span>{escape(movie['release_date'][:4])}</span><span class="gallery-score">{score}</span></div></a></article>''')
    return GALLERY_STYLE + '<div class="movie-gallery" role="region" aria-label="Movie posters">' + "".join(cards) + "</div>"
