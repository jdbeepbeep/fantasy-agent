"""
Isolated test of the consensus rankings call, completely outside
Streamlit -- helps tell whether a slowdown is in the API call itself
or something in how Streamlit is running it.

Usage: python3 test_consensus.py
"""
import time
from src.consensus import fetch_consensus_rankings

if __name__ == "__main__":
    print("Starting request -- may take up to 3 minutes before timing out...")
    start = time.time()
    rankings = fetch_consensus_rankings("PPR", top_n=50)  # smaller for a faster test
    elapsed = time.time() - start
    print(f"\nDone in {elapsed:.1f} seconds.")
    print(f"Got {len(rankings)} ranked players.")
    if rankings:
        sample = list(rankings.items())[:5]
        print("Sample:", sample)
