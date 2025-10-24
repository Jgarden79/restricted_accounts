# 🚀 QUICK START GUIDE

## Step 1: Install Everything
```bash
python setup.py
```

## Step 2: Set Addepar Credentials
```bash
export ADDEPAR_AUTH='username:password'
```

## Step 3: Run the App
```bash
python restriction_checker_with_addepar.py
```

## Step 4: Open Browser
Go to: http://localhost:8050

---

## 📊 What You'll See

### Top Status Bar
Shows:
- Number of Addepar accounts loaded
- When data was last updated
- Time until next auto-refresh

### Two Check Methods
1. **Single Account**: Type and check one account
2. **Bulk Upload**: Upload CSV with many accounts

### Results Show
- ✅ **Green** = Good to go (in Addepar + no restrictions)
- ❌ **Red** = Not in Addepar (problem!)
- 🚫 **Yellow** = Has trading restrictions (don't trade!)

---

## 💡 Important Features

### Daily Caching
- Addepar data loads once per day
- Saves time and API calls
- Force refresh button if needed

### Export Results
- Download button creates CSV
- Includes all check results
- Good for audit trails

---

## 🔧 Common Issues

**"Can't find Addepar accounts"**
- Check your ADDEPAR_AUTH is set correctly
- Try the force refresh button

**"Can't read restriction file"**
- Make sure Z: drive is connected
- Check you have access to the Excel file

**"App won't start"**
- Run `python setup.py` first
- Check all packages installed

---

## 📁 Files You Got

| File | Purpose |
|------|---------|
| `restriction_checker_with_addepar.py` | The main app |
| `addepar_client_list_only.py` | Lightweight Addepar module |
| `config.py` | Settings you can change |
| `setup.py` | Run this first! |
| `sample_accounts.csv` | Test file for bulk upload |

---

## 🎯 Daily Workflow

1. **Morning**: Start app (fetches fresh Addepar data)
2. **Throughout Day**: Check accounts as needed
3. **Export**: Save results for compliance records
4. **Next Day**: App auto-refreshes Addepar data

---

## 📝 CSV Upload Format

Your CSV needs one of these column names:
- Account Number
- Account #
- Account

Example:
```
Account Number
12345678
87654321
```

---

## 🔄 Force Refresh

Need immediate Addepar update?
1. Click "🔄 Force Refresh Addepar Data"
2. Wait ~30 seconds
3. Data is now current

---

## ⚡ Quick Commands

```bash
# First time setup
python setup.py

# Set credentials (do once)
export ADDEPAR_AUTH='username:password'

# Run the app
python restriction_checker_with_addepar.py

# Test with sample data
# Upload sample_accounts.csv in the app
```

---

## 📞 Need Help?

1. Check if ADDEPAR_AUTH is set
2. Make sure Z: drive is connected
3. Try force refresh button
4. Check README_ENHANCED.md for details

---

**That's it! You're ready to check account compliance!** 🎉
