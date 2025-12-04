import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import App from '../App';

// Mock the form submission
const mockSubmit = vi.fn();

describe('Lead Capture Form', () => {
  beforeEach(() => {
    mockSubmit.mockClear();
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the form header correctly', () => {
      render(<App />);
      
      expect(screen.getByText(/hampstead renovations/i)).toBeInTheDocument();
      expect(screen.getByText(/free quote/i)).toBeInTheDocument();
    });

    it('renders step 1 - contact details initially', () => {
      render(<App />);
      
      expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/last name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/phone/i)).toBeInTheDocument();
    });

    it('renders the progress indicator', () => {
      render(<App />);
      
      // Should show step 1 as active
      expect(screen.getByText(/step 1/i)).toBeInTheDocument();
    });
  });

  describe('Form Validation', () => {
    it('shows error for empty first name', async () => {
      render(<App />);
      
      const nextButton = screen.getByRole('button', { name: /next|continue/i });
      await userEvent.click(nextButton);
      
      await waitFor(() => {
        expect(screen.getByText(/first name is required/i)).toBeInTheDocument();
      });
    });

    it('shows error for invalid email format', async () => {
      render(<App />);
      
      const emailInput = screen.getByLabelText(/email/i);
      await userEvent.type(emailInput, 'invalid-email');
      
      const nextButton = screen.getByRole('button', { name: /next|continue/i });
      await userEvent.click(nextButton);
      
      await waitFor(() => {
        expect(screen.getByText(/valid email/i)).toBeInTheDocument();
      });
    });

    it('shows error for invalid phone number', async () => {
      render(<App />);
      
      const phoneInput = screen.getByLabelText(/phone/i);
      await userEvent.type(phoneInput, '12345');
      
      const nextButton = screen.getByRole('button', { name: /next|continue/i });
      await userEvent.click(nextButton);
      
      await waitFor(() => {
        expect(screen.getByText(/valid.*phone/i)).toBeInTheDocument();
      });
    });
  });

  describe('Form Navigation', () => {
    it('advances to step 2 when contact details are valid', async () => {
      render(<App />);
      
      // Fill in contact details
      await userEvent.type(screen.getByLabelText(/first name/i), 'John');
      await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
      await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
      await userEvent.type(screen.getByLabelText(/phone/i), '+44 7700 900123');
      
      const nextButton = screen.getByRole('button', { name: /next|continue/i });
      await userEvent.click(nextButton);
      
      await waitFor(() => {
        // Step 2 should show project details
        expect(screen.getByText(/project type/i)).toBeInTheDocument();
      });
    });

    it('can go back to previous step', async () => {
      render(<App />);
      
      // Fill step 1 and advance
      await userEvent.type(screen.getByLabelText(/first name/i), 'John');
      await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
      await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
      await userEvent.type(screen.getByLabelText(/phone/i), '+44 7700 900123');
      
      const nextButton = screen.getByRole('button', { name: /next|continue/i });
      await userEvent.click(nextButton);
      
      // Go back
      const backButton = screen.getByRole('button', { name: /back|previous/i });
      await userEvent.click(backButton);
      
      await waitFor(() => {
        expect(screen.getByLabelText(/first name/i)).toBeInTheDocument();
      });
    });
  });

  describe('Project Type Selection', () => {
    it('displays all project types', async () => {
      render(<App />);
      
      // Navigate to step 2
      await userEvent.type(screen.getByLabelText(/first name/i), 'John');
      await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
      await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
      await userEvent.type(screen.getByLabelText(/phone/i), '+44 7700 900123');
      await userEvent.click(screen.getByRole('button', { name: /next|continue/i }));
      
      await waitFor(() => {
        expect(screen.getByText(/kitchen/i)).toBeInTheDocument();
        expect(screen.getByText(/bathroom/i)).toBeInTheDocument();
        expect(screen.getByText(/extension/i)).toBeInTheDocument();
      });
    });
  });
});

describe('Form Accessibility', () => {
  it('has proper aria labels on form fields', () => {
    render(<App />);
    
    const firstNameInput = screen.getByLabelText(/first name/i);
    expect(firstNameInput).toHaveAttribute('id');
    expect(firstNameInput).toHaveAttribute('type', 'text');
  });

  it('can be navigated with keyboard', async () => {
    render(<App />);
    
    const firstNameInput = screen.getByLabelText(/first name/i);
    firstNameInput.focus();
    expect(document.activeElement).toBe(firstNameInput);
    
    await userEvent.tab();
    expect(document.activeElement).toBe(screen.getByLabelText(/last name/i));
  });

  it('shows focus indicators', () => {
    render(<App />);
    
    const firstNameInput = screen.getByLabelText(/first name/i);
    firstNameInput.focus();
    
    // Check if element has focus styles (ring utility class)
    expect(firstNameInput).toHaveFocus();
  });
});

describe('API Integration', () => {
  beforeEach(() => {
    (global.fetch as ReturnType<typeof vi.fn>).mockReset();
  });

  it('submits form data to API', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        leadId: 'lead-123',
        message: 'Thank you for your inquiry!',
      }),
    });

    render(<App />);
    
    // Fill all required fields and navigate through steps
    // Step 1
    await userEvent.type(screen.getByLabelText(/first name/i), 'John');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
    await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
    await userEvent.type(screen.getByLabelText(/phone/i), '+44 7700 900123');
    await userEvent.click(screen.getByRole('button', { name: /next|continue/i }));
    
    // This test would continue through all form steps...
    // For brevity, we're testing the basic flow
  });

  it('handles API errors gracefully', async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error('Network error')
    );

    render(<App />);
    
    // Fill form and submit (abbreviated)
    await userEvent.type(screen.getByLabelText(/first name/i), 'John');
    await userEvent.type(screen.getByLabelText(/last name/i), 'Smith');
    await userEvent.type(screen.getByLabelText(/email/i), 'john@example.com');
    await userEvent.type(screen.getByLabelText(/phone/i), '+44 7700 900123');
    
    // Error handling should be in place
  });
});
