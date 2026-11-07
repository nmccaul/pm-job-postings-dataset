"""Summary tables and figures for data/pm_postings.csv.

Prints the summary tables used in the blog post and saves figures to figures/.

Usage:
    uv run scripts/eda.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures"

# Colors from a colorblind-checked palette
BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

LEVELS = ["Intern / Associate", "Product Manager", "Senior", "Staff / Principal",
          "Group / Manager", "Director+"]

SKILL_LABELS = {
    "tech_data_analytics": "Data / analytics / experiments",
    "tech_apis": "APIs / developer products",
    "tech_cs_degree": "CS or engineering degree",
    "tech_technical_background": "\"Technical background\"",
    "tech_sql": "SQL",
    "tech_coding": "Coding (Python, etc.)",
    "soft_collaboration": "Collaboration / cross-functional",
    "soft_stakeholders": "Stakeholders / executives",
    "soft_communication": "Communication",
    "soft_leadership": "Leadership / influence",
    "soft_customer_focus": "Customer empathy",
}


def style_axes(ax, xgrid=True):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)
    ax.grid(axis="x" if xgrid else "y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def load() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "pm_postings.csv")
    df["level"] = df["seniority"].replace({"Intern": "Intern / Associate",
                                           "Associate / Entry": "Intern / Associate"})
    df["level"] = pd.Categorical(df["level"], categories=LEVELS, ordered=True)
    # Midpoint of the listed range, annual pay only (a few internships list hourly pay)
    annual = df["pay_period"] == "year"
    df["pay_mid"] = ((df["pay_low"] + df["pay_high"]) / 2).where(annual)
    return df


def print_summaries(df: pd.DataFrame) -> None:
    print(f"Postings: {len(df)}  Companies: {df['company'].nunique()}  "
          f"Columns: {df.shape[1]}")
    print("\nPostings by level:\n", df["level"].value_counts(sort=False).to_string())
    print("\nPostings by industry:\n", df["industry"].value_counts().to_string())
    print("\nWork mode:\n", df["work_mode"].value_counts().to_string())
    print(f"\nUS location: {df['us_based'].mean():.0%}")
    print(f"Requirements section found: {df['req_section_found'].mean():.0%}")

    ai = df[["ai_anywhere", "ai_in_requirements", "ai_tools_in_requirements"]].mean()
    print("\nAI mentions (share of postings):\n", ai.round(3).to_string())

    skills = df[list(SKILL_LABELS)].mean().sort_values(ascending=False)
    print("\nSkill mentions in requirements:\n", skills.round(3).to_string())

    print("\nNumeric summaries:")
    annual = df[df["pay_period"] == "year"]
    print(f"Annual pay listed: {len(annual)} of {len(df)} ({len(annual)/len(df):.0%})")
    print(annual[["pay_low", "pay_high", "pay_mid"]].describe().round(0).to_string())
    print(df[["min_years_experience", "tech_count", "soft_count", "board_open_jobs"]]
          .describe().round(1).to_string())

    by_level = df.groupby("level", observed=True).agg(
        postings=("title", "size"),
        median_years=("min_years_experience", "median"),
        median_pay_mid=("pay_mid", "median"),
        ai_required=("ai_in_requirements", "mean"),
        ai_tools=("ai_tools_in_requirements", "mean"),
        tech_count=("tech_count", "mean"),
        soft_count=("soft_count", "mean"),
    ).round(2)
    print("\nBy level:\n", by_level.to_string())

    pay_ai = (annual.groupby(["level", "ai_in_requirements"], observed=True)["pay_mid"]
              .agg(["median", "size"]).round(0))
    print("\nMedian annual pay midpoint by level and AI requirement:\n", pay_ai.to_string())

    by_industry = df.groupby("industry").agg(
        postings=("title", "size"),
        ai_required=("ai_in_requirements", "mean"),
        tech_count=("tech_count", "mean"),
        pay_listed=("pay_period", lambda s: (s == "year").mean()),
    ).round(2).sort_values("ai_required", ascending=False)
    print("\nBy industry:\n", by_industry.to_string())


def fig_skills(df: pd.DataFrame) -> None:
    shares = df[list(SKILL_LABELS)].mean().sort_values()
    colors = [BLUE if name.startswith("tech_") else ORANGE for name in shares.index]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([SKILL_LABELS[n] for n in shares.index], shares * 100, color=colors,
            height=0.65)
    for y, value in enumerate(shares * 100):
        ax.text(value + 1, y, f"{value:.0f}%", va="center", color=INK, fontsize=9)
    style_axes(ax)
    ax.set_xlim(0, 75)
    ax.set_xlabel("% of postings that mention it in the requirements", color=MUTED)
    ax.set_title("What PM postings ask for", loc="left", color=INK, fontsize=13)
    ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=BLUE),
                       plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
              labels=["Technical", "Soft"], frameon=False, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "skill_frequency.png", dpi=200)
    plt.close(fig)


def fig_ai_by_level(df: pd.DataFrame) -> None:
    shares = df.groupby("level", observed=True)[
        ["ai_in_requirements", "ai_tools_in_requirements"]].mean() * 100
    counts = df["level"].value_counts().reindex(shares.index)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = range(len(shares))
    ax.barh([i - 0.18 for i in y], shares["ai_in_requirements"], height=0.34,
            color=BLUE, label="Asks for AI knowledge or experience")
    ax.barh([i + 0.18 for i in y], shares["ai_tools_in_requirements"], height=0.34,
            color=ORANGE, label="Asks you to use AI tools yourself")
    ax.set_yticks(list(y), [f"{lvl} (n={counts[lvl]})" for lvl in shares.index])
    ax.invert_yaxis()
    style_axes(ax)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% of postings, requirements section only", color=MUTED)
    ax.set_title("AI in PM requirements by level", loc="left", color=INK, fontsize=13)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ai_by_level.png", dpi=200)
    plt.close(fig)


def fig_pay_by_level(df: pd.DataFrame) -> None:
    annual = df[(df["pay_period"] == "year")]
    levels = [lvl for lvl in LEVELS if (annual["level"] == lvl).sum() >= 5]
    data = [annual.loc[annual["level"] == lvl, "pay_mid"] / 1000 for lvl in levels]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    box = ax.boxplot(data, orientation="horizontal", patch_artist=True, widths=0.55,
                     medianprops={"color": INK, "linewidth": 2},
                     whiskerprops={"color": MUTED}, capprops={"color": MUTED},
                     flierprops={"marker": "o", "markersize": 4,
                                 "markerfacecolor": BLUE, "markeredgecolor": "white"})
    for patch in box["boxes"]:
        patch.set(facecolor="#9ec5f4", edgecolor=BLUE)
    ax.set_yticks(range(1, len(levels) + 1),
                  [f"{lvl} (n={len(d)})" for lvl, d in zip(levels, data)])
    ax.invert_yaxis()
    style_axes(ax)
    ax.set_xlabel("Midpoint of listed annual base pay range ($ thousands)", color=MUTED)
    ax.set_title("Listed base pay by level", loc="left", color=INK, fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "pay_by_level.png", dpi=200)
    plt.close(fig)


def fig_tech_soft_by_level(df: pd.DataFrame) -> None:
    means = df.groupby("level", observed=True)[["tech_count", "soft_count"]].mean()
    x = range(len(means))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar([i - 0.2 for i in x], means["tech_count"], width=0.38, color=BLUE,
           label="Technical skills (out of 6)")
    ax.bar([i + 0.2 for i in x], means["soft_count"], width=0.38, color=ORANGE,
           label="Soft skills (out of 5)")
    ax.set_xticks(list(x), [lvl.replace(" / ", "/\n") for lvl in means.index],
                  fontsize=9)
    style_axes(ax, xgrid=False)
    ax.set_ylabel("Average skills mentioned", color=MUTED)
    ax.set_title("Technical vs soft skills by level", loc="left", color=INK, fontsize=13)
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "tech_vs_soft_by_level.png", dpi=200)
    plt.close(fig)


def main() -> None:
    FIG_DIR.mkdir(exist_ok=True)
    df = load()
    print_summaries(df)
    fig_skills(df)
    fig_ai_by_level(df)
    fig_pay_by_level(df)
    fig_tech_soft_by_level(df)
    print(f"\nSaved figures to {FIG_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
