# Real-Time Inventory Updater 🍪

This system fetches current sales data from Clover and Shopify APIs and updates the "Sold as of NOW" columns in your inventory Google Sheet in real-time.

## 🎯 What It Does

- **Fetches recent sales** from Clover and Shopify (last 1 hour by default)
- **Maps cookie names** from APIs to inventory sheet names
- **Updates "Sold as of NOW" columns** for each location
- **Runs continuously** every 15 minutes (or custom interval)
- **Handles multiple locations** (San Patricio, Plaza del Sol, Plaza Las Americas, Old San Juan)

## 🚀 Quick Start

### 1. Test Run (Once)
```bash
python inventory_updater.py --once
```

### 2. Continuous Updates (15 minutes)
```bash
python inventory_updater.py
```

### 3. Custom Settings
```bash
# Update every 5 minutes (300 seconds)
python inventory_updater.py --interval 300

# Fetch last 2 hours of data
python inventory_updater.py --hours 2

# Update every minute
python inventory_updater.py --interval 60
```

## 📊 Cookie Mapping

The system maps cookie names from your APIs to the inventory sheet:

| API Name | Inventory Sheet Name |
|----------|---------------------|
| Chocolate Chip Nutella | A - Chocolate Chip Nutella |
| Signature Chocolate Chip | B - Signature Chocolate Chip |
| Cookies & Cream | C - Cookies & Cream |
| White Chocolate Macadamia | D - White Chocolate Macadamia |
| Churro With Dulce de Leche | E - Churro with Dulce De Leche |
| Cheesecake with Biscoff | F - Cheesecake with Biscoff |
| Rocky Road | G - Rocky Road |
| Pecan Pie | H - Pecan Pie |
| Tres Leches | I - Tres Leches |
| Fudge Brownie | J - Fudge Brownie |
| Strawberry Cheesecake | K - Strawberry Cheesecake |
| S'mores | L - S'mores |
| Ube with Oreo | M - Ube with Oreo |
| Midnight Nutella | N - Midnight Nutella |

## 📍 Location Mapping

| API Location | Inventory Sheet Location |
|--------------|-------------------------|
| VSJ | San Patricio |
| San Patricio | San Patricio |
| Plaza Del Sol | Plaza del Sol |
| Plaza Las Americas | Plaza Las Americas |
| Old San Juan | Old San Juan |

## ⚙️ Configuration

### Google Sheet ID
The system is configured to update: `1zR0tPkqxMOijgQsmjLvg0cN2MlUuHlCB5VgNbNv3grU`

### Sheet Tab Format
Uses date format: `9-1` for September 1st

### Update Intervals
- **San Patricio**: Every 15 minutes
- **Plaza del Sol**: Every 1 minute  
- **Plaza Las Americas**: Every 1 minute
- **Old San Juan**: Every 1 minute

## 🔧 Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure credentials exist**:
   - `../secrets/clover_creds.json`
   - `../secrets/shopify_creds.json`
   - `../secrets/google_creds.json`

3. **First run will prompt for Google OAuth**

## 📈 How It Works

1. **Fetches orders** from Clover and Shopify APIs
2. **Counts cookies sold** in the specified time period
3. **Maps to inventory sheet** cookie names and locations
4. **Updates "Sold as of NOW" columns** in the Google Sheet
5. **Waits for next interval** and repeats

## 🛠️ Troubleshooting

### Common Issues

1. **"No data found in sheet tab"**
   - Check if the sheet tab exists (e.g., "9-1" for September 1st)
   - Ensure the tab name matches the current date format

2. **"Location not found in sheet"**
   - Verify location mapping in the code
   - Check if location names match exactly

3. **"Error fetching orders"**
   - Check API credentials
   - Verify network connectivity
   - Check API rate limits

### Logs
The system provides detailed logging:
- ✅ Successful updates
- ❌ Errors and retries
- 📊 Sales data summary
- ⏰ Next update timing

## 🔄 Integration with Daily Reports

This real-time system works alongside your daily reports:
- **Real-time**: Updates "Sold as of NOW" columns every 15 minutes/1 minute
- **Daily**: Your existing system runs at 12:01 AM for complete daily summaries

Both systems can run simultaneously without conflicts!






