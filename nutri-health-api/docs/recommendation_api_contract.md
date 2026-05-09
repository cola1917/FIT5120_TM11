# Recommendation API Contract

## Endpoint

```
POST /recommendations
```

## Request

```json
{
  "goal_id": "grow | see | think | fight | feel | strong",
  "likes":     ["dairy", "meat"],
  "dislikes":  ["vegetables"],
  "blacklist": ["milk"],
  "allergies": ["egg"]
}
```

## Response

```json
{
  "super_power_foods": [ <FoodItem>, ... ],
  "tiny_hero_foods":   [ <FoodItem>, ... ],
  "try_less_foods":    [ <FoodItem>, ... ]
}
```

## FoodItem shape

Every item in all three sections has this shape:

```json
{
  "food_id":      "ai-mango",
  "food_name":    "mango",
  "reason":       "Mango is a sweet fruit that supports the feel goal.",
  "category":     "fruits",
  "image_url":    "/static/category_fallback/fruits.png",
  "image_status": "fallback",

  "cn_code": "ai-mango",
  "name":    "mango",
  "grade":   "Mango is a sweet fruit that supports the feel goal."
}
```

### Field reference

| Field          | Type   | Notes |
|----------------|--------|-------|
| `food_id`      | string | URL-safe slug, use as React key |
| `food_name`    | string | Display name |
| `reason`       | string | Child-friendly explanation from the model |
| `category`     | string | One of: eggs, fish, meat, dairy, beans, fruits, vegetables, grains, rice, noodles, snacks, drinks, sauces, mixed_dishes |
| `image_url`    | string | Always non-empty. Points to a fallback or cached generated image |
| `image_status` | string | See values below |
| `cn_code`      | string | Alias for `food_id` — old frontend compatibility |
| `name`         | string | Alias for `food_name` — old frontend compatibility |
| `grade`        | string | Alias for `reason` — old frontend compatibility |

### `image_status` values

| Value       | Meaning |
|-------------|---------|
| `fallback`  | Using category fallback image. Background generation may be queued. |
| `ready`     | A real food photo has been generated and cached. `image_url` points to it. |
| `pending`   | Image generation is in-flight. Response still uses fallback image_url. |
| `failed`    | Generation failed. Response uses fallback image_url. Will be retried after 24 h. |

## Async image caching behaviour

- The `/recommendations` response is **never delayed** by image generation.
- On first request for a food, `image_url` returns the category fallback and `image_status` is `fallback`.
- The backend queues a background task to download a real food photo from Pollinations.ai.
- On subsequent requests for the same food, if the image is ready, `image_url` returns the cached generated path and `image_status` is `ready`.
- If image generation fails, the fallback is used indefinitely until a retry succeeds (after 24 h).

## Frontend notes

- **Display `image_url` regardless of `image_status`** — it is always a valid, displayable image path.
- No frontend changes are needed to support async image caching.
- Old frontend code reading `cn_code`, `name`, `grade` continues to work unchanged.
- New frontend code should prefer `food_id`, `food_name`, `reason`.
