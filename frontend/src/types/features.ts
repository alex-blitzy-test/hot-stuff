/**
 * Content shape of `frontend/src/components/trends/features.json`, the static audio-feature copy
 * consumed as a typed JSON import by the Trends panel (`TrendsSection.tsx`).
 */

/**
 * One audio-feature entry from `features.json`.
 *
 * `desctiption` is the key the JSON actually carries on every entry and the key the Trends panel
 * renders, so the spelling is intentional and must not be corrected: renaming it here would not
 * rename it in the data and would break the render.
 */
export interface FeatureDescription {
  title: string;
  desctiption: string;
}
