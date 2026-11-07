"""Summary tables and figures for data/pm_postings.csv.

Prints the summary tables used in the blog post and saves figures to figures/.

Usage:
    uv run scripts/eda.py
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
FIG_DIR = ROOT / "figures"

sns.set_theme(style="whitegrid", palette="colorblind")

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
    shares = df[list(SKILL_LABELS)].mean().sort_values(ascending=False) * 100
    plot_df = pd.DataFrame({
        "skill": [SKILL_LABELS[name] for name in shares.index],
        "percent": shares.values,
        "type": ["Technical" if name.startswith("tech_") else "Soft"
                 for name in shares.index],
    })

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=plot_df, x="percent", y="skill", hue="type", dodge=False, ax=ax)
    ax.bar_label(ax.containers[0], fmt="%.0f%%", padding=3)
    ax.bar_label(ax.containers[1], fmt="%.0f%%", padding=3)
    ax.set(xlabel="% of postings that mention it in the requirements", ylabel="",
           title="What PM postings ask for", xlim=(0, 75))
    ax.legend(title="")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "skill_frequency.png", dpi=200)
    plt.close(fig)


def fig_ai_by_level(df: pd.DataFrame) -> None:
    shares = (df.groupby("level", observed=True)
              [["ai_in_requirements", "ai_tools_in_requirements"]].mean() * 100)
    shares.columns = ["Asks for AI knowledge or experience",
                      "Asks you to use AI tools yourself"]
    plot_df = shares.reset_index().melt(id_vars="level", var_name="type",
                                        value_name="percent")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(data=plot_df, x="percent", y="level", hue="type", ax=ax)
    ax.set(xlabel="% of postings (requirements section only)", ylabel="",
           title="AI in PM requirements by level", xlim=(0, 100))
    ax.legend(title="", loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "ai_by_level.png", dpi=200)
    plt.close(fig)


def fig_pay_by_level(df: pd.DataFrame) -> None:
    # Intern / Associate is left out since only 2 of those postings list annual pay
    annual = df[df["pay_mid"].notna() & (df["level"] != "Intern / Associate")].copy()
    annual["level"] = annual["level"].cat.remove_unused_categories()
    annual["pay_mid_k"] = annual["pay_mid"] / 1000

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.boxplot(data=annual, x="pay_mid_k", y="level", ax=ax)
    ax.set(xlabel="Midpoint of listed annual base pay ($ thousands)", ylabel="",
           title="Listed base pay by level")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "pay_by_level.png", dpi=200)
    plt.close(fig)


def fig_tech_soft_by_level(df: pd.DataFrame) -> None:
    means = df.groupby("level", observed=True)[["tech_count", "soft_count"]].mean()
    means.columns = ["Technical skills (out of 6)", "Soft skills (out of 5)"]
    plot_df = means.reset_index().melt(id_vars="level", var_name="type",
                                       value_name="average")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(data=plot_df, x="average", y="level", hue="type", ax=ax)
    ax.set(xlabel="Average number of skills mentioned", ylabel="",
           title="Technical vs soft skills by level")
    ax.legend(title="", loc="lower right")
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
