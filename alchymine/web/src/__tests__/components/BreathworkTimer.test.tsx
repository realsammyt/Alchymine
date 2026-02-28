import { render, screen, fireEvent, act } from '@testing-library/react';
import BreathworkTimer from '@/components/shared/BreathworkTimer';

const mockPattern = {
  name: 'Box Breathing',
  phases: [
    { label: 'Inhale', duration: 4, color: 'text-accent' },
    { label: 'Hold', duration: 4, color: 'text-primary' },
    { label: 'Exhale', duration: 4, color: 'text-secondary' },
    { label: 'Hold', duration: 4, color: 'text-primary' },
  ],
  cycles: 2,
  description: 'Equal inhale-hold-exhale-hold pattern.',
};

describe('BreathworkTimer', () => {
  let onComplete: jest.Mock;
  let onStop: jest.Mock;

  beforeEach(() => {
    onComplete = jest.fn();
    onStop = jest.fn();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders the ready state by default', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    expect(screen.getByTestId('breathwork-ready')).toBeInTheDocument();
    expect(screen.getByText('Box Breathing')).toBeInTheDocument();
    expect(screen.getByText('Equal inhale-hold-exhale-hold pattern.')).toBeInTheDocument();
  });

  it('displays phase summary in ready state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    // Should show phase breakdown
    expect(screen.getByText(/Inhale 4s/)).toBeInTheDocument();
  });

  it('has Begin and Back buttons in ready state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    expect(screen.getByText('Begin')).toBeInTheDocument();
    expect(screen.getByText('Back')).toBeInTheDocument();
  });

  it('calls onStop when Back is clicked in ready state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Back'));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it('transitions to active state when Begin is clicked', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));
    expect(screen.getByTestId('breathwork-active')).toBeInTheDocument();
    expect(screen.getByText('Inhale')).toBeInTheDocument();
    expect(screen.getByText('Cycle 1 of 2')).toBeInTheDocument();
  });

  it('shows End Session button in active state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));
    expect(screen.getByText('End Session')).toBeInTheDocument();
  });

  it('calls onStop when End Session is clicked', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));
    fireEvent.click(screen.getByText('End Session'));
    expect(onStop).toHaveBeenCalledTimes(1);
  });

  it('displays the timer role attribute during active state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));
    expect(screen.getByRole('timer')).toBeInTheDocument();
  });

  it('shows phase indicators in active state', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));

    // All phase labels should appear in the indicators
    const phaseIndicators = screen.getAllByText(/Inhale 4s/);
    expect(phaseIndicators.length).toBeGreaterThanOrEqual(1);
  });

  it('transitions through phases as time elapses', () => {
    render(
      <BreathworkTimer pattern={mockPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));

    // Starts with Inhale
    expect(screen.getByText('Inhale')).toBeInTheDocument();

    // Advance past first phase (4 seconds = 40 ticks of 100ms)
    act(() => {
      jest.advanceTimersByTime(4100);
    });

    // Should now be in Hold phase
    // The center text should show "Hold"
    const centerLabels = screen.getAllByText('Hold');
    expect(centerLabels.length).toBeGreaterThanOrEqual(1);
  });

  it('shows session complete screen after all cycles', () => {
    // Use a simple short pattern for testing
    const shortPattern = {
      name: 'Quick Test',
      phases: [{ label: 'Inhale', duration: 0.5, color: 'text-accent' }],
      cycles: 1,
      description: 'Test',
    };

    render(
      <BreathworkTimer pattern={shortPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));

    // Advance past the entire session (0.5s * 1 cycle + buffer)
    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(screen.getByTestId('breathwork-complete')).toBeInTheDocument();
    expect(screen.getByText('Session Complete')).toBeInTheDocument();
  });

  it('allows repeating a completed session', () => {
    const shortPattern = {
      name: 'Quick Test',
      phases: [{ label: 'Inhale', duration: 0.5, color: 'text-accent' }],
      cycles: 1,
      description: 'Test',
    };

    render(
      <BreathworkTimer pattern={shortPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    expect(screen.getByText('Repeat Session')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Repeat Session'));
    expect(screen.getByTestId('breathwork-active')).toBeInTheDocument();
  });

  it('calls onComplete when Done is clicked after session', () => {
    const shortPattern = {
      name: 'Quick Test',
      phases: [{ label: 'Inhale', duration: 0.5, color: 'text-accent' }],
      cycles: 1,
      description: 'Test',
    };

    render(
      <BreathworkTimer pattern={shortPattern} onComplete={onComplete} onStop={onStop} />,
    );
    fireEvent.click(screen.getByText('Begin'));

    act(() => {
      jest.advanceTimersByTime(1000);
    });

    fireEvent.click(screen.getByText('Done'));
    expect(onComplete).toHaveBeenCalledTimes(1);
  });
});
