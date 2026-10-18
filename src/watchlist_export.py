"""In-memory watchlist CSV export."""
import csv, io

def watchlist_csv(rows: list[dict]) -> bytes:
    stream = io.StringIO()
    fields = ["title", "release_year", "genres", "tmdb_rating", "personal_rating", "status", "date_added"]
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        movie = row.get("metadata") or {}
        genres = movie.get("genres") or []
        if genres and isinstance(genres[0], dict): genres = [g.get("name", "") for g in genres]
        writer.writerow({"title": row.get("title", ""), "release_year": (row.get("release_date") or "")[:4],
            "genres": ", ".join(str(x) for x in genres), "tmdb_rating": movie.get("vote_average", ""),
            "personal_rating": row.get("user_rating") or "", "status": row.get("status", ""),
            "date_added": row.get("created_at") or row.get("updated_at") or ""})
    return stream.getvalue().encode("utf-8-sig")

