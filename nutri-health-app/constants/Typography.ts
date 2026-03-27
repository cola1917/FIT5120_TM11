/**
 * NutriHealth Design System - Typography
 * 
 * Pairs geometric Plus Jakarta Sans for displays with soft Be Vietnam Pro for body text.
 * Plus Jakarta Sans provides the "Voice" (high-impact, friendly)
 * Be Vietnam Pro provides the "Guide" (readable, instructional)
 */

/**
 * Font Families
 */
export const FontFamily = {
  // display: 'PlusJakartaSans-Bold',
  display: 'PlusJakartaSans-Variable',
  // headline: 'PlusJakartaSans-SemiBold',
  headline: 'PlusJakartaSans-Variable',
  body: 'BeVietnamPro-Regular',
  body_medium: 'BeVietnamPro-Medium',
  body_bold: 'BeVietnamPro-Bold',
} as const;

/**
 * Font Sizes (in pixels, converted from rem)
 * Base: 16px = 1rem
 */
export const FontSize = {
  // Display (Plus Jakarta Sans)
  display_lg: 56,    // 3.5rem
  display_md: 45,    // 2.8125rem
  display_sm: 36,    // 2.25rem
  
  // Headline (Plus Jakarta Sans)
  headline_lg: 32,   // 2rem
  headline_md: 28,   // 1.75rem
  headline_sm: 24,   // 1.5rem
  
  // Title (Be Vietnam Pro)
  title_lg: 22,      // 1.375rem
  title_md: 20,      // 1.25rem
  title_sm: 18,      // 1.125rem
  
  // Body (Be Vietnam Pro)
  body_lg: 18,       // 1.125rem
  body_md: 16,       // 1rem
  body_sm: 14,       // 0.875rem
  
  // Label
  label_lg: 16,      // 1rem
  label_md: 14,      // 0.875rem
  label_sm: 12,      // 0.75rem
} as const;

/**
 * Line Heights (as multipliers)
 */
export const LineHeight = {
  display: 1.1,
  headline: 1.2,
  title: 1.3,
  body: 1.5,
  label: 1.4,
} as const;

/**
 * Letter Spacing (in pixels)
 */
export const LetterSpacing = {
  tight: -0.5,
  normal: 0,
  wide: 0.5,
} as const;

/**
 * Typography Presets
 * Ready-to-use text style objects
 */
export const Typography = {
  // Display Styles (Plus Jakarta Sans)
  displayLarge: {
    fontFamily: FontFamily.display,
    fontSize: FontSize.display_lg,
    lineHeight: FontSize.display_lg * LineHeight.display,
    letterSpacing: LetterSpacing.tight,
  },
  displayMedium: {
    fontFamily: FontFamily.display,
    fontSize: FontSize.display_md,
    lineHeight: FontSize.display_md * LineHeight.display,
    letterSpacing: LetterSpacing.tight,
  },
  displaySmall: {
    fontFamily: FontFamily.display,
    fontSize: FontSize.display_sm,
    lineHeight: FontSize.display_sm * LineHeight.display,
    letterSpacing: LetterSpacing.normal,
  },
  
  // Headline Styles (Plus Jakarta Sans)
  headlineLarge: {
    fontFamily: FontFamily.headline,
    fontSize: FontSize.headline_lg,
    lineHeight: FontSize.headline_lg * LineHeight.headline,
    letterSpacing: LetterSpacing.normal,
  },
  headlineMedium: {
    fontFamily: FontFamily.headline,
    fontSize: FontSize.headline_md,
    lineHeight: FontSize.headline_md * LineHeight.headline,
    letterSpacing: LetterSpacing.normal,
  },
  headlineSmall: {
    fontFamily: FontFamily.headline,
    fontSize: FontSize.headline_sm,
    lineHeight: FontSize.headline_sm * LineHeight.headline,
    letterSpacing: LetterSpacing.normal,
  },
  
  // Title Styles (Be Vietnam Pro)
  titleLarge: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.title_lg,
    lineHeight: FontSize.title_lg * LineHeight.title,
    letterSpacing: LetterSpacing.normal,
  },
  titleMedium: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.title_md,
    lineHeight: FontSize.title_md * LineHeight.title,
    letterSpacing: LetterSpacing.normal,
  },
  titleSmall: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.title_sm,
    lineHeight: FontSize.title_sm * LineHeight.title,
    letterSpacing: LetterSpacing.normal,
  },
  
  // Body Styles (Be Vietnam Pro)
  bodyLarge: {
    fontFamily: FontFamily.body,
    fontSize: FontSize.body_lg,
    lineHeight: FontSize.body_lg * LineHeight.body,
    letterSpacing: LetterSpacing.normal,
  },
  bodyMedium: {
    fontFamily: FontFamily.body,
    fontSize: FontSize.body_md,
    lineHeight: FontSize.body_md * LineHeight.body,
    letterSpacing: LetterSpacing.normal,
  },
  bodySmall: {
    fontFamily: FontFamily.body,
    fontSize: FontSize.body_sm,
    lineHeight: FontSize.body_sm * LineHeight.body,
    letterSpacing: LetterSpacing.normal,
  },
  
  // Label Styles
  labelLarge: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.label_lg,
    lineHeight: FontSize.label_lg * LineHeight.label,
    letterSpacing: LetterSpacing.wide,
  },
  labelMedium: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.label_md,
    lineHeight: FontSize.label_md * LineHeight.label,
    letterSpacing: LetterSpacing.wide,
  },
  labelSmall: {
    fontFamily: FontFamily.body_medium,
    fontSize: FontSize.label_sm,
    lineHeight: FontSize.label_sm * LineHeight.label,
    letterSpacing: LetterSpacing.wide,
  },
} as const;

/**
 * Font Loading Configuration
 * For use with expo-font or Google Fonts
 */
export const FontAssets = {
  // 'PlusJakartaSans-Bold': require('../assets/fonts/PlusJakartaSans-Bold.ttf'),
  'PlusJakartaSans-Variable': require('../assets/fonts/PlusJakartaSans-VariableFont_wght.ttf'),
  // 'PlusJakartaSans-SemiBold': require('../assets/fonts/PlusJakartaSans-SemiBold.ttf'),
  'BeVietnamPro-Regular': require('../assets/fonts/BeVietnamPro-Regular.ttf'),
  'BeVietnamPro-Medium': require('../assets/fonts/BeVietnamPro-Medium.ttf'),
  'BeVietnamPro-Bold': require('../assets/fonts/BeVietnamPro-Bold.ttf'),
};

/**
 * Note: Fonts should be downloaded from Google Fonts and placed in assets/fonts/
 * - Plus Jakarta Sans: https://fonts.google.com/specimen/Plus+Jakarta+Sans
 * - Be Vietnam Pro: https://fonts.google.com/specimen/Be+Vietnam+Pro
 */
