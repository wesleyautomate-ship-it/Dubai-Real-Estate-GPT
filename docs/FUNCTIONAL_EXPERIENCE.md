# Dubai Real Estate Assistant – What It Does and How to Use It

This document focuses on what the application delivers for users—how it behaves end to end, what you can accomplish with it, and what the experience feels like. It intentionally avoids implementation details.

## Big Picture
- A single workspace for Dubai property discovery, owner intelligence, and quick market answers.
- Users ask questions in plain language; the system combines semantic search, structured filters, and prebuilt analytics to respond with cards instead of raw data.
- Conversations are saved, so users can return to past threads and continue where they left off.

## Who It’s For
- **Agents and brokers:** Find owners, recent comps, and outreach lists fast.
- **Analysts and ops teams:** Validate data loads, answer portfolio questions, and monitor market-level stats.
- **Sales leaders:** Identify top investors, likely sellers, and target segments for campaigns.

## Core Capabilities
- **Natural-language search:** Ask about units, buildings, communities, price ranges, or beds/baths and get ranked property results with owner context where available.
- **Ownership lookup:** Pinpoint the current owner of a specific unit (by unit + building/community) with contact info when on file.
- **Transaction history:** See a timeline of past sales for a unit, with dates, prices, and price per sqft.
- **Portfolio view:** Look up an owner by name or phone to see their holdings, total estimated value, and last known prices.
- **Market insights:** Quick snapshot cards (property counts, average price per sqft, last update) scoped to a building or community inferred from the query.
- **Prospecting lists:** Pull contactable owners within size/price bands, exclude institutional owners if desired, and sort by most recent transactions.
- **Conversation memory:** Each chat is saved with a title and summary; users can reopen a conversation to see prior answers and continue asking follow-ups.
- **Model choice:** Users can switch between available LLM providers for semantics and language quality; the choice sticks per user/session.

## What a User Experiences (End to End)

1. **Landing in the app**
   - The header shows the brand (RealEstateGPT) and a stat chip with indexed property counts and last update recency.
   - A welcome card lists example prompts (“Who owns 905 at Address Sky View tower 2?”; “Properties in Marina”) to guide first-time users.

2. **Starting a conversation**
   - Users type any question into the composer and hit send.
   - The system automatically creates a new conversation if none is active; a “New” button starts a fresh one at any time.

3. **Intent-aware responses**
   - The system classifies the request into one of several intents and returns a purpose-built card:
     - **Search:** A list of units with building/community, owner (if available), last price, and a short snippet.
     - **Ownership:** A focused card with the unit, building, community, and the current owner’s contact details when present.
     - **History:** A timeline of past transactions with dates, prices, and price per sqft.
     - **Portfolio:** A rollup of an owner’s holdings, total value, and a list of properties.
     - **Analytics:** A compact insight card with totals and average price/sqft for the inferred scope.
   - Errors are shown inline in a red banner with human-readable text.

4. **Conversation sidebar**
   - The left panel lists prior conversations with titles and last-message previews.
   - Selecting one loads its message history instantly, so users can pick up threads without reissuing queries.

5. **Model selector**
   - A small control beside the input lets users switch between available LLM providers (e.g., OpenAI vs. Gemini).
   - If a provider is missing credentials, it’s visibly disabled so users know why it’s unavailable.

6. **Authentication (optional)**
   - When auth is enabled, users can request a magic link by email.
   - The app refreshes sessions automatically; if a token expires, it prompts a new sign-in without losing the conversation UI.

7. **Speed and feedback**
   - A “thinking” bubble shows the current step (e.g., “Running semantic search” or “Finding owner”).
   - A loading card skeleton appears for longer operations to set expectations.

## What the System Delivers Behind the Scenes (Functionally)
- **Fresh, normalized property data:** The backend serves a cleaned Dubai property dataset so users can trust community/building/unit names and sizes/prices.
- **Alias-aware lookups:** Building and community aliases are resolved, so user phrasing (“sky view tower” vs. “Address Sky View”) still finds the right records.
- **Structured filters combined with semantics:** If semantic search misses, the system falls back to structured queries, ensuring “no results” is rare for reasonable inputs.
- **Contact-ready outputs:** Owner name/phone/email (when on file) surface directly in cards for outreach scenarios.
- **Analytics in one tap:** Users don’t craft SQL; the API returns ready-to-read stats scoped to their query context.
- **Conversation persistence:** Messages are stored with UI-friendly metadata so cards re-render faithfully on reload.

## Typical User Flows
- **Find an owner quickly**
  - Ask: “Who owns 905 at Address Sky View tower 2?”
  - Result: Ownership card with owner contact; search fallback if the exact unit is ambiguous.

 - **Validate a unit’s history**
  - Ask: “History for 905 in Forte 1”
  - Result: Timeline of sales with prices and dates; helpful for comps or disclosure prep.

- **Prospect in a segment**
  - Ask: “Owners in Marina between 1.5M and 2M for 2 beds”
  - Result: Owner list filtered by price/size/beds; can exclude banks/developers to focus on individuals.

- **Check a portfolio**
  - Ask: “Portfolio for +9715xxxxxxx” or “Properties owned by Ahmed Ali”
  - Result: Portfolio card with total properties, estimated value, and property list.

- **Get a quick market read**
  - Ask: “Market insights for Burj Views”
  - Result: Insights card with property counts and average price per sqft scoped to that community/building.

- **Explore inventory**
  - Ask: “Properties in Marina with 3 beds under 4M”
  - Result: Search card listing matching units, owners (if available), and last prices.

## What Makes It Helpful
- **Plain-language first:** Users don’t need to know column names or exact spellings; alias resolution and semantic search bridge the gap.
- **Task-specific answers, not raw rows:** Cards are tailored to the job—ownership, history, portfolio, or insights—reducing cognitive load.
- **Sticky context:** Saved conversations and previews mean users can multitask without losing state.
- **Fast pivots:** Switching models or starting new conversations is a single click; filtering by community/building/unit is forgiving.
- **Outreach-ready:** Contact info is surfaced where possible, and institutional owners can be excluded to focus on prospects.

## Boundaries and Expectations
- If a unit or owner truly doesn’t exist in the indexed data, the app will return a “No results” card and suggest trying different phrasing.
- Contact fields appear only when present in the data; some properties may have owner placeholders or none at all.
- Analytics are snapshot-level (counts, averages) meant for quick guidance, not exhaustive dashboards.

## How to Get the Most Out of It
- Be specific with units/buildings when looking up owners or history.
- Include price/bedroom hints for better-ranked search results (“3 bed under 4M in Marina”).
- Use phone numbers for portfolio lookups when available; names can be ambiguous.
- Save separate conversations for distinct clients or campaigns to keep context clean.

## Vision for the Experience
- Keep responses concise, card-based, and immediately actionable.
- Minimize dead-ends: when semantic search is thin, fall back to structured lookups and return something useful.
- Maintain a forgiving interface: tolerate spelling variants, aliases, and incomplete information.
- Support fast prospecting: simple paths to filter owners, view portfolios, and export or act on lists.
