# test_scraper.py - Updated v2
# Tests the improved scraper with:
#   - Targeted queries per subsystem
#   - Fixed OSTI URLs
#   - Relevance filtering

from src.tools.search_tools import MARVELSearcherSimple
from config.subsystems import MARVEL_SUBSYSTEMS
import json
import os


def test_single_subsystem(subsystem_key: str = "heat_transport"):
    """Test scraping for a single subsystem with full diagnostics."""

    os.makedirs("data/raw", exist_ok=True)

    searcher = MARVELSearcherSimple(max_results_per_query=10)

    results = searcher.search_subsystem(
        subsystem_key,
        MARVEL_SUBSYSTEMS[subsystem_key]
    )

    # Save results
    output_path = f"data/raw/{subsystem_key}_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Subsystem:       {results['name']}")
    print(f"Total relevant:  {results['total_documents']}")

    stats = results["relevance_stats"]
    print(f"\nOSTI:  {stats['osti_relevant']} relevant / {stats['osti_fetched']} fetched")
    print(f"arXiv: {stats['arxiv_relevant']} relevant / {stats['arxiv_fetched']} fetched")
    print(f"Filtered out:    {stats['total_filtered_out']} irrelevant results")

    # Show sample OSTI result — verify URL is now populated
    if results["osti_results"]:
        print(f"\n📄 Sample OSTI result:")
        s = results["osti_results"][0]
        print(f"   Title:  {s['title'][:80]}")
        print(f"   URL:    {s['url']}")          # Should now show https://www.osti.gov/biblio/...
        print(f"   DOI:    {s.get('doi_url', 'None')}")
        print(f"   Date:   {s.get('publication_date', 'N/A')}")
        print(f"   Org:    {s.get('research_org', 'N/A')[:60]}")

    if results["arxiv_results"]:
        print(f"\n📄 Sample arXiv result:")
        s = results["arxiv_results"][0]
        print(f"   Title:  {s['title'][:80]}")
        print(f"   URL:    {s['url']}")
        print(f"   PDF:    {s['pdf_url']}")
        print(f"   Date:   {s['publication_date']}")

    print(f"\n💾 Saved to: {output_path}")
    return results


def test_all_subsystems():
    """Run scraper for all 6 MARVEL subsystems."""
    os.makedirs("data/raw", exist_ok=True)

    searcher = MARVELSearcherSimple(max_results_per_query=10)
    all_results = {}

    for key, config in MARVEL_SUBSYSTEMS.items():
        results = searcher.search_subsystem(key, config)
        all_results[key] = results

        output_path = f"data/raw/{key}_results.json"
        with open(output_path, "w") as f:
            json.dump(results, f, indent=2)

    # Print overall summary
    print("\n" + "="*60)
    print("ALL SUBSYSTEMS SUMMARY")
    print("="*60)
    total = 0
    for key, r in all_results.items():
        n = r["total_documents"]
        total += n
        print(f"  {r['name'][:45]:<45} {n:>3} docs")
    print(f"\n  TOTAL: {total} relevant documents")

    return all_results


if __name__ == "__main__":
    print("MARVEL TRL Assessment - Improved Scraper v2")
    print("Using: OSTI + arXiv | Targeted queries | Relevance filter")
    print("="*60)

    # Test single subsystem first
    #test_single_subsystem("heat_transport")

    # Uncomment to run all subsystems:
    test_all_subsystems()