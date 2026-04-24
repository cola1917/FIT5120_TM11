# User Food Preferences Feature
This file describes the user food preferences feature, its functionalities, and its design.

The food preferences feature is a sub-section of the user profile. In addition to the existing user profile info, the user should be able to set their food preferences and blacklist.

## Data
The user preferences data should be stored in the user profile data in a field named 'foodPreferences'. The data to be stored are 'likes', 'dislikes', and 'blacklist'. Each of these should be an array of string which possible values are described below.

Strings in the 'likes' and 'dislikes' arrays can have the same possible values:
- fruits
- vegetables
- rice
- bread
- noodles
- chicken
- beef
- pork
- fish
- dairy

Possible values for the 'blacklist' array are:
- egg
- bread
- milk
- peanut
- seafood
- nuts

## UI
The preferences selection UI should be part of the user profile creation.
There should be two sections (one for likes/dislikes and one for blacklist) with grids in each showing the values mentioned above.
In the likes/dislikes section, each value should have a tile that the user can tap/click on. As the user taps/clicks on the tiles, the selection should cycle through 'like', 'dislike', and 'no preference'. Upon creating the user profile, the values selected as 'like' should be saved to the 'likes' array, similarly for 'dislike'. 'no preference' values do not need to be saved in the user profile.
The 'blacklist' section is similar but the selection only cycles between selected and not selected. Upon creating the user profile, the values selected should be saved to the 'blacklist' array.

Refer to `uiux-reference/preferences-example.jpeg` for UI design style. Use emojis as placeholders for the images.
