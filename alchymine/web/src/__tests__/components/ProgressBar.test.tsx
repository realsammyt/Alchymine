import { render, screen } from '@testing-library/react';
import ProgressBar from '@/components/shared/ProgressBar';

describe('ProgressBar', () => {
  it('renders without crashing', () => {
    const { container } = render(<ProgressBar value={50} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it('renders with the correct width based on value', () => {
    const { container } = render(<ProgressBar value={75} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle({ width: '75%' });
  });

  it('clamps values above 100 to 100', () => {
    const { container } = render(<ProgressBar value={150} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle({ width: '100%' });
  });

  it('clamps negative values to 0', () => {
    const { container } = render(<ProgressBar value={-10} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle({ width: '0%' });
  });

  it('displays label when provided', () => {
    render(<ProgressBar value={50} label="Progress" />);
    expect(screen.getByText('Progress')).toBeInTheDocument();
  });

  it('displays percentage when showPercentage is true', () => {
    render(<ProgressBar value={63} showPercentage />);
    expect(screen.getByText('63%')).toBeInTheDocument();
  });

  it('does not display percentage by default', () => {
    const { container } = render(<ProgressBar value={63} />);
    expect(container.textContent).not.toContain('63%');
  });

  it('applies gold variant classes by default', () => {
    const { container } = render(<ProgressBar value={50} />);
    const bar = container.querySelector('[class*="from-primary-dark"]');
    expect(bar).toBeInTheDocument();
  });

  it('applies purple variant classes', () => {
    const { container } = render(<ProgressBar value={50} variant="purple" />);
    const bar = container.querySelector('[class*="from-secondary-dark"]');
    expect(bar).toBeInTheDocument();
  });

  it('applies teal variant classes', () => {
    const { container } = render(<ProgressBar value={50} variant="teal" />);
    const bar = container.querySelector('[class*="from-accent-dark"]');
    expect(bar).toBeInTheDocument();
  });

  it('applies sm size class', () => {
    const { container } = render(<ProgressBar value={50} size="sm" />);
    const track = container.querySelector('.h-1\\.5');
    expect(track).toBeInTheDocument();
  });

  it('applies lg size class', () => {
    const { container } = render(<ProgressBar value={50} size="lg" />);
    const track = container.querySelector('.h-4');
    expect(track).toBeInTheDocument();
  });

  it('shows shimmer animation by default', () => {
    const { container } = render(<ProgressBar value={50} />);
    const shimmer = container.querySelector('.shimmer-gold');
    expect(shimmer).toBeInTheDocument();
  });

  it('hides shimmer animation when animated is false', () => {
    const { container } = render(<ProgressBar value={50} animated={false} />);
    const shimmer = container.querySelector('.shimmer-gold');
    expect(shimmer).not.toBeInTheDocument();
  });

  it('renders both label and percentage together', () => {
    render(<ProgressBar value={42} label="Loading" showPercentage />);
    expect(screen.getByText('Loading')).toBeInTheDocument();
    expect(screen.getByText('42%')).toBeInTheDocument();
  });

  it('handles zero value correctly', () => {
    const { container } = render(<ProgressBar value={0} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle({ width: '0%' });
  });

  it('handles 100% value correctly', () => {
    const { container } = render(<ProgressBar value={100} />);
    const bar = container.querySelector('[style*="width"]');
    expect(bar).toHaveStyle({ width: '100%' });
  });
});
