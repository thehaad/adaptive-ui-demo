import type { ComponentRegistry } from '../adaptive';
import { PreferenceSelector } from './components/PreferenceSelector';
import { Row } from './components/Row';
import { WelcomeCard } from './components/WelcomeCard';

export const registry: ComponentRegistry = {
  Row,
  WelcomeCard,
  PreferenceSelector,
};
