import manifest from '../../capabilities.json';

/** Product Capability Manifest: option sets the host app supports (shared with the backend). */
export const optionSets: Record<string, { options: string[] }> = manifest.optionSets;
