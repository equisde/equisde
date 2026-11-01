#!/usr/bin/env python3
"""
Generate bulletproof, statically hosted GitHub Stats and Top Languages SVGs
with Tokyo Night / Cyberpunk theme matching equisde's profile aesthetic.
Eliminates all third-party Vercel rate-limit and 'Maximum retries exceeded' errors.
"""

import json
import os
from pathlib import Path
import subprocess
import sys

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr.strip() or f"Command failed: {cmd}", file=sys.stderr)
        return ""
    return result.stdout.strip()

def fetch_github_data():
    query = '''
    query {
      user(login: "equisde") {
        name
        login
        followers { totalCount }
        following { totalCount }
        contributionsCollection {
          totalCommitContributions
          restrictedContributionsCount
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
        }
        pullRequests(states: MERGED) { totalCount }
        issues(states: CLOSED) { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, orderBy: {field: STARGAZERS, direction: DESC}) {
          totalCount
          nodes {
            name
            stargazerCount
            forkCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node {
                  name
                  color
                }
              }
            }
          }
        }
      }
    }
    '''
    cmd = f"gh api graphql -f query='{query}'"
    out = run_cmd(cmd)
    try:
        return json.loads(out)
    except Exception as e:
        print(f"Error parsing GraphQL: {e}", file=sys.stderr)
        return None

def compute_metrics(data):
    user = data["data"]["user"]
    repos = user["repositories"]["nodes"]
    
    total_stars = sum(r.get("stargazerCount", 0) for r in repos)
    total_forks = sum(r.get("forkCount", 0) for r in repos)
    total_repos = user["repositories"]["totalCount"]
    
    # Contributions
    cc = user["contributionsCollection"]
    total_commits = cc.get("totalCommitContributions", 0) + cc.get("restrictedContributionsCount", 0)
    total_prs = user["pullRequests"]["totalCount"]
    total_issues = user["issues"]["totalCount"]
    
    # Aggregate languages
    lang_bytes = {}
    lang_colors = {
        "C++": "#00599c",
        "Go": "#00add8",
        "Python": "#3776ab",
        "TypeScript": "#3178c6",
        "PHP": "#777bb4",
        "Kotlin": "#7f52ff",
        "C": "#555555",
        "Shell": "#89e051",
        "JavaScript": "#f1e05a",
        "HTML": "#e34c26"
    }
    
    # Filter out markup/notebooks/build scripts to highlight actual programming languages
    ignored_langs = {"Jupyter Notebook", "HTML", "CSS", "Makefile", "CMake", "Shell", "Roff", "M4", "Batchfile", "QMake", "NSIS"}
    
    for r in repos:
        for edge in r.get("languages", {}).get("edges", []):
            name = edge["node"]["name"]
            size = edge["size"]
            color = edge["node"]["color"]
            if name in ignored_langs:
                continue
            if color:
                lang_colors[name] = color
            lang_bytes[name] = lang_bytes.get(name, 0) + size
            
    total_size = sum(lang_bytes.values()) or 1
    sorted_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)
    
    top_langs = []
    for name, size in sorted_langs[:6]:
        pct = (size / total_size) * 100
        top_langs.append({
            "name": name,
            "percent": pct,
            "color": lang_colors.get(name, "#00f0ff")
        })
        
    return {
        "stars": total_stars,
        "commits": total_commits,
        "prs": total_prs,
        "issues": total_issues,
        "repos": total_repos,
        "top_langs": top_langs
    }

def generate_stats_svg(metrics, filepath):
    svg = f'''<svg width="495" height="195" viewBox="0 0 495 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 700 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #00f0ff; }}
    .stat-label {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
    .stat-val {{ font: 700 14px 'Segoe UI', Ubuntu, Sans-Serif; fill: #ffffff; }}
    .icon {{ fill: #ff00aa; }}
    .rank-circle {{ stroke: #00f0ff; stroke-width: 5; fill: none; }}
    .rank-text {{ font: 800 24px 'Segoe UI', Ubuntu, Sans-Serif; fill: #00f0ff; }}
    .rank-sub {{ font: 600 10px 'Segoe UI', Ubuntu, Sans-Serif; fill: #ff00aa; }}
    .card-border {{ stroke: #00f0ff; stroke-opacity: 0.35; stroke-width: 1.5; }}
  </style>

  <rect width="494" height="194" x="0.5" y="0.5" rx="10" fill="#090b10" class="card-border" />

  <!-- Header -->
  <g transform="translate(25, 32)">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14.5v-9l6 4.5-6 4.5z" class="icon" transform="translate(0, -14) scale(0.9)"/>
    <text x="25" y="0" class="header">Parallax's GitHub Telemetry</text>
  </g>

  <!-- Left Stats Column -->
  <g transform="translate(25, 62)">
    <!-- Stars -->
    <g transform="translate(0, 0)">
      <text class="icon" font-size="14">★</text>
      <text x="22" y="0" class="stat-label">Total Stars Earned:</text>
      <text x="210" y="0" class="stat-val">{metrics['stars']}</text>
    </g>

    <!-- Commits -->
    <g transform="translate(0, 26)">
      <text class="icon" font-size="14">⚡</text>
      <text x="22" y="0" class="stat-label">Total Commits (Tracked):</text>
      <text x="210" y="0" class="stat-val">{metrics['commits']}+</text>
    </g>

    <!-- PRs Merged -->
    <g transform="translate(0, 52)">
      <text class="icon" font-size="14">🦈</text>
      <text x="22" y="0" class="stat-label">Total PRs Merged:</text>
      <text x="210" y="0" class="stat-val">{metrics['prs']} (Pull Shark 2x)</text>
    </g>

    <!-- Issues Closed -->
    <g transform="translate(0, 78)">
      <text class="icon" font-size="14">🎯</text>
      <text x="22" y="0" class="stat-label">Total Issues Resolved:</text>
      <text x="210" y="0" class="stat-val">{metrics['issues']}</text>
    </g>

    <!-- Repos -->
    <g transform="translate(0, 104)">
      <text class="icon" font-size="14">📦</text>
      <text x="22" y="0" class="stat-label">Owned Repositories:</text>
      <text x="210" y="0" class="stat-val">{metrics['repos']}</text>
    </g>
  </g>

  <!-- Right Rank Badge -->
  <g transform="translate(390, 105)">
    <circle r="46" class="rank-circle" />
    <circle r="46" stroke="#ff00aa" stroke-width="5" stroke-dasharray="290" stroke-dashoffset="65" fill="none" />
    <text text-anchor="middle" y="6" class="rank-text">A+</text>
    <text text-anchor="middle" y="24" class="rank-sub">DEVSECOPS</text>
  </g>
</svg>'''
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg)

def generate_top_langs_svg(metrics, filepath):
    langs = metrics["top_langs"]
    
    # Progress bars
    items_svg = []
    y = 52
    for l in langs:
        bar_width = int(l['percent'] * 1.8)
        items_svg.append(f'''
    <g transform="translate(25, {y})">
      <circle cx="5" cy="-4" r="5" fill="{l['color']}" />
      <text x="18" y="0" class="lang-name">{l['name']}</text>
      <text x="145" y="0" class="lang-pct">{l['percent']:.1f}%</text>
      <rect x="200" y="-10" width="180" height="8" rx="4" fill="#1c2438" />
      <rect x="200" y="-10" width="{max(bar_width, 6)}" height="8" rx="4" fill="{l['color']}" />
    </g>''')
        y += 24
        
    items_block = "\n".join(items_svg)
    
    svg = f'''<svg width="430" height="195" viewBox="0 0 430 195" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .header {{ font: 700 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: #00f0ff; }}
    .lang-name {{ font: 600 13px 'Segoe UI', Ubuntu, Sans-Serif; fill: #ffffff; }}
    .lang-pct {{ font: 600 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: #c9d1d9; }}
    .card-border {{ stroke: #00f0ff; stroke-opacity: 0.35; stroke-width: 1.5; }}
  </style>

  <rect width="429" height="194" x="0.5" y="0.5" rx="10" fill="#090b10" class="card-border" />

  <!-- Header -->
  <g transform="translate(25, 32)">
    <text class="header">Most Used Languages</text>
  </g>

  <!-- Languages List -->
{items_block}
</svg>'''
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg)

def main():
    print("Fetching GitHub metrics via authenticated GraphQL...")
    data = fetch_github_data()
    if not data:
        print("Failed to fetch data", file=sys.stderr)
        sys.exit(1)
        
    metrics = compute_metrics(data)
    print("Metrics:", metrics)
    
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    generate_stats_svg(metrics, assets_dir / "github-stats.svg")
    generate_top_langs_svg(metrics, assets_dir / "top-langs.svg")
    print("Successfully generated assets/github-stats.svg and assets/top-langs.svg!")

if __name__ == "__main__":
    main()
