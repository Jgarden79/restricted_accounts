# Enhanced Account Compliance Checker

A comprehensive Dash web application that cross-references accounts against both **Trading Restrictions** and **Addepar Client List** to ensure compliance before processing transactions.

## 🎯 Key Features

### Dual Verification System
- **Trading Restrictions Check**: Validates against your restriction tracker Excel file
- **Addepar Validation**: Confirms accounts exist in your Addepar system
- **Combined Status**: Provides clear overall compliance status

### Smart Caching
- **Daily Cache**: Addepar data cached for 24 hours to minimize API calls
- **Manual Refresh**: Force refresh button when immediate updates needed
- **Persistent Storage**: Cache survives app restarts

### Status Indicators
- ✅ **ALL CLEAR**: Account exists in Addepar AND has no restrictions
- ❌ **NOT IN ADDEPAR**: Account not found in Addepar system
- 🚫 **RESTRICTED**: Account has trading restrictions
- ⚠️ **ERROR**: Unable to verify status

## 📋 Prerequisites

1. **Python 3.6+**
2. **Network Access** to:
   - Restriction tracker Excel file on shared drive
   - Addepar API
3. **Addepar API Credentials**

## 🚀 Quick Start

### 1. Run Setup
```bash
python setup.py
```

### 2. Set Addepar Credentials
```bash
# Mac/Linux
export ADDEPAR_AUTH='username:password'

# Windows
set ADDEPAR_AUTH=username:password
```

### 3. Launch the App
```bash
python restriction_checker_with_addepar.py
```

### 4. Open Browser
Navigate to: `http://localhost:8050`

## 📁 File Structure

```
.
├── restriction_checker_with_addepar.py  # Main application
├── addepar_client_list_only.py         # Lightweight Addepar module
├── config.py                            # Configuration settings
├── setup.py                             # Setup script
├── cache/                               # Cached Addepar data
│   └── addepar_clients.pkl            # Pickled client data
└── run_app.sh / run_app.bat           # Convenient run scripts
```

## 💻 Usage

### Single Account Check
1. Enter account number in the input field
2. Click "Check Account"
3. View detailed status breakdown

### Bulk Account Check
1. Prepare CSV file with account numbers
2. Drag & drop or click to upload
3. Review comprehensive results table
4. Download results as CSV

### CSV Format
Your CSV should have account numbers in a column named:
- Account
- Account #
- Account Number
- (or similar variations)

Example:
```csv
Account Number
64314903
64314905
64314906
```

## 🔄 Cache Management

### Automatic Caching
- Addepar data fetched once per day
- Cache age displayed in status bar
- Automatic refresh after 24 hours

### Manual Cache Control
- Click "🔄 Force Refresh Addepar Data" for immediate update
- Delete `cache/addepar_clients.pkl` to force refresh on next start

## 📊 Results Table

The results table shows:
- **Account Number**: Original account ID
- **In Addepar**: Yes/No indicator
- **Trading Status**: Restricted/Clear
- **Overall Status**: Combined compliance status

Color coding:
- 🟢 Green: All clear accounts
- 🔴 Red: Not in Addepar
- 🟡 Yellow: Trading restrictions

## ⚙️ Configuration

Edit `config.py` to customize:

```python
# Addepar Settings
ADDEPAR_FIRM_ID = "222"
ADDEPAR_CLIENT_LIST_VIEW_ID = 420336

# Restriction File Path
RESTRICTION_FILE_PATH = r"Z:\Shared\..."

# Cache Duration (hours)
CACHE_DURATION_HOURS = 24

# App Port
APP_PORT = 8050
```

## 📈 Performance

- **Initial Load**: ~30-60 seconds (fetching Addepar data)
- **Cached Operations**: <1 second per account check
- **Bulk Processing**: ~100 accounts/second

## 🛠️ Troubleshooting

### "ADDEPAR_AUTH not set"
Set environment variable:
```bash
export ADDEPAR_AUTH='username:password'
```

### "Cannot access restriction file"
- Verify network drive is mounted
- Check file path in `config.py`
- Ensure read permissions

### "Addepar data not loading"
- Check API credentials
- Verify network connectivity
- Try force refresh button

### Cache Issues
```bash
# Clear cache manually
rm cache/addepar_clients.pkl
```

## 📦 Dependencies

- `pandas`: Data manipulation
- `dash`: Web framework
- `dash-bootstrap-components`: UI components
- `requests`: API calls
- `openpyxl`: Excel file reading

## 🔒 Security Notes

- Never commit credentials to version control
- Use environment variables for sensitive data
- Cache files contain account information - secure appropriately
- Consider network security when deploying

## 📝 Export Options

Results can be exported as CSV with:
- Account numbers
- Addepar status
- Restriction status
- Overall compliance status
- Timestamp (optional)

## 🎨 Customization

The app can be extended with:
- Additional data sources
- Custom validation rules
- Email notifications
- Audit logging
- Database integration

## 📞 Support

For issues or questions:
1. Check troubleshooting section
2. Review `restriction_checker.log` if logging enabled
3. Verify all paths and credentials in `config.py`

## 🚦 Status Summary

| Status | Meaning | Action Required |
|--------|---------|-----------------|
| ✅ ALL CLEAR | Account verified in both systems | Safe to proceed |
| ❌ NOT IN ADDEPAR | Account missing from Addepar | Investigate/Add to Addepar |
| 🚫 RESTRICTED | Trading restrictions active | Do not trade |
| ⚠️ ERROR | Verification failed | Check connections/permissions |

## 🔄 Workflow

1. **Daily Start**: App fetches fresh Addepar data (cached 24hrs)
2. **Account Entry**: User enters single or bulk accounts
3. **Dual Check**: System verifies against both sources
4. **Status Report**: Clear visual indicators show results
5. **Export**: Download results for documentation

---

**Version**: 1.0.0  
**Last Updated**: 2024
