# Dataset Directory

Place the dataset file here:

```
data/RewardSphere_1M_Customers.csv
```

Or keep it in the `dataset/` folder (default configured path).

## DO NOT commit the CSV file to Git.

The `.gitignore` excludes `*.csv` files from this directory.

## Quality Report

After running the ingestion script, a `data/quality_report.json` will be
generated here. This file is also excluded from Git.
