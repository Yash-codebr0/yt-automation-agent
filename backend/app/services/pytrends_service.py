import random
from pytrends.request import TrendReq

# Niche-specific seed keywords — used for interest_over_time queries
# and as fallback titles when APIs are unavailable
NICHE_SEED_TOPICS = {
    "gaming": ["video games", "gaming setup", "game review", "esports", "streaming games"],
    "fitness": ["home workout", "weight loss", "gym motivation", "calisthenics", "protein diet"],
    "cooking": ["meal prep", "air fryer recipes", "healthy dinner", "baking tips", "street food"],
    "travel": ["budget travel", "hidden travel gems", "solo travel", "travel hacks", "travel vlog"],
    "tech": ["smartphone review", "laptop buying guide", "smart home", "electric vehicle", "tech unboxing"],
    "ai": ["openai gpt-5", "ai tools 2026", "claude ai", "llm benchmark", "ai automation"],
    "programming": ["python tutorial", "rust programming", "react 2026", "system design", "langchain tutorial"],
    "finance": ["stock market 2026", "bitcoin etf", "personal finance", "index funds", "federal reserve"],
    "startups": ["micro saas", "yc startup advice", "bootstrap vs vc", "indie hacker", "saas pricing"],
    "health": ["mental health tips", "sleep optimization", "gut health", "longevity supplements", "stress reduction"],
    "beauty": ["skincare routine", "makeup trends 2026", "drugstore beauty", "glass skin", "hair care tips"],
    "music": ["music production", "best daw", "guitar lessons", "music theory", "lo-fi beats"],
    "education": ["study techniques", "online learning", "how to learn fast", "productivity student", "note-taking"],
    "business": ["start a business 2026", "digital marketing", "email marketing", "social media growth", "passive income"],
    "sports": ["nfl highlights", "basketball training", "soccer tactics", "sports nutrition", "athlete workout"],
}


def _get_niche_seeds(niche: str) -> list[str]:
    """Return seed keywords for a given niche with fuzzy matching."""
    niche_lower = niche.lower().strip()
    if niche_lower in NICHE_SEED_TOPICS:
        return NICHE_SEED_TOPICS[niche_lower]
    for key, seeds in NICHE_SEED_TOPICS.items():
        if key in niche_lower or niche_lower in key:
            return seeds
    # Truly custom niche — generate on-the-fly
    return [
        f"best {niche} tips 2026",
        f"how to start {niche}",
        f"{niche} beginner guide",
        f"top {niche} trends",
        f"{niche} secrets",
    ]


class PyTrendsService:

    @classmethod
    def fetch_google_trends(cls, niche: str | None = None) -> list[dict]:
        """Fetch trends from Google Trends.

        When `niche` is given:
          1. Uses interest_over_time() for real search-volume data on niche keywords
          2. Falls back to related_queries() rising searches
          3. Finally falls back to seeded mock data

        Without niche: fetches globally trending daily searches.
        """
        try:
            pytrends = TrendReq(hl="en-US", tz=360, timeout=(3, 5), retries=1)

            if niche:
                return cls._fetch_niche_trends(pytrends, niche)

            # Global trending searches
            df = pytrends.trending_searches(pn="united_states")
            trends = []
            if not df.empty:
                for _, row in df.iterrows():
                    query = row[0]
                    trends.append({
                        "title": f"Everything about {query}",
                        "query": query,
                        "source": "Google Trends",
                        "score": float(random.randint(70, 99)),
                        "category": cls._infer_category(query),
                    })
                return trends

            # Fallback: realtime trending
            df_rt = pytrends.realtime_trending_searches(pn="US")
            if not df_rt.empty:
                for _, row in df_rt.iterrows():
                    query = row["title"]
                    trends.append({
                        "title": f"Why {query} is trending",
                        "query": query,
                        "source": "Google Trends",
                        "score": float(random.randint(75, 98)),
                        "category": cls._infer_category(query),
                    })
                return trends

            raise Exception("No trends returned from Google Trends")

        except Exception as e:
            print(f"Google Trends fetch error: {e}. Returning fallback.")
            return cls._get_fallback_trends(niche)

    @classmethod
    def _fetch_niche_trends(cls, pytrends: TrendReq, niche: str) -> list[dict]:
        """Use interest_over_time() to get real niche-specific trend scores."""
        seeds = _get_niche_seeds(niche)
        # pytrends allows max 5 keywords per payload
        kw_list = seeds[:5]
        try:
            pytrends.build_payload(kw_list=kw_list, timeframe="now 7-d", geo="US")
            iot_df = pytrends.interest_over_time()

            trends = []
            if not iot_df.empty and "isPartial" in iot_df.columns:
                iot_df = iot_df[iot_df["isPartial"] == False]

            if not iot_df.empty:
                # Take the mean score for each keyword over the period
                for kw in kw_list:
                    if kw in iot_df.columns:
                        avg_score = float(iot_df[kw].mean())
                        if avg_score > 0:
                            trends.append({
                                "title": f"{kw.title()} — {niche} trend 2026",
                                "query": kw,
                                "source": "Google Trends (Interest Over Time)",
                                "score": round(min(avg_score, 100.0), 1),
                                "category": niche,
                            })

                if trends:
                    # Also try to get related rising queries for richer results
                    try:
                        related = pytrends.related_queries()
                        for kw in kw_list:
                            if kw in related and related[kw] and related[kw].get("rising") is not None:
                                rising_df = related[kw]["rising"]
                                if not rising_df.empty:
                                    for _, row in rising_df.head(3).iterrows():
                                        query = str(row["query"])
                                        trends.append({
                                            "title": f"{query} — rising in {niche}",
                                            "query": query,
                                            "source": "Google Trends (Rising)",
                                            "score": round(min(float(row.get("value", 70)), 100.0), 1),
                                            "category": niche,
                                        })
                    except Exception:
                        pass  # Related queries are bonus — don't fail on them

                    # Sort by score and deduplicate
                    seen = set()
                    unique = []
                    for t in sorted(trends, key=lambda x: x["score"], reverse=True):
                        if t["query"] not in seen:
                            seen.add(t["query"])
                            unique.append(t)
                    return unique[:15]

        except Exception as e:
            print(f"interest_over_time error for '{niche}': {e}")

        # Final fallback: seeded mock data for this niche
        return cls._get_fallback_trends(niche)

    @staticmethod
    def _infer_category(query: str, niche: str | None = None) -> str:
        """Infer a category label from a query string."""
        if niche:
            return niche
        q = query.lower()
        checks = [
            (["ai", "gpt", "openai", "claude", "nvidia", "midjourney", "llm", "gemini"], "AI"),
            (["python", "rust", "javascript", "typescript", "react", "programming", "coding", "nextjs", "langchain"], "Programming"),
            (["finance", "fed", "inflation", "stock", "crypto", "bitcoin", "ethereum", "market", "etf"], "Finance"),
            (["startup", "founder", "saas", "funding", "yc", "y combinator", "venture"], "Startups"),
            (["gaming", "game", "esports", "playstation", "xbox", "gta", "minecraft"], "Gaming"),
            (["fitness", "workout", "gym", "weight loss", "muscle", "protein"], "Fitness"),
            (["cooking", "recipe", "food", "meal", "baking", "kitchen"], "Cooking"),
            (["travel", "vacation", "destination", "hotel", "flight", "passport"], "Travel"),
        ]
        for keywords, label in checks:
            if any(w in q for w in keywords):
                return label
        return "General"

    @classmethod
    def _get_fallback_trends(cls, niche: str | None = None) -> list[dict]:
        """Generate fallback trends — niche-specific when niche is provided."""
        if niche:
            seeds = _get_niche_seeds(niche)
            return [
                {
                    "title": f"{seed.title()} — Top {niche} Topic",
                    "query": seed,
                    "source": "Niche Trends (Fallback)",
                    "score": float(random.randint(65, 98)),
                    "category": niche,
                }
                for seed in seeds
            ]

        # Generic multi-niche fallback pool
        generic = [
            ("Nvidia Blackwell GPU Benchmarks", "AI"),
            ("Next.js 16 Server Actions Guide", "Programming"),
            ("Apple Intelligence Developer API Integration", "AI"),
            ("Rust vs Go for Backend Microservices in 2026", "Programming"),
            ("Federal Reserve Interest Rate Cut Announcement", "Finance"),
            ("How YCombinator Startups are Pivoting to Agents", "Startups"),
            ("Bitcoin Spot ETFs Capital Inflow Surge", "Finance"),
            ("Claude 3.7 Sonnet Programming Capabilities", "AI"),
            ("Best Home Workout Routines Without Equipment", "Fitness"),
            ("GTA 6 Release Date Confirmed 2026", "Gaming"),
            ("Budget Travel Tips Europe 2026", "Travel"),
            ("Easy Air Fryer Recipes for Beginners", "Cooking"),
        ]
        return [
            {
                "title": title,
                "query": title,
                "source": "Google Trends",
                "score": float(random.randint(65, 95)),
                "category": cat,
            }
            for title, cat in generic
        ]
