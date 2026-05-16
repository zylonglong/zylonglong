import argparse
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import pandas as pd


TAXON_COLS = ["门", "纲", "目", "科", "属", "种", "拉丁文"]


def find_sheet_name(sheet_names: List[str], keyword: str) -> str:
    """Find one sheet containing all parts of keyword split by '_' ."""
    parts = [p for p in keyword.split("_") if p]
    for name in sheet_names:
        cleaned = name.strip()
        if all(part in cleaned for part in parts):
            return name
    raise ValueError(f"未找到工作表: {keyword}")


def prepare_table(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    for col in TAXON_COLS:
        if col not in df.columns:
            raise ValueError(f"工作表缺少必要字段: {col}")

    site_cols = [c for c in df.columns if c not in TAXON_COLS]
    for col in site_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["门"] = df["门"].astype(str).str.strip()
    df["种"] = df["种"].astype(str).str.strip()
    return df


def autopct_fmt(pct: float) -> str:
    return f"{pct:.1f}%" if pct >= 3 else ""


def make_donut(ax, series: pd.Series, title: str):
    series = series[series > 0].sort_values(ascending=False)
    if series.empty:
        ax.set_title(title)
        ax.text(0.5, 0.5, "无数据", ha="center", va="center")
        return

    wedges, texts, autotexts = ax.pie(
        series.values,
        labels=series.index,
        autopct=autopct_fmt,
        startangle=90,
        counterclock=False,
        wedgeprops={"width": 0.45, "edgecolor": "white"},
        pctdistance=0.78,
        labeldistance=1.06,
    )
    for t in texts + autotexts:
        t.set_fontsize(9)
    ax.set_title(title)
    ax.axis("equal")


def make_stacked_bar(ax, phylum_site: pd.DataFrame, title: str, ylabel: str):
    phylum_site = phylum_site.loc[:, (phylum_site.sum(axis=0) > 0)]
    if phylum_site.empty:
        ax.set_title(title)
        ax.text(0.5, 0.5, "无数据", ha="center", va="center")
        return

    phylum_site.T.plot(kind="bar", stacked=True, ax=ax, width=0.85, legend=False)
    ax.set_title(title)
    ax.set_xlabel("点位")
    ax.set_ylabel(ylabel)
    ax.tick_params(axis="x", rotation=60, labelsize=8)


def main():
    parser = argparse.ArgumentParser(
        description="绘制枯水期赤石河流域浮游植物门水平组成与点位堆积柱状图"
    )
    parser.add_argument(
        "--excel",
        default=r"E:\\桌面\\水生态项目文件\\深圳源清项目\\【五期】2025年8月-12月\\2025年深圳河流水生生物汇总.xlsx",
        help="Excel文件路径（默认使用你提供的本地路径）",
    )
    parser.add_argument(
        "--out",
        default="赤石河流域_枯水期_浮游植物群落统计图.png",
        help="输出图片路径",
    )
    args = parser.parse_args()

    excel_path = Path(args.excel)
    if not excel_path.exists():
        raise FileNotFoundError(
            f"Excel文件不存在: {excel_path}\n"
            "请确认文件路径正确，或通过 --excel 指定实际路径。"
        )

    xls = pd.ExcelFile(excel_path)
    basin_sheet = find_sheet_name(xls.sheet_names, "所属河流流域")
    density_sheet = find_sheet_name(xls.sheet_names, "枯水期_浮游植物_密度")
    biomass_sheet = find_sheet_name(xls.sheet_names, "枯水期_浮游植物_生物量")

    basin_df = pd.read_excel(excel_path, sheet_name=basin_sheet)
    basin_df.columns = [str(c).strip() for c in basin_df.columns]
    for req in ["点位编号", "所在流域"]:
        if req not in basin_df.columns:
            raise ValueError(f"{basin_sheet} 缺少字段: {req}")

    basin_sites = (
        basin_df.loc[basin_df["所在流域"].astype(str).str.strip() == "赤石河流域", "点位编号"]
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )
    if not basin_sites:
        raise ValueError("所属河流流域表中未找到赤石河流域点位")

    density_df = prepare_table(pd.read_excel(excel_path, sheet_name=density_sheet))
    biomass_df = prepare_table(pd.read_excel(excel_path, sheet_name=biomass_sheet))

    density_sites = [s for s in basin_sites if s in density_df.columns]
    biomass_sites = [s for s in basin_sites if s in biomass_df.columns]
    common_sites = [s for s in basin_sites if s in density_sites and s in biomass_sites]

    if not common_sites:
        raise ValueError("赤石河流域点位未在浮游植物数据表中匹配到")

    density_df = density_df[TAXON_COLS + common_sites]
    biomass_df = biomass_df[TAXON_COLS + common_sites]

    presence_mask = density_df[common_sites].sum(axis=1) > 0
    species_comp = (
        density_df.loc[presence_mask]
        .groupby("门")["种"]
        .nunique()
        .sort_values(ascending=False)
    )

    density_comp = density_df.groupby("门")[common_sites].sum().sum(axis=1).sort_values(ascending=False)
    biomass_comp = biomass_df.groupby("门")[common_sites].sum().sum(axis=1).sort_values(ascending=False)

    density_site_stacked = density_df.groupby("门")[common_sites].sum().sort_values(by=common_sites, axis=0, ascending=False)
    biomass_site_stacked = biomass_df.groupby("门")[common_sites].sum().sort_values(by=common_sites, axis=0, ascending=False)

    plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 3, figsize=(22, 12), constrained_layout=True)

    make_donut(axes[0, 0], species_comp, "枯水期赤石河流域浮游植物（门水平）种类数组成")
    make_donut(axes[0, 1], density_comp, "枯水期赤石河流域浮游植物（门水平）密度组成")
    make_donut(axes[0, 2], biomass_comp, "枯水期赤石河流域浮游植物（门水平）生物量组成")

    make_stacked_bar(
        axes[1, 0],
        density_site_stacked,
        "各点位浮游植物门水平密度堆积柱状图（枯水期，赤石河流域）",
        "密度",
    )
    make_stacked_bar(
        axes[1, 1],
        biomass_site_stacked,
        "各点位浮游植物门水平生物量堆积柱状图（枯水期，赤石河流域）",
        "生物量",
    )
    axes[1, 2].axis("off")

    handles, labels = axes[1, 0].get_legend_handles_labels()
    if labels:
        fig.legend(handles, labels, loc="center right", bbox_to_anchor=(1.02, 0.5), title="门")

    out_path = Path(args.out)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    print(f"图已保存至: {out_path.resolve()}")


if __name__ == "__main__":
    main()
