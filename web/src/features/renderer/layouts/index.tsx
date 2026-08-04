import { CenteredLayout } from './centered';
import { FullBleedLayout } from './full-bleed';
import { GridLayout } from './grid';
import type { Layout, LayoutProps } from './region';
import { SplitLeftLayout } from './split-left';
import { SplitRightLayout } from './split-right';
import { StackLayout } from './stack';

const LAYOUTS: Record<Layout, (props: LayoutProps) => React.ReactNode> = {
  'full-bleed': FullBleedLayout,
  'split-left': SplitLeftLayout,
  'split-right': SplitRightLayout,
  centered: CenteredLayout,
  stack: StackLayout,
  grid: GridLayout,
};

export function SceneLayout({ layout, ...rest }: LayoutProps & { layout: Layout }) {
  const Component = LAYOUTS[layout];
  return <Component {...rest} />;
}

export { groupByRegion } from './region';
export type { Layout, Region } from './region';
