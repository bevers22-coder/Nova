from collections.abc import Mapping, Sequence

import pandas as pd


def apply_screener_filters(
    results: pd.DataFrame,
    criteria: Sequence[Mapping[str, object]],
    sector_contains: str = "",
    industry_contains: str = "",
) -> pd.DataFrame:
    filtered = results.copy()
    mask = pd.Series(True, index=filtered.index)

    for criterion in criteria:
        field = str(criterion["field"])
        operator = str(criterion["operator"])
        lower = float(criterion["lower"])
        if field not in filtered:
            raise ValueError(f"Screener metric is unavailable: {field}")
        values = pd.to_numeric(filtered[field], errors="coerce")
        mask &= values.notna()
        if operator == "≥":
            mask &= values >= lower
        elif operator == "≤":
            mask &= values <= lower
        elif operator == "Between":
            upper = float(criterion["upper"])
            mask &= values.between(lower, upper)
        else:
            raise ValueError(f"Unsupported screener condition: {operator}")

    if sector_contains.strip():
        if "Sector" not in filtered:
            raise ValueError("Sector data is unavailable.")
        mask &= filtered["Sector"].fillna("").str.contains(
            sector_contains.strip(), case=False, regex=False
        )
    if industry_contains.strip():
        if "Industry" not in filtered:
            raise ValueError("Industry data is unavailable.")
        mask &= filtered["Industry"].fillna("").str.contains(
            industry_contains.strip(), case=False, regex=False
        )

    return filtered.loc[mask].copy()
