This document describes some changes to the story section of the app, see `app/(tabs)/stories/`.

1. Any currently playing page audio should stop when the user navigates away from the current story.
2. The story outcome section of each story should show a button to allow the user to claim points to be added to the `totalPoints` in their user profile, see `services/userProfile.ts`.
3. However, each story can only grant points once. After it the user has received points for a story, viewing the story outcome again should no longer allow the user to claim points again. The tracking of which stories have been read by the user can be stored in the user profile.
4. Add appropriate animation when the user claims points so that it is clear and cathartic.

## Story Rework Implementation Plan

### Change 1 — Stop audio on navigation away from story

**File:** `app/(tabs)/stories/[storyId].tsx`

The story reader already calls `cleanupAudio()` in the back button handler and in the `useEffect` cleanup. However, the issue is that navigating away via the "View Story Outcome" button does NOT stop audio first. The fix is:

- In `handleViewOutcome()`, call `await cleanupAudio()` before calling `router.push()`
- Also add a `navigation.addListener('blur')` event listener in the `useEffect` to stop audio whenever the screen loses focus (covers all navigation-away scenarios including swipe-back gestures)

---

### Change 2 & 3 — Claim points button on story outcome (one-time only)

**Files to modify:**
- `services/userProfile.ts` — add `completedStories: string[]` field to `UserProfile` and two new functions
- `app/(tabs)/stories/story-outcome.tsx` — add the claim points button with one-time guard

**`services/userProfile.ts` changes:**

1. Add `completedStories: string[]` to the `UserProfile` interface (default `[]`)
2. Add function `hasClaimedStoryPoints(storyId: string): Promise<boolean>` — checks if storyId is in `completedStories`
3. Add function `claimStoryPoints(storyId: string, points: number): Promise<boolean>` — adds storyId to `completedStories`, adds points to `totalPoints`, saves profile. Returns `false` if already claimed.

**`app/(tabs)/stories/story-outcome.tsx` changes:**

1. On mount, call `hasClaimedStoryPoints(storyId)` and store result in `alreadyClaimed` state
2. If `alreadyClaimed` is false, show a "Claim Points" button (e.g. "Claim 10 Points 🌟")
3. If `alreadyClaimed` is true, show a disabled/greyed "Points Already Claimed ✓" indicator instead
4. On press of "Claim Points", call `claimStoryPoints(storyId, 10)` and trigger the animation (Change 4)

Points value: **10 points per story** (a reasonable fixed amount — can be adjusted).

---

### Change 4 — Points claim animation

**File:** `app/(tabs)/stories/story-outcome.tsx`

Use React Native's built-in `Animated` API (no new dependencies needed) to create a satisfying "cathartic" animation when points are claimed:

- A `+10 ⭐` floating text that animates upward and fades out (translateY + opacity)
- The "Claim Points" button briefly scales up then back down (scale spring animation)
- After animation completes, swap the button to the "Already Claimed" state

This uses only `Animated.parallel`, `Animated.spring`, and `Animated.timing` — all already available in React Native.

---

### Summary of files changed

- `services/userProfile.ts` — add `completedStories` field + 2 new functions
- `app/(tabs)/stories/[storyId].tsx` — stop audio on navigation away (blur listener + fix `handleViewOutcome`)
- `app/(tabs)/stories/story-outcome.tsx` — claim points button, one-time guard, claim animation

No new packages required. The `createUserProfile` function will need to initialise `completedStories: []` for new profiles, and `getUserProfile` will need to handle existing profiles that don't have this field yet (default to `[]`).

---
