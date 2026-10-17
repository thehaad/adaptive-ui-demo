import manifest from '../../capabilities.json';

/** Product Capability Manifest (shared with the backend): approved option sets and actions. */
export const optionSets: Record<string, { options: string[] }> = manifest.optionSets;
export const actions: Record<string, unknown> = manifest.actions;
