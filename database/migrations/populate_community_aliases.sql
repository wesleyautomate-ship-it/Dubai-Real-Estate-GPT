-- ============================================================
-- POPULATE COMMUNITY ALIASES
-- ============================================================
-- Handle community name variations and synonyms
-- e.g., "Downtown Dubai" = "Burj Khalifa" = "Burj Khalifa District"

-- Clear existing community aliases (optional)
DELETE FROM aliases WHERE type = 'community';

-- ============================================================
-- BURJ KHALIFA / DOWNTOWN DUBAI ALIASES
-- ============================================================

-- Downtown Dubai → Burj Khalifa (canonical)
INSERT INTO aliases (alias, canonical, type, confidence)
VALUES 
    ('Downtown Dubai', 'Burj Khalifa', 'community', 1.0),
    ('Downtown', 'Burj Khalifa', 'community', 0.9),
    ('Burj Khalifa District', 'Burj Khalifa', 'community', 1.0),
    ('DIFC', 'Burj Khalifa', 'community', 0.8),  -- Dubai International Financial Centre (nearby)
    ('Old Town', 'Burj Khalifa', 'community', 0.9);

-- ============================================================
-- JVC (JUMEIRAH VILLAGE CIRCLE) ALIASES
-- ============================================================

-- All JVC districts should map to Jumeirah Village Circle
INSERT INTO aliases (alias, canonical, type, confidence)
VALUES 
    ('Jumeirah Village Circle', 'JVC', 'community', 1.0),
    ('JVC District 10', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 11', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 12', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 13', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 14', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 15', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 16', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 17', 'Jumeirah Village Circle', 'community', 1.0),
    ('JVC District 18', 'Jumeirah Village Circle', 'community', 1.0);

-- ============================================================
-- VERIFY ALIASES
-- ============================================================

SELECT 
    type,
    COUNT(*) as alias_count,
    COUNT(DISTINCT canonical) as unique_canonical
FROM aliases
WHERE type = 'community'
GROUP BY type;

SELECT * FROM aliases WHERE type = 'community' ORDER BY canonical, confidence DESC;

-- ============================================================
-- USAGE EXAMPLE
-- ============================================================
-- To use aliases in queries:
-- 
-- SELECT canonical 
-- FROM aliases 
-- WHERE alias ILIKE 'Downtown Dubai' AND type = 'community'
-- LIMIT 1;
-- 
-- This returns: 'Burj Khalifa'
-- ============================================================
