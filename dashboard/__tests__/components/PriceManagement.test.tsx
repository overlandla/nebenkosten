/**
 * Unit tests for PriceManagement component
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import PriceManagement from '@/components/PriceManagement';

// Mock fetch
global.fetch = jest.fn();

describe('PriceManagement', () => {
  beforeEach(() => {
    (global.fetch as jest.Mock).mockClear();
  });

  const mockPrices = [
    {
      id: 'price_1',
      utilityType: 'gas',
      pricePerUnit: 0.10,
      unit: 'kWh',
      validFrom: '2024-01-01T00:00:00Z',
      validTo: '2024-12-31T23:59:59Z',
      currency: 'EUR',
      description: 'Gas price 2024',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
    {
      id: 'price_2',
      utilityType: 'water_cold',
      pricePerUnit: 2.50,
      unit: 'm³',
      validFrom: '2024-01-01T00:00:00Z',
      validTo: null,
      currency: 'EUR',
      description: 'Cold water price',
      createdAt: '2024-01-01T00:00:00Z',
      updatedAt: '2024-01-01T00:00:00Z',
    },
  ];

  it('should render price management header', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: [] }),
    });

    render(<PriceManagement />);

    expect(screen.getByText('Price Management')).toBeInTheDocument();
    expect(screen.getByText(/Configure time-based pricing/i)).toBeInTheDocument();
  });

  it('should fetch and display prices on mount', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: mockPrices }),
    });

    render(<PriceManagement />);

    await waitFor(() => {
      expect(screen.getByText('Gas')).toBeInTheDocument();
      expect(screen.getByText('Cold Water')).toBeInTheDocument();
    });
  });

  it('should display "Add New Price" button', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: [] }),
    });

    render(<PriceManagement />);

    const addButton = await screen.findByText(/Add New Price/i);
    expect(addButton).toBeInTheDocument();
  });

  it('should show create form when clicking Add New Price', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: [] }),
    });

    render(<PriceManagement />);

    const addButton = await screen.findByText(/Add New Price/i);
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText('Create New Price')).toBeInTheDocument();
    });
  });

  it('should handle filter by utility type', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ prices: mockPrices }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ prices: [mockPrices[0]] }),
      });

    render(<PriceManagement />);

    await waitFor(() => {
      expect(screen.getByText('Gas')).toBeInTheDocument();
    });

    const filterSelect = screen.getByDisplayValue('All Utilities');
    fireEvent.change(filterSelect, { target: { value: 'gas' } });

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('utilityType=gas')
      );
    });
  });

  it('should handle active prices filter', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ prices: mockPrices }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ prices: [mockPrices[1]] }),
      });

    render(<PriceManagement />);

    await waitFor(() => {
      expect(screen.getByText('Gas')).toBeInTheDocument();
    });

    const activeOnlyCheckbox = screen.getByLabelText(/Show active prices only/i);
    fireEvent.click(activeOnlyCheckbox);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('activeOnly=true')
      );
    });
  });

  it('should show loading state initially', () => {
    (global.fetch as jest.Mock).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    render(<PriceManagement />);

    expect(screen.getByText('Loading prices...')).toBeInTheDocument();
  });

  it('should show empty state when no prices exist', async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: [] }),
    });

    render(<PriceManagement />);

    await waitFor(() => {
      expect(screen.getByText(/No price configurations found/i)).toBeInTheDocument();
    });
  });

  it('should handle fetch errors gracefully', async () => {
    (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

    render(<PriceManagement />);

    await waitFor(() => {
      // Component should still render without crashing
      expect(screen.getByText('Price Management')).toBeInTheDocument();
    });
  });

  it('should display ACTIVE badge for active prices', async () => {
    const activePrice = {
      ...mockPrices[0],
      validFrom: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      validTo: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ prices: [activePrice] }),
    });

    render(<PriceManagement />);

    await waitFor(() => {
      expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    });
  });
});
