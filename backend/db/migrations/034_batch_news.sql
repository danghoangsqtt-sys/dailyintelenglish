-- Phase 66 (ENH-048): an episode may carry its own material (a news article for a news Short made from today's news),
-- and the owner's public news feeds for "Today's news".
ALTER TABLE channel_episodes ADD COLUMN source_kind TEXT NOT NULL DEFAULT '';
ALTER TABLE channel_episodes ADD COLUMN source_text TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS news_feeds (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    position INTEGER NOT NULL DEFAULT 0
);
INSERT OR IGNORE INTO news_feeds (id, url, name, enabled, position) VALUES
    ('bbc-world', 'https://feeds.bbci.co.uk/news/world/rss.xml', 'BBC News — World', 1, 0),
    ('npr-news', 'https://feeds.npr.org/1001/rss.xml', 'NPR News', 1, 1);
