import type { ComponentRegistry } from '../adaptive';
import { ActionButton } from './components/ActionButton';
import { PreferenceSelector } from './components/PreferenceSelector';
import { Row } from './components/Row';
import { Steps } from './components/Steps';
import { WelcomeCard } from './components/WelcomeCard';

export const registry: ComponentRegistry = {
  Row,
  Steps,
  WelcomeCard,
  PreferenceSelector,
  ActionButton,
};
