#!/usr/bin/env python3
"""
Analyze test results and generate graphs
"""

import pandas as pd
import matplotlib.pyplot as plt
import sys
import os
from pathlib import Path

def load_csv_data(csv_file):
    """Load telemetry CSV data"""
    df = pd.read_csv(csv_file)
    return df

def calculate_metrics(df, device_id):
    """Calculate metrics for a specific device"""
    device_df = df[df['device_id'] == device_id]
    
    if len(device_df) == 0:
        return None
    
    # Calculate bytes per report (average packet size)
    avg_bytes = device_df['packet_bytes'].mean()
    
    # Calculate duplicate rate
    duplicates = device_df['duplicate_flag'].sum()
    total_packets = len(device_df)
    duplicate_rate = (duplicates / total_packets * 100) if total_packets > 0 else 0
    
    # Calculate loss (sequence gaps)
    gaps = device_df['gap_flag'].sum()
    gap_rate = (gaps / total_packets * 100) if total_packets > 0 else 0
    
    return {
        'device_id': device_id,
        'avg_bytes': avg_bytes,
        'duplicate_rate': duplicate_rate,
        'gap_rate': gap_rate,
        'total_packets': total_packets
    }

def analyze_test_results(test_csv, telemetry_csv):
    """Analyze results from test run"""
    
    # Load test configuration
    test_df = pd.read_csv(test_csv)
    
    # Load telemetry data
    telemetry_df = pd.read_csv(telemetry_csv)
    
    results = []
    
    for _, test in test_df.iterrows():
        device_id = test['device_id']
        duration = test['duration']
        netem = test['netem_config']
        
        metrics = calculate_metrics(telemetry_df, device_id)
        
        if metrics:
            results.append({
                'test_name': test['test_name'],
                'device_id': device_id,
                'duration': duration,
                'netem_config': netem,
                'avg_bytes': metrics['avg_bytes'],
                'duplicate_rate': metrics['duplicate_rate'],
                'gap_rate': metrics['gap_rate'],
                'total_packets': metrics['total_packets']
            })
    
    return pd.DataFrame(results)

def plot_bytes_vs_interval(results_df, output_file='bytes_vs_interval.png'):
    """
    Graph 1: bytes_per_report vs reporting_interval (1s, 5s, 30s)
    Shows how packet size varies with different test durations
    """
    
    # Filter baseline tests (no network impairment)
    baseline = results_df[results_df['netem_config'] == 'none']
    
    if len(baseline) == 0:
        print("No baseline data found. Showing all tests grouped by duration.")
        data = results_df
    else:
        data = baseline
    
    # Group by duration and calculate mean
    grouped = data.groupby('duration')['avg_bytes'].mean().reset_index()
    grouped = grouped.sort_values('duration')
    
    plt.figure(figsize=(10, 6))
    plt.bar(grouped['duration'].astype(str) + 's', grouped['avg_bytes'], 
            color=['#3498db', '#2ecc71', '#e74c3c'])
    plt.xlabel('Reporting Interval', fontsize=12, fontweight='bold')
    plt.ylabel('Average Bytes per Report', fontsize=12, fontweight='bold')
    plt.title('Packet Size vs Reporting Interval', fontsize=14, fontweight='bold')
    plt.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, row in grouped.iterrows():
        plt.text(i, row['avg_bytes'] + 2, f"{row['avg_bytes']:.1f}", 
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def plot_duplicate_vs_loss(results_df, output_file='duplicate_vs_loss.png'):
    """
    Graph 2: duplicate_rate vs network loss
    Shows correlation between packet loss and duplicate packets
    """
    
    # Extract loss percentage from netem_config
    def extract_loss(netem_str):
        if 'loss' in netem_str:
            parts = netem_str.split()
            for i, part in enumerate(parts):
                if part == 'loss' and i + 1 < len(parts):
                    return float(parts[i + 1].rstrip('%'))
        return 0.0
    
    results_df['network_loss'] = results_df['netem_config'].apply(extract_loss)
    
    # Filter tests with loss only (exclude combined impairments for clarity)
    loss_tests = results_df[
        (results_df['network_loss'] > 0) & 
        (~results_df['netem_config'].str.contains('delay|reorder|duplicate', case=False, na=False))
    ]
    
    if len(loss_tests) == 0:
        print("No pure loss tests found. Using all tests with loss component.")
        loss_tests = results_df[results_df['network_loss'] > 0]
    
    # Group by network loss level and calculate mean duplicate rate
    grouped = loss_tests.groupby('network_loss')['duplicate_rate'].mean().reset_index()
    grouped = grouped.sort_values('network_loss')
    
    plt.figure(figsize=(10, 6))
    plt.plot(grouped['network_loss'], grouped['duplicate_rate'], 
            marker='o', linewidth=2, markersize=8, color='#e74c3c')
    plt.xlabel('Network Loss Rate (%)', fontsize=12, fontweight='bold')
    plt.ylabel('Duplicate Rate (%)', fontsize=12, fontweight='bold')
    plt.title('Duplicate Packets vs Network Loss', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    # Add value labels
    for _, row in grouped.iterrows():
        plt.text(row['network_loss'], row['duplicate_rate'] + 0.1, 
                f"{row['duplicate_rate']:.2f}%", 
                ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close()

def plot_all_metrics(results_df, output_dir='graphs'):
    """Generate additional useful graphs"""
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Graph 3: Loss rate comparison across different network conditions
    plt.figure(figsize=(12, 6))
    
    # Get tests with different conditions (sample up to 10 for readability)
    sample_tests = results_df.head(15)
    
    x_labels = [f"{row['test_name'][:30]}..." if len(row['test_name']) > 30 
                else row['test_name'] for _, row in sample_tests.iterrows()]
    
    plt.bar(range(len(sample_tests)), sample_tests['gap_rate'], color='#e67e22')
    plt.xlabel('Test Scenario', fontsize=12, fontweight='bold')
    plt.ylabel('Packet Loss Rate (%)', fontsize=12, fontweight='bold')
    plt.title('Packet Loss Across Different Test Scenarios', fontsize=14, fontweight='bold')
    plt.xticks(range(len(sample_tests)), x_labels, rotation=45, ha='right', fontsize=8)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/loss_comparison.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir}/loss_comparison.png")
    plt.close()
    
    # Graph 4: Duration impact on total packets received
    plt.figure(figsize=(10, 6))
    duration_packets = results_df.groupby('duration')['total_packets'].mean().reset_index()
    duration_packets = duration_packets.sort_values('duration')
    
    plt.plot(duration_packets['duration'], duration_packets['total_packets'], 
            marker='s', linewidth=2, markersize=10, color='#9b59b6')
    plt.xlabel('Test Duration (seconds)', fontsize=12, fontweight='bold')
    plt.ylabel('Average Packets Received', fontsize=12, fontweight='bold')
    plt.title('Packets Received vs Test Duration', fontsize=14, fontweight='bold')
    plt.grid(True, alpha=0.3)
    
    for _, row in duration_packets.iterrows():
        plt.text(row['duration'], row['total_packets'] + 0.5, 
                f"{row['total_packets']:.0f}", 
                ha='center', va='bottom', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f'{output_dir}/duration_packets.png', dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_dir}/duration_packets.png")
    plt.close()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_results.py <telemetry_csv> [test_results_csv]")
        print("\nExample:")
        print("  python3 analyze_results.py ../src/telemetry_20251210_224834.csv")
        print("  python3 analyze_results.py ../src/telemetry_20251210_224834.csv ../logs/test_results_20251210.csv")
        sys.exit(1)
    
    telemetry_csv = sys.argv[1]
    test_csv = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(telemetry_csv):
        print(f"Error: Telemetry CSV not found: {telemetry_csv}")
        sys.exit(1)
    
    print(f"Loading telemetry data from: {telemetry_csv}")
    telemetry_df = pd.read_csv(telemetry_csv)
    
    if test_csv and os.path.exists(test_csv):
        print(f"Loading test configuration from: {test_csv}")
        results_df = analyze_test_results(test_csv, telemetry_csv)
    else:
        print("No test CSV provided. Analyzing telemetry data directly...")
        
        # Get unique device IDs
        device_ids = telemetry_df['device_id'].unique()
        
        results = []
        for device_id in device_ids:
            metrics = calculate_metrics(telemetry_df, device_id)
            if metrics:
                # Infer duration and test type from device_id ranges
                if 1001 <= device_id <= 1003:
                    duration = [1, 5, 30][device_id - 1001]
                    test_name = f"Baseline ({duration}s)"
                    netem = "none"
                elif device_id >= 1004:
                    # Estimate based on naming pattern
                    duration = 30  # default
                    test_name = f"Test {device_id}"
                    netem = "unknown"
                else:
                    duration = 30
                    test_name = f"Device {device_id}"
                    netem = "unknown"
                
                results.append({
                    'test_name': test_name,
                    'device_id': device_id,
                    'duration': duration,
                    'netem_config': netem,
                    'avg_bytes': metrics['avg_bytes'],
                    'duplicate_rate': metrics['duplicate_rate'],
                    'gap_rate': metrics['gap_rate'],
                    'total_packets': metrics['total_packets']
                })
        
        results_df = pd.DataFrame(results)
    
    print(f"\nAnalyzing {len(results_df)} test results...")
    print("\nGenerating graphs...")
    
    # Create output directory
    output_dir = 'graphs'
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate main graphs
    plot_bytes_vs_interval(results_df, f'{output_dir}/bytes_vs_interval.png')
    plot_duplicate_vs_loss(results_df, f'{output_dir}/duplicate_vs_loss.png')
    
    # Generate additional graphs
    plot_all_metrics(results_df, output_dir)
    
    # Save analysis summary
    summary_file = f'{output_dir}/analysis_summary.csv'
    results_df.to_csv(summary_file, index=False)
    print(f"\n✓ Saved analysis summary: {summary_file}")
    
    print("\n" + "="*60)
    print("ANALYSIS COMPLETE")
    print("="*60)
    print(f"Total tests analyzed: {len(results_df)}")
    print(f"Output directory: {output_dir}/")
    print("\nGenerated files:")
    print("  - bytes_vs_interval.png")
    print("  - duplicate_vs_loss.png")
    print("  - loss_comparison.png")
    print("  - duration_packets.png")
    print("  - analysis_summary.csv")
    print("="*60)

if __name__ == '__main__':
    main()
