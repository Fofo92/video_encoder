"""Keep both language titles, including identical titles for foreign works."""


def title_with_original(metadata):
    french = str(metadata.get("french_title") or "").strip()
    original = str(metadata.get("original_title") or "").strip()
    if not french:
        return original
    if not original:
        return french
    countries = metadata.get("countries", [])
    french_work = (isinstance(countries, list) and any(
        isinstance(country, str) and country.strip().casefold() == "france" for country in countries))
    if french_work and french.casefold() == original.casefold():
        return french
    already_present = french.casefold().endswith(f" ({original.casefold()})")
    return french if already_present else f"{french} ({original})"
