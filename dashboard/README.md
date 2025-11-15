# Utility Meter Dashboard

A modern, responsive Next.js dashboard for visualizing utility meter data from InfluxDB. This dashboard provides real-time monitoring and analysis of electricity, gas, and water consumption, along with water temperature data from Bavarian lakes.

## Features

- **Time Range Selection**: Choose from preset ranges (last 7 days, 30 days, 3 months, etc.) or select a custom date range
- **Meter Selection**: Select which meters to display on the dashboard
- **Real-time Charts**:
  - Raw meter readings visualization
  - Interpolated readings for gap filling
  - Water temperature trends from Bavarian lakes
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Fast Performance**: Built with Next.js 15 and React for optimal performance

## Prerequisites

- Node.js 18+ and npm
- An InfluxDB instance with utility meter data
- InfluxDB access token with read permissions

## Installation

1. Navigate to the dashboard directory:
```bash
cd dashboard
```

2. Install dependencies:
```bash
npm install
```

3. Configure environment variables:

Copy `.env.example` to `.env.local` and update with your InfluxDB credentials:

```env
# InfluxDB Configuration
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your_influx_token_here
INFLUX_ORG=your_org_name
INFLUX_BUCKET_RAW=homeassistant_raw
INFLUX_BUCKET_PROCESSED=homeassistant_processed

# Gas Conversion Parameters
GAS_ENERGY_CONTENT=10.3
GAS_Z_FACTOR=0.95
```

## Running the Dashboard

### Development Mode

```bash
npm run dev
```

The dashboard will be available at [http://localhost:3000](http://localhost:3000)

### Production Build

```bash
npm run build
npm start
```

## Data Sources

The dashboard fetches data from InfluxDB with the following structure:

### Meter Readings
- **Measurement**: `kWh` or `m³`
- **Field**: `value`
- **Tags**: `entity_id` (meter identifier)

### Water Temperature
- **Measurement**: `°C`
- **Field**: `value`
- **Tags**: `entity_id`, `lake`, `source`

## Supported Meters

The dashboard is pre-configured to display the following meters:

- **Gas**:
  - Gas Meter (m³)
  - Gas Heating (kWh)

- **Electricity**:
  - Electricity NT (Night Tariff)
  - Electricity HT (Day Tariff)
  - Main Electricity
  - Ground Floor Electricity
  - 1st Floor Electricity
  - 2nd Floor Electricity

- **Water**:
  - Cold Water
  - Hot Water

- **Environmental**:
  - Water temperature from Bavarian lakes (Schliersee, Tegernsee, Isar)

## Architecture

- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Recharts
- **Data Source**: InfluxDB via `@influxdata/influxdb-client`
- **Date Handling**: date-fns

## API Routes

- `GET /api/meters` - List all available meters
- `GET /api/readings?meterId=<id>&startDate=<date>&endDate=<date>` - Fetch meter readings
- `GET /api/water-temp?startDate=<date>&endDate=<date>` - Fetch water temperature data

## Customization

### Adding New Meters

Edit `app/page.tsx` and add entries to the `METERS_CONFIG` array:

```typescript
const METERS_CONFIG = [
  { id: 'your_meter_id', unit: 'kWh', name: 'Your Meter Name' },
  // ... other meters
];
```

### Changing Chart Colors

Edit the chart components in the `components/` directory and modify the color properties.

### Adjusting Time Ranges

Edit `components/TimeRangeSelector.tsx` to add or modify preset time ranges.

## Project Structure

```
dashboard/
├── app/
│   ├── api/              # API routes for data fetching
│   │   ├── meters/       # Meter discovery endpoint
│   │   ├── readings/     # Meter readings endpoint
│   │   └── water-temp/   # Water temperature endpoint
│   ├── page.tsx          # Main dashboard page
│   └── layout.tsx        # Root layout
├── components/           # React components
│   ├── TimeRangeSelector.tsx
│   ├── MeterReadingsChart.tsx
│   ├── ConsumptionChart.tsx
│   ├── BreakdownChart.tsx
│   └── WaterTemperatureChart.tsx
├── lib/
│   └── influxdb.ts       # InfluxDB client utilities
└── public/               # Static assets
```

## Troubleshooting

### No data showing in charts

1. Verify InfluxDB credentials in `.env.local`
2. Check that your InfluxDB instance is running and accessible
3. Ensure the bucket name matches your InfluxDB configuration
4. Check browser console for API errors

### Charts rendering incorrectly

1. Clear browser cache
2. Restart the development server
3. Check that meter IDs in `METERS_CONFIG` match your InfluxDB entity IDs

## Performance Optimization

- Charts only fetch data for selected meters
- Data is fetched in parallel using Promise.all
- Time range is validated before queries
- Responsive design reduces unnecessary re-renders

## License

This project is part of the nebenkosten utility analysis system.
