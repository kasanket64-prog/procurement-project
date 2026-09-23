import pandas as pd

df = pd.read_csv("dataset/procurement.csv")

print("Dataset size:")
print(df.shape)

print("\nColumns:")
print(df.columns)

print("\nMissing values:")
print(df.isnull().sum())

print("\nData types:")
print(df.dtypes)
# Convert text dates into real dates
df["order_date"] = pd.to_datetime(df["order_date"])
df["promised_delivery_date"] = pd.to_datetime(df["promised_delivery_date"])
df["actual_delivery_date"] = pd.to_datetime(df["actual_delivery_date"])

# Calculate delivery delay
df["delivery_delay_days"] = (
    df["actual_delivery_date"] - df["promised_delivery_date"]
).dt.days

# Create target
df["late_delivery"] = (df["delivery_delay_days"] > 0).astype(int)

print("\nDelivery delay sample:")
print(
    df[
        [
            "promised_delivery_date",
            "actual_delivery_date",
            "delivery_delay_days",
            "late_delivery"
        ]
    ].head(10)
)

print("\nLate delivery counts:")
print(df["late_delivery"].value_counts())

print("\nLate delivery percentage:")
print(df["late_delivery"].value_counts(normalize=True) * 100)