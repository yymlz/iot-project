#!/usr/bin/env python3
"""
Quick graph generator for TinyTelemetry test results
Generates:
1. bytes_per_report vs reporting_interval (1s, 5s, 30s)
2. duplicate_rate vs loss

Usage: python3 make_graphs.py [csv_file] [output_dir]
  csv_file: Path to telemetry CSV file (default: ../src/telemetry_*.csv - finds latest)
  output_dir: Output directory for graphs (default: graphs)
"""

import pandas as pd
import matplotlib.pyplot as plt
import os
import sys
import glob

# Parse command line arguments
if len(sys.argv) > 1:
    csv_file = sys.argv[1]
else:
    # Find most recent telemetry CSV file
    csv_files = glob.glob('../src/telemetry_*.csv') + glob.glob('../logs/telemetry_*.csv')
    if not csv_files:
        print("Error: No telemetry CSV files found!")
        print("Usage: python3 make_graphs.py <csv_file> [output_dir]")
        sys.exit(1)
    csv_file = max(csv_files, key=os.path.getmtime)
    print(f"Auto-detected latest CSV: {csv_file}")

output_dir = sys.argv[2] if len(sys.argv) > 2 else 'graphs'

# Validate CSV file exists
if not os.path.exists(csv_file):
    print(f"Error: CSV file not found: {csv_file}")
    sys.exit(1)

# Load CSV file
print(f"Loading data from: {csv_file}")
df = pd.read_csv(csv_file)

# Create output directory
os.makedirs(output_dir, exist_ok=True)

print(f"Loaded {len(df)} packets from {len(df['device_id'].unique())} devices")

# ============================================================================
# GRAPH 1: bytes_per_report vs reporting_interval (1s, 5s, 30s)
# ============================================================================

# Map device IDs to intervals based on your test plan
# Baseline tests: 1001(1s), 1002(5s), 1003(30s)
# Pattern continues for each test type

interval_mapping = {
    # Baseline
    1001: 1, 1002: 5, 1003: 30,
    # Loss 5%
    1004: 1, 1005: 5, 1006: 30,
    # Loss 10%
    1007: 1, 1008: 5, 1009: 30,
    # Loss 15%
    1010: 1, 1011: 5, 1012: 30,
    # Delay 50ms
    1013: 1, 1014: 5, 1015: 30,
    # Delay 100ms
    1016: 1, 1017: 5, 1018: 30,
    # Delay 200ms
    1019: 1, 1020: 5, 1021: 30,
    # Jitter 100±10
    1022: 1, 1023: 5, 1024: 30,
    # Jitter 100±50
    1025: 1, 1026: 5, 1027: 30,
    # Reorder 25%
    1028: 1, 1029: 5, 1030: 30,
    # Reorder 50%
    1031: 1, 1032: 5, 1033: 30,
    # Duplicate 5%
    1034: 1, 1035: 5, 1036: 30,
    # Combined Light
    1037: 1, 1038: 5, 1039: 30,
    # Combined Medium
    1040: 1, 1041: 5, 1042: 30,
    # Combined Harsh
    1043: 1, 1044: 5, 1045: 30,
    # Batch size tests
    1046: 1, 1047: 5, 1048: 30,
    1049: 1, 1050: 5, 1051: 30,
    1052: 1, 1053: 5, 1054: 30,
    # Client loss + network loss
    1055: 1, 1056: 5, 1057: 30,
    # Client jitter + network delay
    1058: 1, 1059: 5, 1060: 30,
}

df['interval'] = df['device_id'].map(interval_mapping)

# Calculate average bytes per interval
interval_stats = df.groupby('interval').agg({
    'packet_bytes': 'mean',
    'device_id': 'nunique'
}).reset_index()

interval_stats = interval_stats.sort_values('interval')

plt.figure(figsize=(10, 6))
bars = plt.bar(
    interval_stats['interval'].astype(str) + 's',
    interval_stats['packet_bytes'],
    color=['#3498db', '#2ecc71', '#e74c3c'],
    edgecolor='black',
    linewidth=1.5
)

plt.xlabel('Reporting Interval', fontsize=14, fontweight='bold')
plt.ylabel('Average Bytes per Report', fontsize=14, fontweight='bold')
plt.title('Packet Size vs Reporting Interval', fontsize=16, fontweight='bold', pad=20)
plt.grid(axis='y', alpha=0.3, linestyle='--')

# Add value labels on bars
for bar, (_, row) in zip(bars, interval_stats.iterrows()):
    height = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2., height + 2,
            f'{height:.1f} bytes\n({row["device_id"]} tests)',
            ha='center', va='bottom', fontweight='bold', fontsize=11)

plt.ylim(0, max(interval_stats['packet_bytes']) * 1.15)
plt.tight_layout()
plt.savefig(f'{output_dir}/bytes_vs_interval.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir}/bytes_vs_interval.png")
plt.close()

# ============================================================================
# GRAPH 2: duplicate_rate vs loss
# ============================================================================

# Map device IDs to loss percentage
loss_mapping = {
    # No loss
    1001: 0, 1002: 0, 1003: 0,
    # 5% loss
    1004: 5, 1005: 5, 1006: 5,
    # 10% loss
    1007: 10, 1008: 10, 1009: 10,
    # 15% loss
    1010: 15, 1011: 15, 1012: 15,
    # Batch size with 10% loss
    1046: 10, 1047: 10, 1048: 10,
    1049: 10, 1050: 10, 1051: 10,
    1052: 10, 1053: 10, 1054: 10,
    # Client+network 5%+5% = 10% total
    1055: 10, 1056: 10, 1057: 10,
}

df['network_loss'] = df['device_id'].map(loss_mapping)

# Filter only devices with loss data
loss_df = df[df['network_loss'].notna()]

# Calculate duplicate rate per device
device_stats = loss_df.groupby('device_id').agg({
    'duplicate_flag': lambda x: (x.sum() / len(x) * 100),
    'network_loss': 'first'
}).reset_index()

device_stats.columns = ['device_id', 'duplicate_rate', 'network_loss']

# Group by loss percentage
loss_stats = device_stats.groupby('network_loss').agg({
    'duplicate_rate': 'mean',
    'device_id': 'count'
}).reset_index()

loss_stats.columns = ['network_loss', 'avg_duplicate_rate', 'num_tests']
loss_stats = loss_stats.sort_values('network_loss')

plt.figure(figsize=(10, 6))
plt.plot(
    loss_stats['network_loss'],
    loss_stats['avg_duplicate_rate'],
    marker='o',
    linewidth=3,
    markersize=12,
    color='#e74c3c',
    markeredgecolor='darkred',
    markeredgewidth=2
)

plt.xlabel('Network Loss Rate (%)', fontsize=14, fontweight='bold')
plt.ylabel('Average Duplicate Rate (%)', fontsize=14, fontweight='bold')
plt.title('Duplicate Packets vs Network Loss Rate', fontsize=16, fontweight='bold', pad=20)
plt.grid(True, alpha=0.3, linestyle='--')

# Add value labels
for _, row in loss_stats.iterrows():
    plt.text(
        row['network_loss'],
        row['avg_duplicate_rate'] + 0.05,
        f"{row['avg_duplicate_rate']:.2f}%\n({int(row['num_tests'])} tests)",
        ha='center',
        va='bottom',
        fontweight='bold',
        fontsize=10,
        bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.3)
    )

plt.xlim(-0.5, max(loss_stats['network_loss']) + 0.5)
plt.tight_layout()
plt.savefig(f'{output_dir}/duplicate_vs_loss.png', dpi=300, bbox_inches='tight')
print(f"✓ Saved: {output_dir}/duplicate_vs_loss.png")
plt.close()

# ============================================================================
# Summary
# ============================================================================

print("\n" + "="*60)
print("GRAPH GENERATION COMPLETE")
print("="*60)
print(f"\nInput file: {csv_file}")
print(f"Output directory: {output_dir}/")
print(f"\nInterval analysis:")
for _, row in interval_stats.iterrows():
    print(f"  {int(row['interval'])}s interval: {row['packet_bytes']:.1f} bytes/report ({int(row['device_id'])} tests)")

print(f"\nLoss vs Duplicate analysis:")
for _, row in loss_stats.iterrows():
    print(f"  {int(row['network_loss'])}% loss: {row['avg_duplicate_rate']:.2f}% duplicates ({int(row['num_tests'])} tests)")

print("\nGenerated graphs:")
print(f"  📊 {output_dir}/bytes_vs_interval.png")
print(f"  📊 {output_dir}/duplicate_vs_loss.png")
print("="*60)
